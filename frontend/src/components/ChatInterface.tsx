import React, { useState, useEffect, useRef, useCallback } from 'react';

interface Message {
  id: string;
  sender: 'user' | 'moka';
  text: string;
  timestamp: string;
}

interface ChatInterfaceProps {
  onBackToLanding?: () => void;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ onBackToLanding }) => {
  const [isConversationStarted, setIsConversationStarted] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isMokaTyping, setIsMokaTyping] = useState(false);
  const [pendingQueue, setPendingQueue] = useState<{ id: string; text: string; timestamp: string }[]>([]);

  const [isMuted, setIsMuted] = useState(() => {
    return localStorage.getItem('moka_chat_muted') === 'true';
  });

  useEffect(() => {
    localStorage.setItem('moka_chat_muted', String(isMuted));
  }, [isMuted]);

  const handleToggleMute = async () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);

    if (nextMuted) {
      try {
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };
        if (token) {
          headers['X-Moka-Token'] = token;
        }

        await fetch(`${API_BASE_URL}/api/mute`, {
          method: 'POST',
          headers,
        });
      } catch (err) {
        console.warn("Failed to notify backend of mute interrupt:", err);
      }
    }
  };

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const mouseRef = useRef({ x: 0, y: 0 });
  const mouseTargetRef = useRef({ x: 0, y: 0 });
  const mousePosTargetRef = useRef({ x: -9999, y: -9999 });
  const animationFrameId = useRef<number | null>(null);

  // Sync isConversationStarted to a ref to prevent state-closure stale bugs in the canvas loop
  const isConversationStartedRef = useRef(false);
  useEffect(() => {
    isConversationStartedRef.current = isConversationStarted;
  }, [isConversationStarted]);

  // Header loop state to cycle between MOKA text and mini-eyes every 15 seconds
  const [headerState, setHeaderState] = useState<'moka' | 'eyes'>('moka');
  const headerStateRef = useRef<'moka' | 'eyes'>('moka');

  useEffect(() => {
    if (!isConversationStarted) {
      setHeaderState('moka');
      headerStateRef.current = 'moka';
      return;
    }

    const interval = setInterval(() => {
      const next = headerStateRef.current === 'moka' ? 'eyes' : 'moka';
      setHeaderState(next);
      headerStateRef.current = next;
    }, 15000);

    return () => clearInterval(interval);
  }, [isConversationStarted]);

  // Core Brain Connection State (polls backend /api/health)
  const [isConnected, setIsConnected] = useState(false);
  const isConnectedRef = useRef(false);
  useEffect(() => {
    isConnectedRef.current = isConnected;
  }, [isConnected]);
  const [token, setToken] = useState<string>('');

  useEffect(() => {
    const fetchLocalToken = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/token/local`);
        if (res.ok) {
          const data = await res.json();
          if (data.token) {
            setToken(data.token);
          }
        }
      } catch (err) {
        console.warn("Failed to automatically retrieve local token:", err);
      }
    };
    fetchLocalToken();
  }, []);

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/health`);
        if (res.ok) {
          setIsConnected(true);
        } else {
          setIsConnected(false);
        }
      } catch {
        setIsConnected(false);
      }
    };

    checkConnection();
    const intervalId = setInterval(checkConnection, 3000);
    return () => clearInterval(intervalId);
  }, []);

  // Suggested starter prompts
  /* const suggestions = [
    "Tell me about Moka's memory system.",
    "How does OpenCV auto-docking work?",
    "Which local LLMs can Moka run?",
    "What workflows can Moka automate?"
  ]; */

  // Scroll to bottom helper
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isMokaTyping]);

  // High-performance Particle Canvas Eye system
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const logicalW = 1200;
    const logicalH = 600;

    // Helper for rounded rectangle
    const drawRoundedRect = (
      c: CanvasRenderingContext2D,
      x: number,
      y: number,
      w: number,
      h: number,
      r: number
    ) => {
      c.beginPath();
      c.moveTo(x + r, y);
      c.lineTo(x + w - r, y);
      c.quadraticCurveTo(x + w, y, x + w, y + r);
      c.lineTo(x + w, y + h - r);
      c.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      c.lineTo(x + r, y + h);
      c.quadraticCurveTo(x, y + h, x, y + h - r);
      c.lineTo(x, y + r);
      c.quadraticCurveTo(x, y, x + r, y);
      c.closePath();
      c.fill();
    };

    // Draw eye shapes offscreen to extract pixel targets
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = logicalW;
    tempCanvas.height = logicalH;
    const tempCtx = tempCanvas.getContext('2d');
    if (!tempCtx) return;

    tempCtx.fillStyle = '#000000';
    tempCtx.fillRect(0, 0, logicalW, logicalH);
    tempCtx.fillStyle = '#ffffff';

    // Left and Right eye locations
    drawRoundedRect(tempCtx, 280, 180, 240, 240, 45);
    drawRoundedRect(tempCtx, 680, 180, 240, 240, 45);

    const eyeImgData = tempCtx.getImageData(0, 0, logicalW, logicalH);
    const eyeData = eyeImgData.data;
    const eyeTargets: { x: number; y: number }[] = [];

    const stepY = 8;
    const stepX = 5;

    for (let y = 0; y < logicalH; y += stepY) {
      for (let x = 0; x < logicalW; x += stepX) {
        const idx = (y * logicalW + x) * 4;
        if (eyeData[idx] > 128) {
          eyeTargets.push({ x, y });
        }
      }
    }

    // --- Scene: MOKA Logo Shape ---
    const tempCanvasMoka = document.createElement('canvas');
    tempCanvasMoka.width = logicalW;
    tempCanvasMoka.height = logicalH;
    const tempCtxMoka = tempCanvasMoka.getContext('2d');
    const mokaTargets: { x: number; y: number }[] = [];

    if (tempCtxMoka) {
      tempCtxMoka.fillStyle = '#000000';
      tempCtxMoka.fillRect(0, 0, logicalW, logicalH);
      tempCtxMoka.fillStyle = '#ffffff';
      tempCtxMoka.font = 'bold 100px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      tempCtxMoka.textAlign = 'left';
      tempCtxMoka.textBaseline = 'top';
      tempCtxMoka.fillText('MOKA', 0, 0);

      const mokaImgData = tempCtxMoka.getImageData(0, 0, logicalW, logicalH);
      const mokaData = mokaImgData.data;

      // Sample logo targets with stepY=8 and stepX=5 to match homepage density exactly
      for (let y = 0; y < logicalH; y += stepY) {
        for (let x = 0; x < logicalW; x += stepX) {
          const idx = (y * logicalW + x) * 4;
          if (mokaData[idx] > 128) {
            mokaTargets.push({ x, y });
          }
        }
      }
    }

    const shuffledMoka = [...mokaTargets].sort(() => Math.random() - 0.5);

    interface EyeParticle {
      x: number;
      y: number;
      eyeX: number;
      eyeY: number;
      mokaX: number;
      mokaY: number;
      size: number;
      alpha: number;
      mokaAlpha: number;
      seed: number;
      speedOffset: number;
    }

    const particles: EyeParticle[] = eyeTargets.map((target, idx) => {
      const isMokaActive = idx < shuffledMoka.length;
      const mokaT = shuffledMoka[idx % shuffledMoka.length];
      return {
        x: target.x,
        y: target.y,
        eyeX: target.x,
        eyeY: target.y,
        mokaX: mokaT.x,
        mokaY: mokaT.y,
        size: Math.random() * 1.0 + 1.8,
        alpha: 0,
        mokaAlpha: isMokaActive ? 1.0 : 0.0,
        seed: Math.random() * 100,
        speedOffset: Math.random(),
      };
    });

    let time = 0;
    let blinkTimer = 0;
    let blinkFactor = 1.0;

    const render = () => {
      time++;

      // Use window coordinates for full-viewport canvas
      const width = window.innerWidth;
      const height = window.innerHeight;

      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }

      ctx.clearRect(0, 0, width, height);

      // Handle blinks
      if (blinkTimer > 0) {
        blinkTimer--;
        if (blinkTimer > 10) {
          blinkFactor = (blinkTimer - 10) / 10; // closing
        } else {
          blinkFactor = (10 - blinkTimer) / 10; // opening
        }
      } else {
        blinkFactor = 1.0;
        if (Math.random() < 0.004) {
          blinkTimer = 20;
        }
      }

      // Smooth mouse tracking
      mouseRef.current.x += (mouseTargetRef.current.x - mouseRef.current.x) * 0.08;
      mouseRef.current.y += (mouseTargetRef.current.y - mouseRef.current.y) * 0.08;

      const isConversationStartedVal = isConversationStartedRef.current;
      const eyesCenterY = height * 0.32;
      const scale = Math.min(width / logicalW, height / logicalH) * 0.82;
      const offsetX = (width - logicalW * scale) / 2;
      const offsetY = eyesCenterY - (logicalH / 2) * scale;

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        let targetX = 0;
        let targetY = 0;
        let pTargetAlpha = 1.0;

        if (!isConversationStartedVal) {
          // Eye shape centers
          const cx = p.eyeX < 600 ? 400 : 800;
          const cy = 300;

          const dx = p.eyeX - cx;
          const dy = p.eyeY - cy;

          // Steer with mouse coordinates
          const isLeftEye = p.eyeX < 600;
          const eyeScale = isLeftEye
            ? (1.0 - mouseRef.current.x * 0.15)
            : (1.0 + mouseRef.current.x * 0.15);

          const scaledX = cx + dx * eyeScale;
          // Blink vertically towards local center cy
          const scaledY = cy + dy * eyeScale * blinkFactor;

          // Apply mouse shift
          const maxShift = 24;
          const shiftX = mouseRef.current.x * maxShift;
          const shiftY = mouseRef.current.y * maxShift;

          // Breathe cycle
          const idleX = Math.sin(time * 0.07 + p.seed * 5) * 0.7;
          const idleY = Math.cos(time * 0.07 + p.seed * 5) * 0.5;

          targetX = (scaledX + shiftX) * scale + offsetX + idleX;
          targetY = (scaledY + shiftY) * scale + offsetY + idleY;
          pTargetAlpha = 1.0;
        } else {
          // Conversation started: cycle inside the header container area
          if (headerStateRef.current === 'moka') {
            // MOKA logo text shape aligned to the header (left: 24px, centered at top: 16px)
            const logoScale = 0.48;
            targetX = 24 + p.mokaX * logoScale;
            targetY = 16 + p.mokaY * logoScale;
            pTargetAlpha = p.mokaAlpha;
          } else {
            // Miniature eyes shape in the header (centered at X=96px, Y=40px)
            const miniScale = 0.15;
            const headerCenterX = 96;
            const headerCenterY = 40;

            const cx = p.eyeX < 600 ? 400 : 800;
            const cy = 300;

            const dx_eye = p.eyeX - cx;
            const dy_eye = p.eyeY - cy;

            const isLeftEye = p.eyeX < 600;
            const eyeScale = isLeftEye
              ? (1.0 - mouseRef.current.x * 0.15)
              : (1.0 + mouseRef.current.x * 0.15);

            const scaledX = cx + dx_eye * eyeScale;
            const scaledY = cy + dy_eye * eyeScale * blinkFactor;

            const maxShiftMini = 6;
            const shiftX = mouseRef.current.x * maxShiftMini;
            const shiftY = mouseRef.current.y * maxShiftMini;

            const idleX = Math.sin(time * 0.07 + p.seed * 5) * 0.3;
            const idleY = Math.cos(time * 0.07 + p.seed * 5) * 0.2;

            const relativeX = (scaledX - 600) * miniScale;
            const relativeY = (scaledY - 300) * miniScale;

            targetX = headerCenterX + relativeX + shiftX + idleX;
            targetY = headerCenterY + relativeY + shiftY + idleY;
            pTargetAlpha = 1.0;
          }
        }

        // Mouse avoidance repelling force (applied in screen pixel space relative to target coordinates)
        const dxMouse = targetX - mousePosTargetRef.current.x;
        const dyMouse = targetY - mousePosTargetRef.current.y;
        const distMouse = Math.sqrt(dxMouse * dxMouse + dyMouse * dyMouse);

        let avoidX = 0;
        let avoidY = 0;
        const avoidanceRadius = 60; // push radius in pixels
        if (distMouse < avoidanceRadius && distMouse > 0) {
          const force = (avoidanceRadius - distMouse) / avoidanceRadius; // 0 to 1
          const strength = force * 50; // push distance in pixels
          avoidX = (dxMouse / distMouse) * strength;
          avoidY = (dyMouse / distMouse) * strength;
        }

        targetX += avoidX;
        targetY += avoidY;

        // Update positions
        p.x += (targetX - p.x) * (0.07 + p.speedOffset * 0.05);
        p.y += (targetY - p.y) * (0.07 + p.speedOffset * 0.05);

        // Smoothly fade to target alpha
        p.alpha += (pTargetAlpha - p.alpha) * 0.08;

        if (p.alpha > 0.01) {
          // Render dot (scaled down for the logo shape to keep typography detail sharp)
          const currentSize = isConversationStartedVal
            ? Math.max(0.8, p.size * 0.65 * scale)
            : Math.max(1.0, p.size * scale);
          ctx.fillStyle = `rgba(0, 243, 255, ${p.alpha})`;
          ctx.beginPath();
          ctx.arc(p.x, p.y, currentSize, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      animationFrameId.current = requestAnimationFrame(render);
    };

    render();

    // Mouse movement listener
    const handleMouseMove = (e: MouseEvent) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      mouseTargetRef.current = {
        x: (e.clientX - cx) / cx,
        y: (e.clientY - cy) / cy,
      };
      mousePosTargetRef.current = {
        x: e.clientX,
        y: e.clientY,
      };
    };

    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, []);

  // Context-aware replies mock response logic returning a Promise
  const triggerMockMokaResponse = useCallback((userMsg: string): Promise<void> => {
    setIsMokaTyping(true);

    return new Promise((resolve) => {
      setTimeout(() => {
        let reply = "I am checking my local systems for that task. What would you like to build?";
        const cleaned = userMsg.toLowerCase();

        if (cleaned.includes('memory') || cleaned.includes('short-term') || cleaned.includes('long-term')) {
          reply = "Moka uses a dual-layer memory system: PostgresSaver indexes recent message threads, while our local FastEmbed implementation manages long-term RAG lookups across files.";
        } else if (cleaned.includes('cozmo') || cleaned.includes('robot') || cleaned.includes('control')) {
          reply = "My low-latency physical bridge is active. I can steering-dock to the charger using cv2 HSV filters, query paths, or animate OLED face expressions.";
        } else if (cleaned.includes('llm') || cleaned.includes('ollama') || cleaned.includes('model')) {
          reply = "Moka is connected to your local Ollama engine. I am currently running Qwen 2.5 (7B) for deep cognition and Gemma 2 for lower latency routing checkpoints.";
        } else if (cleaned.includes('hello') || cleaned.includes('hi') || cleaned.includes('hey')) {
          reply = "Hello! I am Moka, your local autonomous AI companion. I'm connected to the local Ollama brain. How can I assist you with your workspace or Cozmo today?";
        } else if (cleaned.includes('capabilities') || cleaned.includes('feature') || cleaned.includes('can you do')) {
          reply = "I manage voice triggers ('hey buddy'), index FAISS vectors, trigger workstations, coordinate Google Calendar via n8n, and run OpenAPI auto-docking cycles.";
        }

        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        setMessages(prev => [
          ...prev,
          {
            id: Math.random().toString(),
            sender: 'moka',
            text: reply,
            timestamp
          }
        ]);
        setIsMokaTyping(false);
        resolve();
      }, 1500);
    });
  }, []);

  const processMessage = useCallback(async (messageId: string, text: string, timestamp: string) => {
    setIsMokaTyping(true);

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['X-Moka-Token'] = token;
      }

      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: text,
          session_id: 'web_session',
          mute: isMuted,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();
      const replyTimestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setMessages(prev => [
        ...prev,
        {
          id: Math.random().toString(),
          sender: 'moka',
          text: data.response || 'No response text returned.',
          timestamp: replyTimestamp
        }
      ]);
      setIsMokaTyping(false);
    } catch (error) {
      console.warn("Backend API not reachable. Checking connection status...", error);
      if (!isConnectedRef.current) {
        // Roll back: remove user message from chat stream and prepend back to pending queue
        setMessages(prev => prev.filter(m => m.id !== messageId));
        setPendingQueue(prev => [
          { id: messageId, text, timestamp },
          ...prev
        ]);
        setIsMokaTyping(false);
      } else {
        await triggerMockMokaResponse(text);
      }
    }
  }, [token, isMuted, triggerMockMokaResponse]);

  // Submit handler
  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if (!text) return;

    if (!isConversationStarted) {
      setIsConversationStarted(true);
    }

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const newMessage = {
      id: Math.random().toString(),
      text,
      timestamp
    };

    if (!textToSend) setInputText('');

    if (isMokaTyping || pendingQueue.length > 0 || !isConnected) {
      // Put message on hold in queue
      setPendingQueue(prev => [...prev, newMessage]);
    } else {
      // Direct send
      const userMessage: Message = {
        id: newMessage.id,
        sender: 'user',
        text: newMessage.text,
        timestamp: newMessage.timestamp
      };
      setMessages(prev => [...prev, userMessage]);
      processMessage(newMessage.id, newMessage.text, newMessage.timestamp);
    }
  };

  // Delete pending/on-hold message from queue
  const handleDeletePendingMessage = (id: string) => {
    setPendingQueue(prev => prev.filter(m => m.id !== id));
  };

  // Queue loop: whenever agent is idle, connection is there, and queue has elements, process the next one
  useEffect(() => {
    if (isConnected && !isMokaTyping && pendingQueue.length > 0) {
      const nextMsg = pendingQueue[0];
      setPendingQueue(prev => prev.slice(1));

      const userMessage: Message = {
        id: nextMsg.id,
        sender: 'user',
        text: nextMsg.text,
        timestamp: nextMsg.timestamp
      };
      setMessages(prev => [...prev, userMessage]);
      processMessage(nextMsg.id, nextMsg.text, nextMsg.timestamp);
    }
  }, [isConnected, isMokaTyping, pendingQueue, processMessage]);

  // Keypress listener for Enter and Spacebar voice trigger
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  };

  return (
    <div className="relative w-screen h-screen bg-[#020512] bg-gradient-to-br from-[#020512] via-[#070b1a] to-[#020512] overflow-hidden flex flex-col">
      {/* Subtle digital grid overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.03] z-10"
        style={{
          backgroundImage: 'radial-gradient(circle, #00f3ff 1px, transparent 1px)',
          backgroundSize: '30px 30px'
        }}
      />

      {/* Persistent Header */}
      <header
        data-identity-state={headerState}
        className="fixed top-0 left-0 w-full h-20 bg-[#020512]/95 border-b border-slate-900/60 backdrop-blur-md z-30 flex items-center justify-between px-6"
      >
        {/* Placeholder spacer for the absolute eyes container when transitioned */}
        <div className="w-36 h-10" />

        {/* Back and state details */}
        <div className="flex items-center gap-4">
          <button
            onClick={onBackToLanding}
            className="px-4 py-1.5 rounded-lg border border-slate-800 bg-slate-950/40 hover:bg-slate-900/60 hover:border-slate-700 text-xs md:text-sm font-semibold tracking-wide text-slate-400 hover:text-white transition-all cursor-pointer"
          >
            ← Back to Ecosystem
          </button>
          <div className="flex items-center gap-2 text-xs md:text-sm text-slate-400 font-medium tracking-wide">
            <span className={`w-2 h-2 rounded-full animate-pulse ${isConnected
              ? 'bg-emerald-500 shadow-[0_0_8px_#10b981]'
              : 'bg-rose-500 shadow-[0_0_8px_#f43f5e]'
              }`} />
            Core Brain: {isConnected ? 'Connected' : 'Connecting...'}
          </div>
          {token && (
            <div className="text-[10px] md:text-xs text-cyan-400 bg-cyan-950/40 border border-cyan-800/60 px-2 py-0.5 rounded font-mono" title={token}>
              Token: {token.length > 8 ? `${token.substring(0, 4)}...${token.substring(token.length - 4)}` : token} (Local)
            </div>
          )}
        </div>
      </header>

      {/* Full-viewport canvas for fluid particle eyes and MOKA logo text */}
      <canvas
        ref={canvasRef}
        className="fixed inset-0 w-full h-full block pointer-events-none z-45"
      />

      {/* Scrollable Conversation Stream Wrapper (Full Width) */}
      <div
        className={`w-full flex-1 overflow-y-auto transition-all duration-700 delay-200 ${isConversationStarted ? 'opacity-100' : 'opacity-0 pointer-events-none'
          }`}
      >
        {/* Centered Conversation Stream Content */}
        <div
          className={`px-6 pt-24 pb-32 max-w-2xl mx-auto w-full flex flex-col gap-4 transition-all duration-700 delay-200 ${isConversationStarted ? 'translate-y-0' : 'translate-y-10'
            }`}
        >
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col max-w-[85%] ${msg.sender === 'user' ? 'self-end items-end' : 'self-start items-start'
                }`}
            >
              {/* Sender tag */}
              <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-1 px-1">
                {msg.sender === 'user' ? 'You' : 'Moka'}
              </span>
              {/* Message bubble */}
              <div
                className={`p-4 rounded-2xl text-sm md:text-base leading-relaxed ${msg.sender === 'user'
                  ? 'bg-slate-900/65 border border-cyan-500/20 text-white shadow-[0_0_15px_rgba(0,243,255,0.04)] rounded-tr-none'
                  : 'bg-slate-950/70 border border-slate-800/70 text-slate-300 rounded-tl-none'
                  }`}
              >
                {msg.text}
              </div>
              {/* Timestamp & Actions */}
              {msg.sender === 'user' ? (
                <div className="w-full flex items-center justify-between mt-1 px-1">
                  <button
                    onClick={() => handleSendMessage(msg.text)}
                    className="p-1 rounded text-slate-500 hover:text-cyan-400 hover:bg-slate-900/60 transition-all cursor-pointer flex items-center justify-center group"
                    title="Resend this message"
                  >
                    <svg
                      className="w-3.5 h-3.5 transition-transform duration-500 ease-out group-hover:rotate-180"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2.5}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
                      />
                    </svg>
                  </button>
                  <span className="text-[9px] text-slate-600">{msg.timestamp}</span>
                </div>
              ) : (
                <span className="text-[9px] text-slate-600 mt-1 px-1">{msg.timestamp}</span>
              )}
            </div>
          ))}

          {/* Render pending/on-hold queued messages */}
          {pendingQueue.map((msg) => (
            <div
              key={msg.id}
              className="flex flex-col max-w-[85%] self-end items-end transition-all duration-300"
            >
              <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-1 px-1">
                You
              </span>
              <div
                className="p-4 rounded-2xl text-sm md:text-base leading-relaxed bg-[#0a0f24]/50 border border-dashed border-slate-700/60 text-slate-400 rounded-tr-none flex flex-col gap-2 min-w-[220px]"
              >
                <div>{msg.text}</div>
                <div className="flex items-center justify-between gap-4 mt-1 pt-1.5 border-t border-slate-800/40">
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-medium font-sans">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse" />
                    Queued (On Hold)
                  </div>
                  <button
                    onClick={() => handleDeletePendingMessage(msg.id)}
                    className="px-2 py-0.5 rounded border border-red-500/30 hover:border-red-400 bg-red-950/40 hover:bg-red-900/60 text-red-400 hover:text-white transition-all cursor-pointer text-xs flex items-center gap-1 font-semibold"
                    title="Cancel and delete from queue"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    Cancel
                  </button>
                </div>
              </div>
              <span className="text-[9px] text-slate-600 mt-1 px-1">{msg.timestamp}</span>
            </div>
          ))}

          {/* Typing indicator bubble */}
          {isMokaTyping && (
            <div className="flex flex-col self-start items-start max-w-[85%]">
              <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-1 px-1">
                Moka
              </span>
              <div className="p-4 rounded-2xl rounded-tl-none bg-slate-950/70 border border-slate-800/70 flex gap-1.5 items-center justify-center min-w-[60px]">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Suggested Prompts Grid in Center (Fades out when conversation starts)
      <div
        className={`absolute bottom-[20vh] left-1/2 -translate-x-1/2 w-full max-w-lg px-6 flex flex-col gap-3 transition-all duration-700 ${
          isConversationStarted ? 'opacity-0 scale-95 pointer-events-none' : 'opacity-100 scale-100 z-20'
        }`}
      >
        <p className="text-center text-xs text-slate-500 uppercase tracking-widest font-bold mb-1">
          Suggested prompts
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {suggestions.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(prompt)}
              className="text-left text-xs md:text-sm p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/60 text-slate-400 hover:text-white hover:border-[#00d2ff]/40 hover:bg-slate-900/40 hover:shadow-[0_0_15px_rgba(0,210,255,0.04)] transition-all cursor-pointer font-medium"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
      */}

      {/* Sliding Input Box Container */}
      <div
        className={`absolute left-1/2 -translate-x-1/2 w-full px-6 transition-all duration-700 ease-in-out z-20 ${isConversationStarted
          ? 'bottom-6 max-w-2xl'
          : 'bottom-10 max-w-lg'
          }`}
      >
        <div className="w-full flex items-center bg-slate-950/70 border border-slate-800/80 rounded-2xl p-2.5 backdrop-blur-md hover:border-[#00d2ff]/30 focus-within:border-[#00d2ff]/50 focus-within:shadow-[0_0_20px_rgba(0,210,255,0.06)] transition-all">
          <button
            onClick={handleToggleMute}
            className={`p-3 rounded-xl border transition-all duration-300 cursor-pointer flex items-center justify-center ${isMuted
                ? 'bg-rose-950/40 hover:bg-rose-900/60 border-rose-500/25 hover:border-rose-500/50 text-rose-400'
                : 'bg-cyan-950/40 hover:bg-cyan-900/60 border-cyan-500/25 hover:border-cyan-500/50 text-cyan-400'
              }`}
            title={isMuted ? "Unmute speech output" : "Mute speech output"}
          >
            {isMuted ? (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 9.75L19.5 12m0 0l2.25 2.25M19.5 12l2.25-2.25M19.5 12l-2.25 2.25m-10.5-6L4.5 9H1.5v6h3l4.5 3.75V5.25z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
              </svg>
            )}
          </button>
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message or press Enter to talk..."
            className="flex-1 bg-transparent border-0 outline-none text-white text-sm md:text-base px-4 py-2 placeholder-slate-500"
          />
          <button
            onClick={() => handleSendMessage()}
            disabled={!inputText.trim()}
            className="p-3 bg-cyan-950/60 hover:bg-cyan-500 border border-cyan-500/25 hover:border-cyan-400 text-[#00d2ff] hover:text-white rounded-xl transition-all duration-300 disabled:opacity-30 disabled:hover:bg-cyan-950/60 disabled:hover:text-[#00d2ff] disabled:hover:border-cyan-500/25 cursor-pointer shadow-[0_0_15px_rgba(0,210,255,0.08)] flex items-center justify-center"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
