import React, { useState, useEffect, useRef, useCallback } from 'react';
import SemanticGridMap, { type VisualAnchorData, type ObstacleData, type RobotPose, type BlockData } from './SemanticGridMap';
import Cozmo3DWorldMap from './Cozmo3DWorldMap';
import Header from './ui/Header';
import { useTheme } from '../context/ThemeContext';
import ConstellationFieldBackground from './ui/ConstellationFieldBackground';
import GoldVeinsBackground from './ui/GoldVeinsBackground';
import ParticleDriftBackground from './ui/ParticleDriftBackground';

interface TelemetryData {
  camera_source?: 'cozmo' | 'webcam';
  robot: RobotPose & {
    battery_voltage: number;
    headlight_on: boolean;
    show_heatmap?: boolean;
    webcam_enabled?: boolean;
    camera_source?: 'cozmo' | 'webcam';
    state: string;
    action: string;
    lift_height_mm: number;
    is_connecting?: boolean;
  };
  anchors: VisualAnchorData[];
  obstacles: ObstacleData[];
  blocks?: BlockData[];
  path_info?: {
    success?: boolean;
    total_length_mm?: number;
    min_obstacle_distance_mm?: number;
    clearance_buffer_mm?: number;
    approach_point?: [number, number];
    approach_heading_deg?: number;
    nodes_expanded?: number;
    execution_time_ms?: number;
    waypoints_count?: number;
    message?: string;
  };
  simulation?: {
    is_active?: boolean;
    stage?: string;
  };
  detections: Array<{
    label: string;
    confidence: number;
    world_x: number;
    world_y: number;
    distance_mm: number;
  }>;
  path: number[][];
}

interface CozmoDashboardProps {
  onBackToChat?: () => void;
  onBackToLanding?: () => void;
}

