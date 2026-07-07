import React, { useEffect, useRef } from 'react';

// ==========================================
// ANIMATION PHYSICS & DENSITY CONFIGURATION
// You can adjust these values to change the speed, density, and swarming behaviors.
// ==========================================
const CONFIG = {
  // --- Particle Generation & Spacing ---
  // Smaller values = denser dots and higher particle count
  STEP_X: 4,  // Horizontal dot spacing (pixels)
  STEP_Y: 7,  // Vertical scanline height (pixels)

  // --- Animation Transition Speeds ---
  // Base easing speed. Increase to make transition faster (e.g. 0.08 to 0.12)
  TRANSITION_SPEED: 0.14,
  // Speed variation per particle for an organic, asynchronous arrival (e.g. 0.04)
  TRANSITION_VARIATION: 0.5,

  // --- Swarm/Drifting Wave Physics ---
  // Maximum strength of the curving swarm effect (0 for straight lines, 20-50 for curved paths)
  SWARM_STRENGTH: 35,
  // How fast the curving perturbation decays as particles approach targets (e.g. 0.15)
  SWARM_DECAY: 0.15,
  // Wave frequency/speed multiplier (higher = faster waving during transit)
  SWARM_FREQUENCY: 0.07,

  // --- Eyes Idle State (Scene 1) ---
  // Easing towards eye coordinates
  EYE_STEERING: 0.1,
  // Speed of the organic idle breathing cycle
  IDLE_BREATH_SPEED: 0.08,
  // Scale of horizontal and vertical idle breathing
  IDLE_RANGE_X: 0.6,
  // Vertical breathing range
  IDLE_RANGE_Y: 0.4,
};

export interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;

  // Logical coordinates (0 to 1200, 0 to 600)
  eyeX: number;
  eyeY: number;
  welcomeX: number;
  welcomeY: number;
  mokaX: number;
  mokaY: number;

  size: number;
  alpha: number;
  targetAlpha: number; // dynamically changes based on state
  mokaAlpha: number;   // active logo opacity (only 1 particle per pixel target to avoid blobs)
  speedOffset: number;
  seed: number;
  isFadingOut: boolean;
}

// Mathematical helper to distribute particles uniformly along a rounded rectangle border
const getRoundedRectPoint = (
  w: number,
  h: number,
  r: number,
  cx: number,
  cy: number,
  t: number
) => {
  const L_top = w - 2 * r;
  const L_side = h - 2 * r;
  const L_arc = (Math.PI * r) / 2;
  const P = 2 * L_top + 2 * L_side + 4 * L_arc; // total perimeter

  const d = t * P; // distance along perimeter

  // 1. Top side (moving right)
  if (d < L_top) {
    return { x: cx - w / 2 + r + d, y: cy - h / 2 };
  }

  // 2. Top-right corner
  let limit = L_top + L_arc;
  if (d < limit) {
    const d_arc = d - L_top;
    const angle = -Math.PI / 2 + (d_arc / L_arc) * (Math.PI / 2);
    return {
      x: cx + w / 2 - r + r * Math.cos(angle),
      y: cy - h / 2 + r + r * Math.sin(angle),
    };
  }

  // 3. Right side (moving down)
  limit += L_side;
  if (d < limit) {
    const d_side = d - (L_top + L_arc);
    return { x: cx + w / 2, y: cy - h / 2 + r + d_side };
  }

  // 4. Bottom-right corner
  limit += L_arc;
  if (d < limit) {
    const d_arc = d - (L_top + L_arc + L_side);
    const angle = 0 + (d_arc / L_arc) * (Math.PI / 2);
    return {
      x: cx + w / 2 - r + r * Math.cos(angle),
      y: cy + h / 2 - r + r * Math.sin(angle),
    };
  }

  // 5. Bottom side (moving left)
  limit += L_top;
  if (d < limit) {
    const d_top = d - (L_top + 2 * L_arc + L_side);
    return { x: cx + w / 2 - r - d_top, y: cy + h / 2 };
  }

  // 6. Bottom-left corner
  limit += L_arc;
  if (d < limit) {
    const d_arc = d - (2 * L_top + 2 * L_arc + L_side);
    const angle = Math.PI / 2 + (d_arc / L_arc) * (Math.PI / 2);
    return {
      x: cx - w / 2 + r + r * Math.cos(angle),
      y: cy + h / 2 - r + r * Math.sin(angle),
    };
  }

  // 7. Left side (moving up)
  limit += L_side;
  if (d < limit) {
    const d_side = d - (2 * L_top + 3 * L_arc + L_side);
    return { x: cx - w / 2, y: cy + h / 2 - r - d_side };
  }

  // 8. Top-left corner
  const d_arc = d - (2 * L_top + 3 * L_arc + 2 * L_side);
  const angle = Math.PI + (d_arc / L_arc) * (Math.PI / 2);
  return {
    x: cx - w / 2 + r + r * Math.cos(angle),
    y: cy - h / 2 + r + r * Math.sin(angle),
  };
};