export const CozmoDashboard: React.FC<CozmoDashboardProps> = ({
  onBackToChat: _onBackToChat,
  onBackToLanding: _onBackToLanding,
}) => {
  const { theme } = useTheme();
  const isBlackIce = theme === 'black-ice';
  const isRoyal = theme === 'royal';
  const isIT = theme === 'it';

  const [telemetry, setTelemetry] = useState<TelemetryData>({
    robot: {
      x: 0,
      y: 0,
      theta_deg: 0,
      head_pitch_deg: 15,
      lift_height_mm: 32,
      battery_voltage: 4.10,
      headlight_on: false,
      is_connected: false,
      is_connecting: false,
      webcam_enabled: true,
      state: 'STANDBY',
      action: 'IDLE',
      camera_source: 'cozmo',
    },
    camera_source: 'cozmo',
    anchors: [],
    obstacles: [],
    blocks: [],
    detections: [],
    path: [],
  });

  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [isConnecting, setIsConnecting] = useState<boolean>(false);
  const [cameraSource, setCameraSource] = useState<'cozmo' | 'webcam'>('cozmo');
  const [webcamEnabled, setWebcamEnabled] = useState<boolean>(true);
  const [streamKey, setStreamKey] = useState<number>(Date.now());
  const [teachLabel, setTeachLabel] = useState<string>('');
  const [showTeachModal, setShowTeachModal] = useState<boolean>(false);
  const [clickPos, setClickPos] = useState<{ x: number; y: number } | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('Connecting to Cozmo WebSocket...');
  const [mapViewMode, setMapViewMode] = useState<'2d' | '3d'>('3d');
  const [_activeTab, _setActiveTab] = useState<'stream' | 'map' | 'split'>('split');
  const wsRef = useRef<WebSocket | null>(null);
  const userForcedDisconnectRef = useRef<boolean>(false);

  const apiHost = window.location.hostname || 'localhost';
  const apiPort = '8000';
  const streamUrl = `http://${apiHost}:${apiPort}/api/cozmo/video_feed?source=${cameraSource}&v=${streamKey}`;
  const wsUrl = `ws://${apiHost}:${apiPort}/ws/cozmo/telemetry`;

  // Sync initial status (camera source & connection state) on mount
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`http://${apiHost}:${apiPort}/api/cozmo/status`);
        if (res.ok) {
          const data = await res.json();
          if (typeof data.webcam_enabled === 'boolean') {
            setWebcamEnabled(data.webcam_enabled);
          }
          if (data.camera_source) {
            setCameraSource(data.camera_source);
          }
          if (typeof data.is_connected === 'boolean') {
            const isConn = userForcedDisconnectRef.current ? false : data.is_connected;
            const isConnProg = userForcedDisconnectRef.current ? false : Boolean(data.is_connecting);
            setTelemetry((prev) => ({
              ...prev,
              robot: {
                ...prev.robot,
                is_connected: isConn,
                is_connecting: isConnProg,
              },
            }));
            if (isConnProg) {
              setIsConnecting(true);
            }
          }
        }
      } catch (e) {
        // ignore if offline
      }
    };
    fetchStatus();
  }, [apiHost, apiPort]);

  // Establish WebSocket Connection
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connectWs = () => {
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        setStatusMessage('Telemetry Stream Active (20Hz)');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // If user explicitly forced disconnect, prevent stale backend loops from resurrecting is_connected
          if (userForcedDisconnectRef.current && data.robot) {
            data.robot.is_connected = false;
            data.robot.is_connecting = false;
          }
          setTelemetry(data);
          if (data.robot?.is_connected) {
            setIsConnecting(false);
          } else if (typeof data.robot?.is_connecting === 'boolean' && !userForcedDisconnectRef.current) {
            setIsConnecting(data.robot.is_connecting);
          }
          if (typeof data.robot?.webcam_enabled === 'boolean') {
            setWebcamEnabled(data.robot.webcam_enabled);
          } else if (typeof data.webcam_enabled === 'boolean') {
            setWebcamEnabled(data.webcam_enabled);
          }
        } catch (e) {
          // ignore malformed JSON
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        setStatusMessage('Telemetry Disconnected. Reconnecting...');
        reconnectTimeout = setTimeout(connectWs, 2000);
      };

      ws.onerror = () => {
        setWsConnected(false);
      };
    };

    connectWs();

    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [wsUrl]);

  // Trigger Cozmo Wi-Fi Handshake
  const handleConnectCozmo = useCallback(async () => {
    userForcedDisconnectRef.current = false;
    setIsConnecting(true);
    setStatusMessage('Initiating Cozmo Wi-Fi handshake... (Make sure PC is connected to Cozmo_XXXXXX)');
    try {
      const res = await fetch(`http://${apiHost}:${apiPort}/api/cozmo/connect`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.status === 'connecting') {
        setStatusMessage('Connecting to Cozmo... Awaiting robot Wi-Fi handshake.');
      }
    } catch (e) {
      console.error('Failed to initiate Cozmo connection:', e);
      setStatusMessage('Error contacting backend to connect to Cozmo.');
      setIsConnecting(false);
    }
  }, [apiHost, apiPort]);

  // Trigger Cozmo Disconnect
  const handleDisconnectCozmo = useCallback(async () => {
    // 1. Optimistically reset all UI state immediately so button turns to "CONNECT TO COZMO"
    userForcedDisconnectRef.current = true;
    setIsConnecting(false);
    setTelemetry((prev) => ({
      ...prev,
      robot: {
        ...prev.robot,
        is_connected: false,
        is_connecting: false,
      },
    }));
    setStatusMessage('Cozmo robot disconnected.');
    setStreamKey(Date.now());

    // 2. Notify backend through all channels (POST /disconnect and POST /command)
    try {
      await fetch(`http://${apiHost}:${apiPort}/api/cozmo/disconnect`, {
        method: 'POST',
      });
    } catch (e) {
      // ignore
    }
    try {
      await fetch(`http://${apiHost}:${apiPort}/api/cozmo/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'disconnect' }),
      });
    } catch (e) {
      // ignore
    }
  }, [apiHost, apiPort]);

  // Active polling while connection handshake is in progress
  useEffect(() => {
    if (!isConnecting) return;
    let attempts = 0;
    const maxAttempts = 25; // 25 seconds
    const interval = setInterval(async () => {
      attempts += 1;
      try {
        const res = await fetch(`http://${apiHost}:${apiPort}/api/cozmo/status`);
        if (res.ok) {
          const data = await res.json();
          if (data.is_connected) {
            setIsConnecting(false);
            setStatusMessage('Cozmo connected successfully! Hardware link active.');
            setStreamKey(Date.now());
            clearInterval(interval);
            return;
          }
          if (!data.is_connecting && attempts > 3) {
            setIsConnecting(false);
            setStatusMessage('Cozmo connection failed or timed out. Ensure robot is ON and PC is on Cozmo Wi-Fi.');
            clearInterval(interval);
            return;
          }
        }
      } catch (e) {
        // network issue
      }
      if (attempts >= maxAttempts) {
        setIsConnecting(false);
        setStatusMessage('Cozmo connection attempt timed out.');
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isConnecting, apiHost, apiPort]);

  // Send Command to Backend API / WebSocket
  const sendCommand = useCallback(async (action: string, params: Record<string, any> = {}) => {
    // 1. If real-time motion command and WebSocket is open, send with 0ms latency over WS
    if (['drive', 'stop', 'tilt_head', 'headlight', 'reset_simulation'].includes(action)) {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(JSON.stringify({ action, ...params }));
          return { status: 'success', action };
        } catch (e) {
          // fallback to HTTP
        }
      }
    }

    // 2. HTTP POST Fallback / Management endpoints
    try {
      const res = await fetch(`http://${apiHost}:${apiPort}/api/cozmo/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, ...params }),
      });
      const data = await res.json();
      return data;
    } catch (e) {
      console.error('Command failed:', e);
    }
  }, [apiHost, apiPort]);

  // Camera Source Switcher Handler
  const handleSetCameraSource = useCallback(async (newSource: 'cozmo' | 'webcam') => {
    setCameraSource(newSource);
    await sendCommand('set_camera_source', { source: newSource });
    setStreamKey(Date.now());
  }, [sendCommand]);

  // -------------------------------------------------------------
  // HIGH-RESPONSIVENESS GAME LOOP CONTROLLER (SIMULATION & ROBOT)
  // -------------------------------------------------------------
  const activeKeysRef = useRef<Set<string>>(new Set());
  const activePadDirectionRef = useRef<string | null>(null);

  const startContinuousDriving = useCallback((direction: string) => {
    activePadDirectionRef.current = direction;
  }, []);

  const stopContinuousDriving = useCallback(() => {
    activePadDirectionRef.current = null;
    sendCommand('stop');
  }, [sendCommand]);

  // Main 20Hz Driving Controller Game-Loop
  useEffect(() => {
    const loopInterval = setInterval(() => {
      const keys = activeKeysRef.current;
      const pad = activePadDirectionRef.current;

      let speed = 0.0;
      let steer = 0.0;

      // Check Keyboard Keys
      if (keys.has('w') || keys.has('arrowup')) speed += 85.0;
      if (keys.has('s') || keys.has('arrowdown')) speed -= 85.0;
      if (keys.has('a') || keys.has('arrowleft')) steer += 65.0;
      if (keys.has('d') || keys.has('arrowright')) steer -= 65.0;

      // Check On-screen D-Pad
      if (pad === 'forward') speed += 85.0;
      if (pad === 'backward') speed -= 85.0;
      if (pad === 'left') steer += 65.0;
      if (pad === 'right') steer -= 65.0;

      if (speed !== 0.0 || steer !== 0.0) {
        // 1. Send command to backend
        sendCommand('drive', { speed_mms: speed, turn_rate: steer });

        // 2. Immediately update local telemetry pose for silky-smooth 60FPS digital twin response
        const dt = 0.05;
        setTelemetry((prev) => {
          const curTheta = prev.robot.theta_deg;
          const newTheta = (curTheta + steer * dt) % 360.0;
          const rad = (newTheta * Math.PI) / 180.0;
          const newX = prev.robot.x + speed * Math.cos(rad) * dt;
          const newY = prev.robot.y + speed * Math.sin(rad) * dt;

          return {
            ...prev,
            robot: {
              ...prev.robot,
              x: Math.round(newX * 10) / 10,
              y: Math.round(newY * 10) / 10,
              theta_deg: Math.round(newTheta * 10) / 10,
              action: `DRIVING (${speed > 0 ? 'FWD' : speed < 0 ? 'REV' : ''} ${steer > 0 ? 'L' : steer < 0 ? 'R' : ''})`,
            },
          };
        });
      }
    }, 50);

    return () => clearInterval(loopInterval);
  }, [sendCommand]);

  // Keyboard Event Listeners
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      const key = e.key.toLowerCase();

      if (['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(key)) {
        activeKeysRef.current.add(key);
      } else if (key === ' ' || key === 'x') {
        activeKeysRef.current.clear();
        activePadDirectionRef.current = null;
        sendCommand('stop');
      } else if (key === 'i') {
        sendCommand('tilt_head', { angle_deg: Math.min(44, (telemetry.robot.head_pitch_deg || 15) + 6) });
      } else if (key === 'k') {
        sendCommand('tilt_head', { angle_deg: Math.max(-25, (telemetry.robot.head_pitch_deg || 15) - 6) });
      } else if (key === 'o' || key === 'p') {
        sendCommand('headlight');
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      if (activeKeysRef.current.has(key)) {
        activeKeysRef.current.delete(key);
        if (activeKeysRef.current.size === 0 && !activePadDirectionRef.current) {
          sendCommand('stop');
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [sendCommand, telemetry.robot.head_pitch_deg]);

  // Handle Video Click to Teach (Dual Pane Aware: Left = Camera Video, Right = Heatmap)
  const handleVideoClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const rawClickX = (e.clientX - rect.left) / rect.width;
    const clickY = (e.clientY - rect.top) / rect.height;
    // Map normalized X coordinates seamlessly from either pane (0..0.5 or 0.5..1.0)
    const normX = rawClickX < 0.5 ? rawClickX * 2.0 : (rawClickX - 0.5) * 2.0;
    const clampedX = Math.max(0, Math.min(1, normX));
    const clampedY = Math.max(0, Math.min(1, clickY));

    setClickPos({ x: clampedX, y: clampedY });
    // Immediately trigger backend segmentation to display the purple box over the clicked object
    sendCommand('select_point', { click_x: clampedX, click_y: clampedY });
    setShowTeachModal(true);
  };

  const handleCancelTeach = () => {
    sendCommand('clear_selection');
    setShowTeachModal(false);
    setTeachLabel('');
  };

  const handleSaveTeach = async () => {
    if (!teachLabel.trim()) return;
    await sendCommand('teach', {
      label: teachLabel.trim(),
      click_x: clickPos?.x,
      click_y: clickPos?.y,
    });
    setTeachLabel('');
    setShowTeachModal(false);
  };

  const handleDeleteAnchor = async (label: string) => {
    try {
      await fetch(`http://${apiHost}:${apiPort}/api/cozmo/anchors/${encodeURIComponent(label)}`, {
        method: 'DELETE',
      });
    } catch (e) {
      console.error('Delete anchor failed:', e);
    }
  };

  // Phase 5 Autonomous Docking & 2-Way A* Handlers
  const handlePlanPath = useCallback(async () => {
    try {
      setStatusMessage('Calculating Two-Way A* Docking Path (5cm clearance)...');
      const res = await fetch(`http://${apiHost}:${apiPort}/api/cozmo/plan_dock_path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clearance_mm: 50.0 }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setStatusMessage(`Computed 2-Way A* Path: ${data.plan?.waypoints_count} waypoints (${data.plan?.total_length_mm?.toFixed(0)}mm) in ${data.plan?.execution_time_ms}ms`);
      } else {
        setStatusMessage(data.detail || 'Path planning failed.');
      }
    } catch (e) {
      console.error('Plan path request failed:', e);
    }
  }, [apiHost, apiPort]);

  const handleSimulateDock = useCallback(async () => {
    try {
      setStatusMessage('Locking charger & planning Two-Way A* docking path (5cm clearance)...');
      const res = await fetch(`http://${apiHost}:${apiPort}/api/cozmo/simulation/dock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clearance_mm: 50.0 }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setStatusMessage(
          telemetry.robot.is_connected
            ? 'Autonomous Docking Active: Real Cozmo navigating to charger with 5cm obstacle clearance!'
            : 'Simulation Active: Cozmo returning to charger avoiding all blocks with 5cm clearance!'
        );
      } else {
        setStatusMessage(data.detail || 'Docking request failed.');
      }
    } catch (e) {
      console.error('Docking request failed:', e);
    }
  }, [apiHost, apiPort, telemetry.robot.is_connected]);

  const handleSpawnBlock = useCallback(async (x: number, y: number) => {
    try {
      const blockId = `cube_${Date.now() % 10000}`;
      await fetch(`http://${apiHost}:${apiPort}/api/cozmo/blocks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: blockId,
          x,
          y,
          radius: 25.0,
          clearance_mm: 50.0,
          label: `Cube ${blockId.slice(-3)}`,
        }),
      });
      setStatusMessage(`Spawned Cozmo Light Cube at (${(x / 10).toFixed(1)}, ${(y / 10).toFixed(1)})cm with 5cm safety clearance.`);
      handlePlanPath();
    } catch (e) {
      console.error('Spawn block failed:', e);
    }
  }, [apiHost, apiPort, handlePlanPath]);

  const handleDeleteBlock = useCallback(async (blockId: string) => {
    try {
      await fetch(`http://${apiHost}:${apiPort}/api/cozmo/blocks/${encodeURIComponent(blockId)}`, {
        method: 'DELETE',
      });
      setStatusMessage(`Deleted block ${blockId}`);
      handlePlanPath();
    } catch (e) {
      console.error('Delete block failed:', e);
    }
  }, [apiHost, apiPort, handlePlanPath]);

  const handleResetBlocks = useCallback(async () => {
    try {
      await fetch(`http://${apiHost}:${apiPort}/api/cozmo/blocks/reset`, {
        method: 'POST',
      });
      setStatusMessage('Reset blocks to default 3-cube layout.');
      handlePlanPath();
    } catch (e) {
      console.error('Reset blocks failed:', e);
    }
  }, [apiHost, apiPort, handlePlanPath]);

  const handleResetSimulation = useCallback(async () => {
    try {
      await fetch(`http://${apiHost}:${apiPort}/api/cozmo/simulation/reset`, {
        method: 'POST',
      });
      setStatusMessage('Simulation reset. Cozmo pose at origin (0, 0, 0°).');
    } catch (e) {
      console.error('Reset simulation failed:', e);
    }
  }, [apiHost, apiPort]);

  const batteryColor =
    telemetry.robot.battery_voltage >= 3.8
      ? 'text-emerald-400'
      : telemetry.robot.battery_voltage >= 3.65
      ? 'text-amber-400'
      : 'text-rose-500 animate-pulse';

  return (
    <div className={`relative w-full max-w-full min-h-screen ${
      isBlackIce ? 'bg-[#020407]' : isRoyal ? 'bg-[#030407]' : isIT ? 'bg-[#020503]' : 'bg-[#030407]'
    } text-slate-100 font-sans select-none overflow-x-hidden overflow-y-auto transition-colors duration-700`}>
      {/* Dynamic Theme Gradient Layer */}
      <div 
        className="fixed inset-0 pointer-events-none z-0 transition-opacity duration-700"
        style={{
          background: isBlackIce
            ? `
              radial-gradient(ellipse 90% 60% at 70% 30%, rgba(0, 243, 255, 0.12) 0%, rgba(8, 60, 77, 0.22) 35%, transparent 75%),
              radial-gradient(ellipse 60% 80% at 20% 80%, rgba(0, 243, 255, 0.06) 0%, rgba(6, 30, 42, 0.3) 40%, transparent 80%),
              linear-gradient(135deg, #020407 0%, #03080e 25%, #05141f 55%, #082836 85%, #061c27 100%)
            `
            : isRoyal
            ? `
              radial-gradient(ellipse 80% 60% at 75% 25%, rgba(212, 175, 55, 0.08) 0%, rgba(30, 25, 15, 0.25) 40%, transparent 75%),
              radial-gradient(ellipse 60% 70% at 25% 75%, rgba(255, 215, 0, 0.05) 0%, rgba(18, 16, 12, 0.3) 45%, transparent 80%),
              linear-gradient(135deg, #030407 0%, #06070b 30%, #0a0c12 65%, #020305 100%)
            `
            : isIT
            ? 'linear-gradient(180deg, #020503 0%, #030805 50%, #010402 100%)'
            : 'linear-gradient(180deg, #030407 0%, #05060a 50%, #020305 100%)'
        }}
      />

      {/* ThreeUI Constellation Field Background (Rendered for Black Ice) */}
      {isBlackIce && (
        <ConstellationFieldBackground className="fixed inset-0 pointer-events-none z-0" />
      )}

      {/* Liquid Kintsugi 24k Gold Veins Background (Rendered for Royal) */}
      {isRoyal && (
        <GoldVeinsBackground className="fixed inset-0 pointer-events-none z-0" />
      )}

      {/* ThreeUI Particle Drift ASCII Cyber Data Stream (Rendered for IT) */}
      {isIT && (
        <ParticleDriftBackground className="fixed inset-0 pointer-events-none z-0" />
      )}

      {/* Floating Sub-surface Royal Gold & Warm Amber Lights (Rendered for Royal) */}
      {isRoyal && (
        <>
          <div 
            className="fixed top-1/4 right-[12%] w-[520px] h-[520px] rounded-full blur-[160px] pointer-events-none z-[2] opacity-30 animate-pulse"
            style={{ backgroundColor: 'rgba(212, 175, 55, 0.12)', animationDuration: '7s' }}
          />
          <div 
            className="fixed bottom-1/4 left-[8%] w-[480px] h-[480px] rounded-full blur-[150px] pointer-events-none z-[2] opacity-20"
            style={{ backgroundColor: 'rgba(255, 215, 0, 0.08)' }}
          />
        </>
      )}

      {/* Subtle digital grid overlay */}
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.035] z-[3]"
        style={{
          backgroundImage: isBlackIce 
            ? 'radial-gradient(circle, #00f3ff 1px, transparent 1px)' 
            : isRoyal
            ? 'radial-gradient(circle, rgba(212, 175, 55, 0.6) 1px, transparent 1px)'
            : isIT
            ? 'radial-gradient(circle, rgba(0, 255, 102, 0.6) 1px, transparent 1px)'
            : 'radial-gradient(circle, rgba(255, 255, 255, 0.4) 1px, transparent 1px)',
          backgroundSize: '28px 28px'
        }}
      />

      {/* 1. Global Sticky Navigation Header */}
      <Header defaultActive="cozmo" />

      {/* =========================================================================
          ORIGINAL HEADER (PRESERVED AS COMMENTED OUT PER INSTRUCTION)
         ========================================================================= */}
      {/*
      <header className="h-14 bg-slate-950/90 border-b border-cyan-900/40 px-5 flex items-center justify-between backdrop-blur-md z-30">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <h1 className="text-base font-bold tracking-wider text-cyan-300 flex items-center gap-2">
              COZMO AUTONOMOUS MISSION CONTROL
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-400 border border-cyan-700/50">
                v5.2
              </span>
            </h1>
          </div>

          <div className="h-4 w-px bg-slate-800" />

          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800">
              <span
                className={`w-2 h-2 rounded-full ${
                  telemetry.robot.is_connected ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-amber-400'
                }`}
              />
              <span className="text-slate-300">
                {telemetry.robot.is_connected ? 'ROBOT CONNECTED' : 'STANDBY / WEBCAM'}
              </span>
            </div>

            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800">
              <span className={`font-mono font-bold ${batteryColor}`}>
                {telemetry.robot.battery_voltage.toFixed(2)}V
              </span>
            </div>

            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800">
              <span className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-cyan-400 animate-pulse' : 'bg-rose-500'}`} />
              <span className="text-[11px] text-slate-400 font-mono">
                {wsConnected ? 'TELEMETRY 20Hz' : 'TELEMETRY OFFLINE'}
              </span>
            </div>

            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 font-mono text-cyan-300">
              <span>HEAD: {(telemetry.robot.head_pitch_deg ?? 15) >= 0 ? `+${telemetry.robot.head_pitch_deg ?? 15}` : telemetry.robot.head_pitch_deg}°</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setActiveTab('stream')}
              className={`px-3 py-1 rounded transition ${activeTab === 'stream' ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-white'}`}
            >
              Camera Feed
            </button>
            <button
              onClick={() => setActiveTab('split')}
              className={`px-3 py-1 rounded transition ${activeTab === 'split' ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-white'}`}
            >
              Split View
            </button>
            <button
              onClick={() => setActiveTab('map')}
              className={`px-3 py-1 rounded transition ${activeTab === 'map' ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-white'}`}
            >
              2D Semantic Map
            </button>
          </div>

          <div className="h-4 w-px bg-slate-800" />

          {onBackToChat && (
            <button
              onClick={onBackToChat}
              className="px-3 py-1.5 text-xs font-semibold text-cyan-300 bg-cyan-950/60 hover:bg-cyan-900 border border-cyan-800/60 rounded-md transition flex items-center gap-1.5"
            >
              MoKa Chat
            </button>
          )}

          {onBackToLanding && (
            <button
              onClick={onBackToLanding}
              className="px-3 py-1.5 text-xs font-semibold text-slate-400 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-md transition"
            >
              Home
            </button>
          )}
        </div>
      </header>
      */}

      {/* 2. Top Telemetry & Status Header Bar */}
      <div className="relative z-20 pt-28 md:pt-32 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto pb-6">
        <div className="theme-card rounded-2xl px-5 py-3.5 flex flex-wrap items-center justify-between gap-4 shadow-[0_12px_32px_rgba(0,0,0,0.6)] border border-white/[0.08]">
          {/* Identity & Subtitle */}
          <div className="flex items-center gap-3.5">
            <div className="theme-icon-box w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-lg">
              <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="10" rx="2" />
                <circle cx="12" cy="5" r="2" />
                <path d="M12 7v4" />
                <line x1="8" y1="16" x2="8.01" y2="16" />
                <line x1="16" y1="16" x2="16.01" y2="16" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-bold text-sm md:text-base tracking-wide text-white flex items-center gap-2">
                  COZMO MISSION CONTROL
                </h1>
                <span className="theme-badge px-2 py-0.5 rounded-md text-[10px] font-mono tracking-widest font-bold">
                  v5.2
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono tracking-wider hidden sm:block">
                EMBODIED PHYSICAL SPATIAL INTELLIGENCE & TELEMETRY
              </p>
            </div>
          </div>

          {/* Telemetry Status Badges */}
          <div className="flex items-center flex-wrap gap-2.5 text-xs">
            {/* Robot Wi-Fi Connection Control */}
            {telemetry.robot.is_connected ? (
              <div className="flex items-center gap-1.5">
                <div className="theme-badge px-3 py-1.5 rounded-xl flex items-center gap-2 font-mono text-[11px] border-emerald-500/50 bg-emerald-950/60 text-emerald-300 shadow-[0_0_12px_rgba(52,211,153,0.2)]">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399] animate-pulse" />
                  <span className="font-bold">ROBOT LINKED</span>
                </div>
                <button
                  onClick={handleConnectCozmo}
                  className="dock-btn dock-btn-cyan h-7 px-2.5 text-[11px] font-mono flex items-center gap-1 cursor-pointer select-none"
                  title="Force Reconnect to Cozmo Robot Wi-Fi"
                >
                  <svg className="w-3 h-3 fill-none stroke-current" viewBox="0 0 24 24" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="23 4 23 10 17 10" />
                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                  </svg>
                  <span>RECONNECT</span>
                </button>
                <button
                  onClick={handleDisconnectCozmo}
                  className="dock-btn dock-btn-rose h-7 px-2.5 text-[11px] font-mono flex items-center gap-1 hover:bg-rose-950/80 transition-all cursor-pointer select-none"
                  title="Disconnect Cozmo Robot Wi-Fi"
                >
                  <svg className="w-3 h-3 text-rose-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                  <span>DISCONNECT</span>
                </button>
              </div>
            ) : isConnecting || telemetry.robot.is_connecting ? (
              <div className="flex items-center gap-1.5">
                <button
                  disabled
                  className="theme-badge px-3.5 py-1.5 rounded-xl flex items-center gap-2 font-mono text-[11px] border-amber-500/50 bg-amber-950/70 text-amber-300 cursor-wait animate-pulse"
                  title="Waiting for Cozmo Wi-Fi Handshake..."
                >
                  <svg className="w-3.5 h-3.5 animate-spin text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span className="font-bold">CONNECTING...</span>
                </button>
                <button
                  onClick={handleDisconnectCozmo}
                  className="dock-btn dock-btn-rose h-7 px-2.5 text-[10px] font-mono hover:bg-rose-950/80 cursor-pointer select-none"
                  title="Cancel Connection Attempt"
                >
                  CANCEL
                </button>
              </div>
            ) : (
              <button
                onClick={handleConnectCozmo}
                className={`h-8 px-3.5 rounded-xl flex items-center gap-2 font-mono text-xs font-bold transition-all duration-300 shadow-[0_0_16px_rgba(6,182,212,0.3)] hover:shadow-[0_0_24px_rgba(6,182,212,0.6)] hover:scale-105 active:scale-95 cursor-pointer select-none ${
                  isRoyal
                    ? 'bg-gradient-to-r from-amber-500 to-yellow-400 text-black font-extrabold border border-amber-300/80 shadow-[0_0_16px_rgba(212,175,55,0.4)]'
                    : isIT
                    ? 'bg-gradient-to-r from-emerald-500 to-green-400 text-black font-extrabold border border-emerald-300/80 shadow-[0_0_16px_rgba(16,185,129,0.4)]'
                    : 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white border border-cyan-400/60'
                }`}
                title="Initiate Wi-Fi Connection to Cozmo Robot (Ensure PC is on Cozmo_XXXXXX Wi-Fi)"
              >
                <svg className="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12.55a11 11 0 0 1 14.08 0" />
                  <path d="M1.42 9a16 16 0 0 1 21.16 0" />
                  <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
                  <line x1="12" y1="20" x2="12.01" y2="20" strokeWidth="3" />
                </svg>
                <span>CONNECT TO COZMO</span>
              </button>
            )}

            {/* Active Camera Source Badge */}
            <button
              onClick={() => handleSetCameraSource(cameraSource === 'cozmo' ? 'webcam' : 'cozmo')}
              className="dock-btn h-7 px-3 flex items-center gap-2"
              title="Click to toggle camera source between Cozmo Cam and Webcam"
            >
              <span className={`w-2 h-2 rounded-full ${cameraSource === 'cozmo' ? 'bg-cyan-400 shadow-[0_0_8px_#00f3ff]' : 'bg-indigo-400 shadow-[0_0_8px_#818cf8]'}`} />
              <span>CAM: <strong className="text-white">{cameraSource === 'cozmo' ? 'COZMO' : 'WEBCAM'}</strong></span>
            </button>

            {/* Battery Voltage */}
            <div className="theme-badge px-3.5 py-1.5 rounded-xl flex items-center gap-2 font-mono text-[11px]">
              <svg className="w-3.5 h-3.5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="1" y="6" width="18" height="12" rx="2" ry="2" />
                <line x1="23" y1="13" x2="23" y2="11" />
              </svg>
              <span className={`font-bold ${batteryColor}`}>
                {telemetry.robot.battery_voltage.toFixed(2)}V
              </span>
            </div>

            {/* Telemetry Stream Frequency */}
            <div className="theme-badge px-3.5 py-1.5 rounded-xl flex items-center gap-1.5 font-mono text-[11px] hidden sm:flex">
              <span className={`w-1.5 h-1.5 rounded-full ${
                wsConnected
                  ? isRoyal
                    ? 'bg-amber-400 shadow-[0_0_8px_#f59e0b] animate-pulse'
                    : isIT
                    ? 'bg-emerald-400 shadow-[0_0_8px_#10b981] animate-pulse'
                    : 'bg-cyan-400 shadow-[0_0_8px_#00f3ff] animate-pulse'
                  : 'bg-rose-500'
              }`} />
              <span className="text-slate-300">
                {wsConnected ? '20Hz TELEMETRY' : 'OFFLINE'}
              </span>
            </div>

            {/* Head Pitch */}
            <div className="theme-badge px-3.5 py-1.5 rounded-xl font-mono text-[11px] hidden md:flex items-center gap-1">
              <span className="text-slate-400">HEAD:</span>
              <span className="text-white font-semibold">
                {(telemetry.robot.head_pitch_deg ?? 15) >= 0 ? `+${telemetry.robot.head_pitch_deg ?? 15}` : telemetry.robot.head_pitch_deg}°
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. SECTION 1: Camera Feed First with Generous Space Around It */}
      <section className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 mb-16">
        {/* Main Camera Card */}
        <div className="theme-card rounded-3xl overflow-hidden shadow-[0_24px_64px_rgba(0,0,0,0.85)] border border-white/[0.12]">
          {/* Viewport Header with Camera Source Selector Button on Top Right */}
          <div className="min-h-14 py-2 bg-white/[0.03] border-b border-white/[0.08] px-5 flex flex-wrap items-center justify-between gap-3 text-xs backdrop-blur-xl">
            <div className="flex items-center gap-2.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_#34d399]" />
              <span className="font-bold text-white flex items-center gap-2 font-mono tracking-wider text-sm">
                {cameraSource === 'cozmo' ? 'COZMO CAM + DINO DUAL-PANE' : 'WEBCAM + DINO DUAL-PANE'}
              </span>
              <span className="theme-badge px-2 py-0.5 rounded-md text-[10px] font-mono uppercase font-bold text-emerald-300 border-emerald-500/40 ml-1">
                SIDE-BY-SIDE VIEW
              </span>
              <span className="theme-badge px-2 py-0.5 rounded-md text-[10px] font-mono uppercase font-bold text-slate-300 ml-1">
                {telemetry.robot.action}
              </span>
            </div>

            {/* TOP RIGHT CAMERA SOURCE TOGGLE BUTTONS (Dock Style) */}
            <div className="flex items-center gap-2.5">
              {cameraSource === 'cozmo' && !telemetry.robot.is_connected && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleConnectCozmo();
                  }}
                  disabled={isConnecting}
                  className="dock-btn dock-btn-cyan h-7 px-2.5 text-[11px] font-mono animate-pulse flex items-center gap-1.5 cursor-pointer select-none"
                  title="Connect to Cozmo Robot Wi-Fi"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  <span>{isConnecting ? 'Connecting...' : 'Connect Robot Wi-Fi'}</span>
                </button>
              )}
              <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">
                SOURCE:
              </span>
              <div className="dock-nav-bar">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSetCameraSource('cozmo');
                  }}
                  className={`dock-btn ${cameraSource === 'cozmo' ? 'dock-btn-active' : ''}`}
                  title="Switch stream to Cozmo Robot Built-in Camera"
                >
                  <span className={`w-2 h-2 rounded-full ${cameraSource === 'cozmo' ? 'bg-black animate-ping' : 'bg-slate-500'}`} />
                  Cozmo Cam
                </button>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSetCameraSource('webcam');
                  }}
                  className={`dock-btn ${cameraSource === 'webcam' ? 'dock-btn-active' : ''}`}
                  title="Switch stream to PC Webcam"
                >
                  <span className={`w-2 h-2 rounded-full ${cameraSource === 'webcam' ? 'bg-black animate-ping' : 'bg-slate-500'}`} />
                  PC Webcam
                </button>
              </div>
            </div>
          </div>

          {/* Video Canvas Container (Side-by-Side Dual Pane) */}
          <div
            className="relative aspect-[16/7] md:aspect-[16/7] min-h-[300px] w-full bg-black/95 flex items-center justify-center cursor-crosshair overflow-hidden group border-b border-white/[0.08]"
            onClick={handleVideoClick}
          >
            <img
              src={streamUrl}
              alt="Cozmo DINO Live Vision Stream"
              className="w-full h-full object-contain pointer-events-none"
              onError={(e) => {
                (e.target as HTMLImageElement).src =
                  'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480"><rect width="640" height="480" fill="%23030407"/><text x="50%" y="50%" fill="%23e4e4e7" font-family="monospace" font-size="14" text-anchor="middle" dominant-baseline="middle">CONNECTING TO COZMO VIDEO STREAM...</text></svg>';
              }}
            />

            {/* Detections Overlay Banner */}
            {telemetry.detections && telemetry.detections.length > 0 && (
              <div className="absolute top-4 left-4 bg-emerald-950/85 border border-emerald-500/50 text-emerald-300 px-3.5 py-2 rounded-xl text-xs backdrop-blur-md shadow-xl flex items-center gap-2 pointer-events-none font-mono">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                <span>
                  RECOGNIZED: {telemetry.detections.map((d) => `${d.label.toUpperCase()} (${(d.confidence * 100).toFixed(0)}%)`).join(', ')}
                </span>
              </div>
            )}

            {/* Quick Stream Controls Overlay (Dock Style) */}
            <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity p-2 px-3 rounded-xl border border-white/[0.08] bg-[#08080c]/90 backdrop-blur-2xl shadow-[0_12px_34px_rgba(0,0,0,0.7)]">
              <div className="flex items-center gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    sendCommand('headlight');
                  }}
                  className={`dock-btn ${telemetry.robot.headlight_on ? 'dock-btn-amber dock-btn-active' : ''}`}
                >
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="5" />
                    <line x1="12" y1="1" x2="12" y2="3" />
                    <line x1="12" y1="21" x2="12" y2="23" />
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                    <line x1="1" y1="12" x2="3" y2="12" />
                    <line x1="21" y1="12" x2="23" y2="12" />
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                  </svg>
                  <span>Headlights ({telemetry.robot.headlight_on ? 'ON' : 'OFF'})</span>
                </button>

                <button
                  onClick={async (e) => {
                    e.stopPropagation();
                    const targetState = !webcamEnabled;
                    setWebcamEnabled(targetState);
                    setTelemetry((prev) => ({
                      ...prev,
                      webcam_enabled: targetState,
                      robot: {
                        ...prev.robot,
                        webcam_enabled: targetState,
                      },
                    }));
                    try {
                      const res = await sendCommand('toggle_webcam', { enabled: targetState });
                      if (res && typeof res.webcam_enabled === 'boolean') {
                        setWebcamEnabled(res.webcam_enabled);
                        setTelemetry((prev) => ({
                          ...prev,
                          webcam_enabled: res.webcam_enabled,
                          robot: {
                            ...prev.robot,
                            webcam_enabled: res.webcam_enabled,
                          },
                        }));
                      }
                    } catch (err) {
                      console.error('Toggle webcam failed:', err);
                    }
                    setStreamKey(Date.now());
                  }}
                  className={`dock-btn ${webcamEnabled ? 'dock-btn-emerald dock-btn-active' : 'dock-btn-rose'}`}
                  title="Toggle PC Webcam Hardware & DINO Inference (ON / OFF)"
                >
                  <span className={`w-2 h-2 rounded-full ${webcamEnabled ? 'bg-black animate-ping' : 'bg-rose-400'}`} />
                  <span>Webcam ({webcamEnabled ? 'ON' : 'OFF'})</span>
                </button>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    sendCommand('brightness', { delta: 10 });
                  }}
                  className="dock-btn"
                  title="Increase Camera Brightness"
                >
                  BRIGHT +10
                </button>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    sendCommand('brightness', { delta: -10 });
                  }}
                  className="dock-btn"
                  title="Decrease Camera Brightness"
                >
                  BRIGHT -10
                </button>
              </div>

              <span className="text-xs text-slate-400 font-mono hidden md:inline px-2">
                Click viewport to store neural anchor
              </span>
            </div>
          </div>
        </div>

        {/* Teleoperation Controls Dock directly below Camera for seamless pilotage */}
        <div className="mt-6">
          <div className="theme-card rounded-2xl px-6 py-4 flex flex-wrap items-center justify-between gap-4 shadow-[0_16px_40px_rgba(0,0,0,0.7)] border border-white/[0.08]">
            {/* Driving D-Pad & Emergency Brake */}
            <div className="flex items-center gap-3.5">
              <div className="flex items-center gap-1.5">
                <button
                  onPointerDown={() => startContinuousDriving('left')}
                  onPointerUp={stopContinuousDriving}
                  onPointerLeave={stopContinuousDriving}
                  className="theme-btn w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm text-white hover:scale-105 active:scale-95 transition cursor-pointer select-none"
                  title="Turn Left (A / Left Arrow)"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="15 18 9 12 15 6" />
                  </svg>
                </button>
                <div className="flex flex-col gap-1.5">
                  <button
                    onPointerDown={() => startContinuousDriving('forward')}
                    onPointerUp={stopContinuousDriving}
                    onPointerLeave={stopContinuousDriving}
                    className="theme-btn w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm text-white hover:scale-105 active:scale-95 transition cursor-pointer select-none"
                    title="Drive Forward (W / Up Arrow)"
                  >
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="18 15 12 9 6 15" />
                    </svg>
                  </button>
                  <button
                    onPointerDown={() => startContinuousDriving('backward')}
                    onPointerUp={stopContinuousDriving}
                    onPointerLeave={stopContinuousDriving}
                    className="theme-btn w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm text-white hover:scale-105 active:scale-95 transition cursor-pointer select-none"
                    title="Drive Backward (S / Down Arrow)"
                  >
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </button>
                </div>
                <button
                  onPointerDown={() => startContinuousDriving('right')}
                  onPointerUp={stopContinuousDriving}
                  onPointerLeave={stopContinuousDriving}
                  className="theme-btn w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm text-white hover:scale-105 active:scale-95 transition cursor-pointer select-none"
                  title="Turn Right (D / Right Arrow)"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </button>
              </div>

              <button
                onClick={stopContinuousDriving}
                className="h-10 px-4 bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/50 text-rose-300 rounded-xl text-xs font-mono font-bold transition flex items-center gap-2 shadow-lg cursor-pointer active:scale-95 select-none"
              >
                <svg className="w-3 h-3 fill-current" viewBox="0 0 24 24">
                  <rect x="4" y="4" width="16" height="16" rx="2" />
                </svg>
                <span>STOP (Space)</span>
              </button>
            </div>

            {/* Head Tilt & Charging Actions */}
            <div className="flex items-center gap-5">
              <div className="flex flex-col items-center gap-1.5">
                <span className="text-[10px] text-slate-400 font-mono tracking-wider font-semibold">HEAD PITCH</span>
                <div className="dock-nav-bar">
                  <button
                    onClick={() => sendCommand('tilt_head', { angle_deg: Math.min(44, (telemetry.robot.head_pitch_deg || 15) + 6) })}
                    className="dock-btn h-7 px-2.5"
                  >
                    UP (+5°)
                  </button>
                  <button
                    onClick={() => sendCommand('tilt_head', { angle_deg: 0 })}
                    className="dock-btn h-7 px-2.5"
                  >
                    0°
                  </button>
                  <button
                    onClick={() => sendCommand('tilt_head', { angle_deg: Math.max(-25, (telemetry.robot.head_pitch_deg || 15) - 6) })}
                    className="dock-btn h-7 px-2.5"
                  >
                    DN (-5°)
                  </button>
                </div>
              </div>

              <div className="h-9 w-px bg-white/[0.08]" />

              {/* Quick Action Dock */}
              <button
                onClick={() => sendCommand('dock')}
                className="dock-btn dock-btn-amber dock-btn-active h-9 px-4 font-bold shadow-lg"
              >
                <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
                <span>DOCK AT CHARGER</span>
              </button>
            </div>

            {/* Status Prompt & Keyboard Legend */}
            <div className="text-right font-mono">
              <div className="text-xs text-white font-medium mb-0.5">{statusMessage}</div>
              <div className="text-[11px] text-slate-400">
                Keys: WASD (Drive) | Space (Stop) | I/K (Pitch) | O (Lights)
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. SECTION 2: Scroll Down Section (Map 2/3 and Visual Anchors 1/3 in a Row Layout) */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        {/* Section Heading */}
        <div className="mb-6">
          <div className="relative inline-block mb-2">
            <h2 className="font-megrim text-3xl md:text-4xl text-white tracking-wider">
              SPATIAL MAP & NEURAL ANCHORS
            </h2>
            <div className="brand-underline" />
          </div>
          <p className="text-slate-400 text-xs md:text-sm font-mono tracking-wider">
            REAL-TIME 2D OCCUPANCY GRID MAPPING & PERSISTENT SPATIAL MEMORY
          </p>
        </div>

        {/* Row Layout: 2/3 Map and 1/3 Visual Anchors */}
        <div className="flex flex-col lg:flex-row gap-6 w-full max-w-full items-stretch">
          {/* 2/3 Width: World Map (2D Grid or 3D Cozmo Model) */}
          <div className="w-full lg:w-2/3 min-w-0 theme-card rounded-2xl overflow-hidden flex flex-col min-h-[520px] shadow-[0_20px_50px_rgba(0,0,0,0.8)] border border-white/[0.1]">
            <div className="h-12 bg-white/[0.03] border-b border-white/[0.08] px-5 flex items-center justify-between text-xs backdrop-blur-xl">
              <div className="flex items-center gap-3">
                <span className="font-bold text-white flex items-center gap-2 font-mono tracking-wider text-sm">
                  <svg className={`w-4 h-4 ${isRoyal ? 'text-amber-400' : isIT ? 'text-emerald-400' : 'text-cyan-400'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
                    <line x1="8" y1="2" x2="8" y2="18" />
                    <line x1="16" y1="6" x2="16" y2="22" />
                  </svg>
                  <span>{mapViewMode === '3d' ? '3D COZMO WORLD MAP' : '2D SEMANTIC WORLD MAP'}</span>
                </span>

                {/* 2D / 3D Mode Toggle Switch (Dock Style) */}
                <div className="dock-nav-bar ml-2">
                  <button
                    onClick={() => setMapViewMode('2d')}
                    className={`dock-btn h-7 px-3 ${mapViewMode === '2d' ? 'dock-btn-active' : ''}`}
                  >
                    2D GRID
                  </button>
                  <button
                    onClick={() => setMapViewMode('3d')}
                    className={`dock-btn h-7 px-3 ${mapViewMode === '3d' ? 'dock-btn-active' : ''}`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${mapViewMode === '3d' ? 'bg-black animate-pulse' : 'bg-cyan-400'}`} />
                    3D MAP
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="theme-badge px-3 py-1 rounded-lg text-xs font-mono text-slate-300">
                  Pose: ({(telemetry.robot.x / 10).toFixed(1)}, {(telemetry.robot.y / 10).toFixed(1)})cm | Heading: {telemetry.robot.theta_deg.toFixed(0)}°
                </span>
              </div>
            </div>

            <div className="flex-1 relative min-h-[460px]">
              {mapViewMode === '2d' ? (
                <SemanticGridMap
                  robot={telemetry.robot}
                  anchors={telemetry.anchors}
                  obstacles={telemetry.obstacles}
                  blocks={telemetry.blocks || []}
                  path={telemetry.path}
                  onPointClick={(wx, wy) => {
                    sendCommand('drive', { target_x: wx, target_y: wy });
                  }}
                  onAnchorClick={(a) => {
                    if (a.label.toLowerCase().includes('charger') || a.label.toLowerCase().includes('dock')) {
                      handleSimulateDock();
                    }
                  }}
                />
              ) : (
                <Cozmo3DWorldMap
                  robot={telemetry.robot}
                  anchors={telemetry.anchors}
                  obstacles={telemetry.obstacles}
                  blocks={telemetry.blocks || []}
                  path={telemetry.path}
                  onPointClick={(wx, wy) => {
                    sendCommand('drive', { target_x: wx, target_y: wy });
                  }}
                  onAnchorClick={(a) => {
                    if (a.label.toLowerCase().includes('charger') || a.label.toLowerCase().includes('dock')) {
                      handleSimulateDock();
                    }
                  }}
                  onSimulateDock={handleSimulateDock}
                  onSpawnBlock={handleSpawnBlock}
                />
              )}
            </div>
          </div>

          {/* 1/3 Width: Interactive Light Cubes (5cm Buffer) & Visual Anchors */}
          <div className="w-full lg:w-1/3 min-w-0 flex flex-col gap-4 min-h-[520px]">
            {/* Card 1: Phase 5 Bidirectional A* & Cubes Manager */}
            <div className="theme-card rounded-2xl p-4 shadow-[0_20px_50px_rgba(0,0,0,0.8)] border border-white/[0.1] flex flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-white/[0.08]">
                <div className="flex items-center gap-2 flex-nowrap">
                  <span className="text-xs font-bold font-mono tracking-wider text-amber-300 flex items-center gap-1.5 whitespace-nowrap">
                    <span>LIGHT CUBES</span>
                  </span>
                  <span className="theme-badge px-2 py-0.5 rounded-md text-[10px] font-mono text-emerald-400 whitespace-nowrap">
                    5cm BUFFER
                  </span>
                </div>
                <div className="dock-nav-bar">
                  <button
                    onClick={handleResetSimulation}
                    className="dock-btn dock-btn-amber h-6 px-2 text-[10px]"
                    title="Reset Cozmo Pose to Origin (0, 0, 0°)"
                  >
                    Reset Pose
                  </button>
                  <button
                    onClick={handleResetBlocks}
                    className="dock-btn h-6 px-2 text-[10px]"
                    title="Reset Default 3-Cube Layout"
                  >
                    Reset Cubes
                  </button>
                  <button
                    onClick={handlePlanPath}
                    className="dock-btn dock-btn-active h-6 px-2 text-[10px]"
                    title="Recalculate Two-Way A* Path"
                  >
                    Replan
                  </button>
                </div>
              </div>

              {/* Cubes List */}
              <div className="grid grid-cols-1 gap-2 max-h-[140px] overflow-y-auto pr-1">
                {(telemetry.blocks || []).map((blk) => (
                  <div
                    key={blk.id}
                    className="flex items-center justify-between bg-white/[0.02] border border-white/[0.07] p-2.5 rounded-xl text-xs font-mono"
                  >
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-sm bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.6)]" />
                      <span className="text-white font-semibold">{blk.label}</span>
                      <span className="text-[10px] text-slate-400">({(blk.x / 10).toFixed(1)}, {(blk.y / 10).toFixed(1)})cm</span>
                    </div>
                    <button
                      onClick={() => handleDeleteBlock(blk.id)}
                      className="w-7 h-7 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/30 flex items-center justify-center transition-all cursor-pointer select-none active:scale-90"
                      title="Remove Block"
                    >
                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>

              {/* 2-Way A* Telemetry Mini HUD */}
              <div className="bg-slate-950/60 p-2.5 rounded-xl border border-purple-500/20 text-[10px] font-mono text-slate-300 grid grid-cols-2 gap-2 shadow-inner">
                <div>
                  <span className="text-slate-500">2-Way A* Waypoints:</span>{' '}
                  <span className="text-purple-300 font-bold">{telemetry.path?.length || 0} pts</span>
                </div>
                <div>
                  <span className="text-slate-500">Path Length:</span>{' '}
                  <span className="text-cyan-300 font-bold">{((telemetry.path_info?.total_length_mm || 0) / 10).toFixed(1)} cm</span>
                </div>
                <div>
                  <span className="text-slate-500">Safety Buffer:</span>{' '}
                  <span className="text-emerald-400 font-bold">5.0 cm (50mm)</span>
                </div>
                <div>
                  <span className="text-slate-500">Compute Time:</span>{' '}
                  <span className="text-amber-300 font-bold">{telemetry.path_info?.execution_time_ms || 1.8} ms</span>
                </div>
              </div>
            </div>

            {/* Card 2: Persistent Visual Anchors */}
            <div className="theme-card rounded-2xl p-4 shadow-[0_20px_50px_rgba(0,0,0,0.8)] border border-white/[0.1] flex flex-col flex-1">
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.08] mb-3">
                <span className="text-xs font-bold text-white flex items-center gap-1.5 font-mono tracking-wider">
                  <svg className={`w-3.5 h-3.5 ${isRoyal ? 'text-amber-400' : isIT ? 'text-emerald-400' : 'text-amber-400'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                  </svg>
                  <span>VISUAL ANCHORS</span>
                </span>
                <span className="theme-badge px-2 py-0.5 rounded-md text-[10px] text-slate-400 font-mono">
                  {telemetry.anchors.length} Nodes
                </span>
              </div>

              <div className="flex-1 overflow-y-auto pr-1 space-y-2">
                {telemetry.anchors.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center p-4 text-slate-500 font-mono text-xs">
                    <p className="text-[11px] text-slate-500">No anchors registered yet</p>
                  </div>
                ) : (
                  telemetry.anchors.map((anchor) => (
                    <div
                      key={anchor.label}
                      className="flex items-center justify-between bg-white/[0.02] border border-white/[0.07] hover:border-white/[0.18] p-2.5 rounded-xl text-xs transition-all"
                    >
                      <div className="flex flex-col gap-0.5">
                        <div className="flex items-center gap-1.5">
                          <span className="text-white font-semibold text-xs">{anchor.label}</span>
                          {anchor.is_locked && (
                            <span className="theme-badge px-1 py-0.2 rounded text-[9px] font-mono text-amber-300 border border-amber-500/40">
                              LOCKED 🔒
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-slate-400 font-mono">({(anchor.x / 10).toFixed(1)}, {(anchor.y / 10).toFixed(1)})cm</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {anchor.label.toLowerCase().includes('charger') && (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={async () => {
                                const action = anchor.is_locked ? 'unlock' : 'lock';
                                await fetch(`http://${apiHost}:${apiPort}/api/cozmo/anchors/${encodeURIComponent(anchor.label)}/${action}`, {
                                  method: 'POST'
                                });
                                setStatusMessage(`Charger coordinates ${action === 'lock' ? 'locked' : 'unlocked'}.`);
                              }}
                              className={`dock-btn ${anchor.is_locked ? 'dock-btn-amber dock-btn-active' : ''} h-6 px-1.5 text-[10px]`}
                              title={anchor.is_locked ? "Click to unlock charger location" : "Click to lock charger location"}
                            >
                              {anchor.is_locked ? '🔒' : '🔓'}
                            </button>
                            <button
                              onClick={handleSimulateDock}
                              className="dock-btn dock-btn-emerald dock-btn-active h-6 px-2 text-[10px]"
                              title="Lock charger and navigate along 2-Way A* trajectory"
                            >
                              Dock
                            </button>
                          </div>
                        )}
                        <button
                          onClick={() => handleDeleteAnchor(anchor.label)}
                          className="w-7 h-7 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/30 flex items-center justify-center transition-all cursor-pointer select-none active:scale-90"
                          title="Delete Anchor"
                        >
                          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Interactive Object Labeling / Teach Modal */}
      {showTeachModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="theme-card rounded-2xl p-6 max-w-md w-full shadow-[0_24px_64px_rgba(0,0,0,0.9)] border border-white/[0.15]">
            <div className="flex items-center gap-3 mb-3">
              <div className="theme-icon-box w-9 h-9 rounded-xl flex items-center justify-center text-white">
                <svg className={`w-4 h-4 ${isRoyal ? 'text-amber-400' : isIT ? 'text-emerald-400' : 'text-cyan-400'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
                  <line x1="7" y1="7" x2="7.01" y2="7" />
                </svg>
              </div>
              <div>
                <h3 className="text-base font-bold text-white">
                  TEACH OBJECT ANCHOR
                </h3>
                <span className="text-[11px] font-mono text-slate-400">
                  NEURAL ZERO-SHOT ANCHOR REGISTRATION
                </span>
              </div>
            </div>

            <p className="text-xs text-slate-300 mb-5 leading-relaxed">
              Enter a descriptor for the selected object (e.g. <code className="text-white bg-white/[0.08] px-1.5 py-0.5 rounded font-mono">ChargingDock</code>, <code className="text-white bg-white/[0.08] px-1.5 py-0.5 rounded font-mono">CoffeeMug</code>, <code className="text-white bg-white/[0.08] px-1.5 py-0.5 rounded font-mono">Operator</code>).
              Its 384-D feature vector and 2D spatial coordinate will be preserved permanently.
            </p>

            <input
              type="text"
              value={teachLabel}
              onChange={(e) => setTeachLabel(e.target.value)}
              placeholder="e.g. ChargingDock..."
              autoFocus
              className="w-full bg-white/[0.04] border border-white/[0.12] rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-white/[0.4] focus:ring-1 focus:ring-white/[0.3] mb-5 font-mono"
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveTeach();
                if (e.key === 'Escape') handleCancelTeach();
              }}
            />

            <div className="flex items-center justify-end gap-2.5">
              <button
                onClick={handleCancelTeach}
                className="dock-btn h-8 px-4 font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveTeach}
                disabled={!teachLabel.trim()}
                className="dock-btn dock-btn-active h-8 px-5 font-bold disabled:opacity-40 disabled:pointer-events-none"
              >
                Save Anchor
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CozmoDashboard;