// Helper to draw rounded rectangle
const drawRoundedRect = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number
) => {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
  ctx.fill();
};

interface ParticleCanvasProps {
  chatBoxRef: React.RefObject<HTMLDivElement | null>;
  onChatActiveChange: (active: boolean) => void;
}

/**
 * ParticleCanvas component rendering the glowing vector dot matrix animations.
 * Tracks screen scrolling to flow particles between shapes:
 * - Eyes idle breathing layout
 * - TRANSITION -> WELCOME text center alignment
 * - MOKA top-left logo alignment (header background tracking)
 * - Outline tracking for the floating ChatBox.
 */
export const ParticleCanvas: React.FC<ParticleCanvasProps> = ({
  chatBoxRef,
  onChatActiveChange,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Keep animation state in refs for high-performance retrieval inside requestAnimationFrame
  const stateRef = useRef<'eyes' | 'transitioning' | 'moka' | 'chat_box'>('eyes');
  const particlesRef = useRef<Particle[]>([]);
  const animationFrameId = useRef<number | null>(null);
  const cycleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isScrolledRef = useRef(false);
  const isChatActiveRef = useRef(false);
  const hasShownWelcomeRef = useRef(false);
  const mouseRef = useRef({ x: 0, y: 0 });
  const mouseTargetRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    // 1. Generate Target Coordinates using an offscreen canvas
    const logicalW = 1200;
    const logicalH = 600;

    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = logicalW;
    tempCanvas.height = logicalH;
    const tempCtx = tempCanvas.getContext('2d');
    if (!tempCtx) return;

    // --- Scene 1: Eyes Shape ---
    tempCtx.fillStyle = '#000000';
    tempCtx.fillRect(0, 0, logicalW, logicalH);

    tempCtx.fillStyle = '#ffffff';
    // Draw two rounded rectangular eyes
    // Left eye (centered at X = 400)
    drawRoundedRect(tempCtx, 280, 180, 240, 240, 40);
    // Right eye (centered at X = 800)
    drawRoundedRect(tempCtx, 680, 180, 240, 240, 40);

    // Extract eye targets
    const eyeImgData = tempCtx.getImageData(0, 0, logicalW, logicalH);
    const eyeData = eyeImgData.data;
    const eyeTargets: { x: number; y: number }[] = [];

    // Dense grid sampling for matrix scanline aesthetic
    const stepY = CONFIG.STEP_Y;
    const stepX = CONFIG.STEP_X;

    for (let y = 0; y < logicalH; y += stepY) {
      for (let x = 0; x < logicalW; x += stepX) {
        const idx = (y * logicalW + x) * 4;
        if (eyeData[idx] > 128) {
          eyeTargets.push({ x, y });
        }
      }
    }

    // --- Scene 3: WELCOME Text Shape ---
    tempCtx.fillStyle = '#000000';
    tempCtx.fillRect(0, 0, logicalW, logicalH);

    tempCtx.fillStyle = '#ffffff';
    // Draw "WELCOME" text centered
    tempCtx.font = '900 150px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    tempCtx.textAlign = 'center';
    tempCtx.textBaseline = 'middle';
    tempCtx.fillText('WELCOME', logicalW / 2, logicalH / 2 + 10);

    // Extract welcome targets
    const welcomeImgData = tempCtx.getImageData(0, 0, logicalW, logicalH);
    const welcomeData = welcomeImgData.data;
    const welcomeTargets: { x: number; y: number }[] = [];

    for (let y = 0; y < logicalH; y += stepY) {
      for (let x = 0; x < logicalW; x += stepX) {
        const idx = (y * logicalW + x) * 4;
        if (welcomeData[idx] > 128) {
          welcomeTargets.push({ x, y });
        }
      }
    }

    // --- Scene 4: MOKA Logo Shape (Top-Left) ---
    tempCtx.fillStyle = '#000000';
    tempCtx.fillRect(0, 0, logicalW, logicalH);

    tempCtx.fillStyle = '#ffffff';
    // Draw "MOKA" text starting at 0, 0 with a slightly lighter font-weight (bold) to make strokes thinner and readable
    tempCtx.font = 'bold 100px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    tempCtx.textAlign = 'left';
    tempCtx.textBaseline = 'top';
    tempCtx.fillText('MOKA', 0, 0);

    // Extract moka targets
    const mokaImgData = tempCtx.getImageData(0, 0, logicalW, logicalH);
    const mokaData = mokaImgData.data;
    const mokaTargets: { x: number; y: number }[] = [];

    for (let y = 0; y < logicalH; y += stepY) {
      for (let x = 0; x < logicalW; x += stepX) {
        const idx = (y * logicalW + x) * 4;
        if (mokaData[idx] > 128) {
          mokaTargets.push({ x, y });
        }
      }
    }

    // --- Particle System Initialization ---
    const shuffledWelcome = [...welcomeTargets].sort(() => Math.random() - 0.5);
    const shuffledMoka = [...mokaTargets].sort(() => Math.random() - 0.5);

    // Set particle count to match all dots from the eyes
    const particleCount = eyeTargets.length;
    const particles: Particle[] = [];

    for (let i = 0; i < particleCount; i++) {
      const eyeT = eyeTargets[i];
      const welcomeT = shuffledWelcome[i % shuffledWelcome.length];

      // Select only exactly one particle per pixel target of MOKA to avoid overlap/blurring
      const isMokaActive = i < shuffledMoka.length;
      const mokaT = shuffledMoka[i % shuffledMoka.length];

      // Add a tiny random offset to overlapping welcome targets
      const offsetXWelcome = (Math.random() - 0.5) * 4;
      const offsetYWelcome = (Math.random() - 0.5) * 4;

      particles.push({
        x: eyeT.x,
        y: eyeT.y,
        vx: (Math.random() - 0.5) * 2,
        vy: (Math.random() - 0.5) * 2,
        eyeX: eyeT.x,
        eyeY: eyeT.y,
        welcomeX: welcomeT.x + offsetXWelcome,
        welcomeY: welcomeT.y + offsetYWelcome,
        mokaX: mokaT.x,
        mokaY: mokaT.y,
        size: Math.random() * 1.0 + 1.6, // dot size between 1.6px and 2.6px
        alpha: 0, // start invisible and fade in
        targetAlpha: 1.0,
        mokaAlpha: isMokaActive ? 1.0 : 0.0, // hide excess particles in logo state
        speedOffset: Math.random(),
        seed: Math.random() * 100,
        isFadingOut: false,
      });
    }

    particlesRef.current = particles;

    // --- Canvas Dimensions & Animation Setup ---
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resizeCanvas = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      ctx.scale(dpr, dpr);
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Fade-in initial state
    particles.forEach(p => {
      p.alpha = 0;
    });

    let time = 0;
    const render = () => {
      time++;
      const width = window.innerWidth;
      const height = window.innerHeight;

      // Smoothly interpolate cursor position (lerp)
      mouseRef.current.x += (mouseTargetRef.current.x - mouseRef.current.x) * 0.35;
      mouseRef.current.y += (mouseTargetRef.current.y - mouseRef.current.y) * 0.35;

      // Scale matrix to fit screen width and height uniformly with margins
      const scale = Math.min(width / logicalW, height / logicalH) * 0.82;
      const offsetX = (width - logicalW * scale) / 2;
      const offsetY = (height - logicalH * scale) / 2;

      ctx.clearRect(0, 0, width, height);

      const currentState = stateRef.current;

      // Make the shadow glow subtler/sharper in MOKA and CHAT states to improve legibility
      const isSubtleGlow = currentState === 'moka' || currentState === 'chat_box';
      ctx.shadowBlur = (isSubtleGlow ? 4 : 8) * scale;
      ctx.shadowColor = 'rgba(0, 243, 255, 0.75)';
      ctx.fillStyle = '#00f3ff';

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // 1. Determine active target coordinates and opacity target based on state
        let targetX = 0;
        let targetY = 0;
        let pTargetAlpha = 1.0;

        if (currentState === 'eyes') {
          // 1. Calculate base coordinates relative to local eye center (400 or 800)
          const cx = p.eyeX < 600 ? 400 : 800;
          const cy = 300;
          const dx = p.eyeX - cx;
          const dy = p.eyeY - cy;

          // 2. Interactive eye sizing based on mouse side
          const isLeftEye = p.eyeX < 600;
          const eyeScale = isLeftEye
            ? (1.0 - mouseRef.current.x * 0.15)
            : (1.0 + mouseRef.current.x * 0.15);

          const scaledX = cx + dx * eyeScale;
          const scaledY = cy + dy * eyeScale;

          // 3. Smooth gaze shift offset for the entire eye shapes
          const maxShift = 20; // maximum offset in logical pixels
          const shiftX = mouseRef.current.x * maxShift;
          const shiftY = mouseRef.current.y * maxShift;

          // 4. Combine scaling, translation, shift, and idle breathing motion
          const idleX = Math.sin(time * CONFIG.IDLE_BREATH_SPEED + p.seed * 5) * CONFIG.IDLE_RANGE_X;
          const idleY = Math.cos(time * CONFIG.IDLE_BREATH_SPEED + p.seed * 5) * CONFIG.IDLE_RANGE_Y;

          targetX = (scaledX + shiftX) * scale + offsetX + idleX;
          targetY = (scaledY + shiftY) * scale + offsetY + idleY;
          pTargetAlpha = 1.0;
        } else if (currentState === 'moka') {
          // MOKA logo at top-left, centered vertically inside the fixed 96px header
          const logoScale = 0.38;
          targetX = 48 + p.mokaX * logoScale;
          targetY = 29 + p.mokaY * logoScale;
          pTargetAlpha = p.mokaAlpha; // inactive particles fade to 0 opacity
        } else if (currentState === 'chat_box' && chatBoxRef.current) {
          // Dynamic chat box tracking! Query the HTML element's bounding box relative to the viewport
          const rect = chatBoxRef.current.getBoundingClientRect();
          const boxW = rect.width;
          const boxH = rect.height;
          const boxR = 24; // matches rounded-[24px] corner radius
          const boxCX = rect.left + rect.width / 2;
          const boxCY = rect.top + rect.height / 2;

          // Map particle uniformly along the rounded rect outline in viewport coordinates
          const pt = i / particles.length;
          const pCoord = getRoundedRectPoint(boxW, boxH, boxR, boxCX, boxCY, pt);
          targetX = pCoord.x;
          targetY = pCoord.y;
          pTargetAlpha = 1.0;

          // --- Path Constraint for Chat Box Transition ---
          // Force particles to follow the red line conduit (down the left side first, then curve right into the box)
          // To prevent distorting the settled box, we only apply the left-skew constraint if the particle is physically above the top of the box.
          let finalTargetX = targetX;
          if (p.y < rect.top - 10) {
            const startX = 60; // lock X target near the left margin (X ≈ 60px)
            const curveStartHeight = rect.top - 20; // curve starts sweeping right just above the box
            const t = Math.max(0, Math.min(1, (p.y - 48) / (curveStartHeight - 48)));
            finalTargetX = startX + (targetX - startX) * (t * t);
          }
          targetX = finalTargetX;
        } else if (currentState === 'chat_box') {
          // Fallback if ref is not fully painted yet
          const boxW = Math.min(width * 0.8, 800);
          const boxH = 450;
          const boxR = 24;
          const boxCX = width / 2;
          const boxCY = height + 100;
          const pt = i / particles.length;
          const pCoord = getRoundedRectPoint(boxW, boxH, boxR, boxCX, boxCY, pt);
          targetX = pCoord.x;
          targetY = pCoord.y;
          pTargetAlpha = 0.0;
        } else {
          // WELCOME coordinates
          targetX = p.welcomeX * scale + offsetX;
          targetY = p.welcomeY * scale + offsetY;
          pTargetAlpha = 1.0;
        }

        // 2. Physics Motion Update (steer and swarm dynamically)
        const dx = targetX - p.x;
        const dy = targetY - p.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        // Easing factor with variation: tighter and faster when in eyes state to track cursor instantly
        const ease = currentState === 'eyes' 
          ? 0.28 + p.speedOffset * 0.08
          : CONFIG.TRANSITION_SPEED + p.speedOffset * CONFIG.TRANSITION_VARIATION;

        // Swarming curving perturbation: decays as particles reach targets (disable for steady eyes/moka/chat to avoid slow-motion drift)
        const isSwarmingState = currentState !== 'eyes' && currentState !== 'moka' && currentState !== 'chat_box';
        const swarmFactor = isSwarmingState ? Math.min(dist * CONFIG.SWARM_DECAY, CONFIG.SWARM_STRENGTH) : 0;
        const angle = time * CONFIG.SWARM_FREQUENCY + p.seed * 15;
        const swarmX = Math.sin(angle) * swarmFactor;
        const swarmY = Math.cos(angle * 0.9) * swarmFactor;

        p.x += (targetX + swarmX - p.x) * ease;
        p.y += (targetY + swarmY - p.y) * ease;

        // Smoothly fade in or fade out based on target alpha
        p.alpha += (pTargetAlpha - p.alpha) * 0.08;

        // Draw particle if visible
        if (p.alpha > 0.01) {
          // Render dots slightly smaller for moka & chat box to keep detail sharp
          const isScaledDown = currentState === 'moka' || currentState === 'chat_box';
          const currentSize = isScaledDown ? p.size * 0.72 * scale : p.size * scale;
          
          ctx.fillStyle = `rgba(0, 243, 255, ${p.alpha})`;
          ctx.beginPath();
          ctx.arc(p.x, p.y, currentSize, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      animationFrameId.current = requestAnimationFrame(render);
    };

    render();

    // Loop cycle: 10s eyes -> 10s welcome -> repeat (active only when not scrolled)
    const runCycle = () => {
      if (cycleTimerRef.current) clearTimeout(cycleTimerRef.current);
      if (hasShownWelcomeRef.current && stateRef.current === 'eyes') return;

      cycleTimerRef.current = setTimeout(() => {
        if (isScrolledRef.current) return; // do not cycle if user is scrolled down

        if (stateRef.current === 'eyes') {
          stateRef.current = 'transitioning';
          hasShownWelcomeRef.current = true;
          runCycle();
        } else {
          stateRef.current = 'eyes';
        }
      }, 10000);
    };

    runCycle();

    // Mouse tracking event listener
    const handleMouseMove = (e: MouseEvent) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      mouseTargetRef.current = {
        x: (e.clientX - cx) / cx,
        y: (e.clientY - cy) / cy,
      };
    };
    window.addEventListener('mousemove', handleMouseMove);

    // Scroll tracking logic
    const handleScroll = () => {
      const scrollY = window.scrollY;
      isScrolledRef.current = scrollY > 40;

      if (scrollY <= 40) {
        if (stateRef.current !== 'eyes' && stateRef.current !== 'transitioning') {
          stateRef.current = 'eyes';
          runCycle();
        }
        if (isChatActiveRef.current) {
          isChatActiveRef.current = false;
          onChatActiveChange(false);
        }
      } else {
        if (cycleTimerRef.current) clearTimeout(cycleTimerRef.current);

        // Dynamically track if the chat box container has entered the viewport
        let showChat = false;
        if (chatBoxRef.current) {
          const rect = chatBoxRef.current.getBoundingClientRect();
          // Trigger transition when the top of the chat box enters the viewport
          showChat = rect.top < window.innerHeight - 40;
        }

        if (showChat) {
          stateRef.current = 'chat_box';
          if (!isChatActiveRef.current) {
            isChatActiveRef.current = true;
            onChatActiveChange(true);
          }
        } else {
          stateRef.current = 'moka';
          if (isChatActiveRef.current) {
            isChatActiveRef.current = false;
            onChatActiveChange(false);
          }
        }
      }
    };

    // Run once initially to register active coordinates if already scrolled
    handleScroll();
    window.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('mousemove', handleMouseMove);
      if (cycleTimerRef.current) clearTimeout(cycleTimerRef.current);
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, [chatBoxRef, onChatActiveChange]);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full block z-35 pointer-events-none"
    />
  );
};

export default ParticleCanvas;
