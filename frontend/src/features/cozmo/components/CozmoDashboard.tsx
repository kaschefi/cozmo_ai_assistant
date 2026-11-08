import React, { useState, useEffect, useRef, useCallback } from 'react';
import SemanticGridMap, { type VisualAnchorData, type ObstacleData, type RobotPose, type BlockData } from './SemanticGridMap';
import Cozmo3DWorldMap from './Cozmo3DWorldMap';
import Header from '../../../shared/components/layout/Header';
import { useTheme } from '../../../shared/context/ThemeContext';
import {
  ConstellationFieldBackground,
  GoldVeinsBackground,
  ParticleDriftBackground
} from '../../../shared/components/backgrounds';
import { getApiBaseUrl, getWsBaseUrl } from '../../../shared/utils';

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

export interface CozmoDashboardProps {
  onBackToChat?: () => void;
  onBackToLanding?: () => void;
}

/**
 * Cozmo Mission Control Dashboard
 *
 * Cybernetic Physical Embodiment & Frosted Obsidian Glass interface for Anki Cozmo robotics.
 * Integrates dual-pane DINO optical vision, 3D photorealistic digital twin simulation,
 * bidirectional A* path planning with 50mm safety buffer, and persistent neural anchors.
 */
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
  const [isNamingSelectedObject, setIsNamingSelectedObject] = useState<boolean>(false);
  const [clickPos, setClickPos] = useState<{ x: number; y: number } | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('Telemetry stream standby...');
  const [mapViewMode, setMapViewMode] = useState<'2d' | '3d'>('3d');
  const [pressedKeys, setPressedKeys] = useState<Set<string>>(new Set());

  const wsRef = useRef<WebSocket | null>(null);
  const userForcedDisconnectRef = useRef<boolean>(false);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const teachInputRef = useRef<HTMLInputElement | null>(null);

  // Auto-focus input when inline naming bar opens
  useEffect(() => {
    if (isNamingSelectedObject) {
      const timer = setTimeout(() => {
        teachInputRef.current?.focus();
      }, 60);
      return () => clearTimeout(timer);
    }
  }, [isNamingSelectedObject]);

  const apiBaseUrl = getApiBaseUrl();
  const wsBaseUrl = getWsBaseUrl();
  const streamUrl = `${apiBaseUrl}/api/cozmo/video_feed?source=${cameraSource}&v=${streamKey}`;
  const wsUrl = `${wsBaseUrl}/ws/cozmo/telemetry`;

  // Sync initial status (camera source & connection state) on mount
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${apiBaseUrl}/api/cozmo/status`);
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
      } catch {
        // ignore if offline
      }
    };
    fetchStatus();
  }, [apiBaseUrl]);

  // Establish WebSocket Connection (20Hz telemetry)
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

    const connectWs = () => {
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        setStatusMessage('Telemetry Stream Active (20Hz WebSocket)');
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
        } catch {
          // ignore malformed JSON
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        setStatusMessage('Telemetry stream offline. Reconnecting...');
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
    setStatusMessage('Initiating Cozmo Wi-Fi handshake... Ensure PC is linked to Cozmo_XXXXXX');
    try {
      const res = await fetch(`${apiBaseUrl}/api/cozmo/connect`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.status === 'connecting') {
        setStatusMessage('Awaiting robot Wi-Fi link handshake...');
      }
    } catch (e) {
      console.error('Failed to initiate Cozmo connection:', e);
      setStatusMessage('Error contacting backend to connect to Cozmo.');
      setIsConnecting(false);
    }
  }, [apiBaseUrl]);

  // Trigger Cozmo Disconnect
  const handleDisconnectCozmo = useCallback(async () => {
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

    try {
      await fetch(`${apiBaseUrl}/api/cozmo/disconnect`, {
        method: 'POST',
      });
    } catch {
      // ignore
    }
    try {
      await fetch(`${apiBaseUrl}/api/cozmo/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'disconnect' }),
      });
    } catch {
      // ignore
    }
  }, [apiBaseUrl]);

  // Active polling while connection handshake is in progress
  useEffect(() => {
    if (!isConnecting) return;
    let attempts = 0;
    const maxAttempts = 25;
    const interval = setInterval(async () => {
      attempts += 1;
      try {
        const res = await fetch(`${apiBaseUrl}/api/cozmo/status`);
        if (res.ok) {
          const data = await res.json();
          if (data.is_connected) {
            setIsConnecting(false);
            setStatusMessage('Cozmo connected! Hardware link active.');
            setStreamKey(Date.now());
            clearInterval(interval);
            return;
          }
          if (!data.is_connecting && attempts > 3) {
            setIsConnecting(false);
            setStatusMessage('Cozmo connection failed or timed out. Check robot battery & Wi-Fi.');
            clearInterval(interval);
            return;
          }
        }
      } catch {
        // network issue
      }
      if (attempts >= maxAttempts) {
        setIsConnecting(false);
        setStatusMessage('Cozmo connection attempt timed out.');
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isConnecting, apiBaseUrl]);

  // Send Command to Backend API / WebSocket
  const sendCommand = useCallback(async (action: string, params: Record<string, any> = {}) => {
    // Real-time kinematics sent with 0ms latency over WebSocket
    if (['drive', 'stop', 'tilt_head', 'lift', 'headlight', 'reset_simulation'].includes(action)) {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(JSON.stringify({ action, ...params }));
          return { status: 'success', action };
        } catch {
          // fallback to HTTP
        }
      }
    }

    try {
      const res = await fetch(`${apiBaseUrl}/api/cozmo/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, ...params }),
      });
      return await res.json();
    } catch (e) {
      console.error('Command failed:', e);
    }
  }, [apiBaseUrl]);

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
        sendCommand('drive', { speed_mms: speed, turn_rate: steer });

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

  // Keyboard Event Listeners with Visual UI State Feedback
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      const key = e.key.toLowerCase();

      if (['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(key)) {
        activeKeysRef.current.add(key);
        setPressedKeys(new Set(activeKeysRef.current));
      } else if (key === ' ' || key === 'x') {
        activeKeysRef.current.clear();
        activePadDirectionRef.current = null;
        setPressedKeys(new Set());
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
        setPressedKeys(new Set(activeKeysRef.current));
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

  // Handle Video Click to Teach Landmark with pixel-exact letterbox-aware coordinate mapping
  const handleVideoClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const container = e.currentTarget;
    const rect = container.getBoundingClientRect();
    const clickClientX = e.clientX;
    const clickClientY = e.clientY;

    const img = imgRef.current;
    let normX = 0.5;
    let clickY = 0.5;

    if (img && img.naturalWidth && img.naturalHeight) {
      const naturalRatio = img.naturalWidth / img.naturalHeight;
      const containerRatio = rect.width / rect.height;

      let renderedW = rect.width;
      let renderedH = rect.height;
      let padX = 0;
      let padY = 0;

      if (containerRatio > naturalRatio) {
        // Container wider than image: black letterbox bars on left/right
        renderedH = rect.height;
        renderedW = renderedH * naturalRatio;
        padX = (rect.width - renderedW) / 2;
      } else {
        // Container taller than image: black letterbox bars on top/bottom
        renderedW = rect.width;
        renderedH = renderedW / naturalRatio;
        padY = (rect.height - renderedH) / 2;
      }

      const imgPixelX = clickClientX - rect.left - padX;
      const imgPixelY = clickClientY - rect.top - padY;

      const normTotalX = Math.max(0, Math.min(1, imgPixelX / Math.max(1, renderedW)));
      clickY = Math.max(0, Math.min(1, imgPixelY / Math.max(1, renderedH)));

      // In dual-view: left pane is raw camera (0..0.5), right pane is DINO heatmap (0.5..1.0)
      normX = normTotalX < 0.5 ? normTotalX * 2.0 : (normTotalX - 0.5) * 2.0;
    } else {
      const rawClickX = (clickClientX - rect.left) / rect.width;
      clickY = (clickClientY - rect.top) / rect.height;
      normX = rawClickX < 0.5 ? rawClickX * 2.0 : (rawClickX - 0.5) * 2.0;
    }

    const clampedX = Math.max(0, Math.min(1, normX));
    const clampedY = Math.max(0, Math.min(1, clickY));

    setClickPos({ x: clampedX, y: clampedY });
    // Trigger backend DINO connected-component segmentation to display purple box
    sendCommand('select_point', { click_x: clampedX, click_y: clampedY });
    setIsNamingSelectedObject(true);
    setStatusMessage('Object selected! Confirm purple box on stream, enter label below, and press Enter.');
  };

  const handleCancelTeach = useCallback(() => {
    sendCommand('clear_selection');
    setIsNamingSelectedObject(false);
    setTeachLabel('');
    setStatusMessage('Object selection cleared.');
  }, [sendCommand]);

  const handleSaveTeach = useCallback(async () => {
    if (!teachLabel.trim()) return;
    const label = teachLabel.trim();
    setStatusMessage(`Teaching visual anchor '${label}'...`);
    const res = await sendCommand('teach', {
      label,
      click_x: clickPos?.x,
      click_y: clickPos?.y,
    });
    if (res && res.status === 'success') {
      setStatusMessage(`Learned landmark '${label}'! Now tracking in real-time.`);
      try {
        const anchorsRes = await fetch(`${apiBaseUrl}/api/cozmo/anchors`);
        if (anchorsRes.ok) {
          const anchorsData = await anchorsRes.json();
          if (Array.isArray(anchorsData)) {
            setTelemetry((prev) => ({ ...prev, anchors: anchorsData }));
          }
        }
      } catch {
        // ignore network error
      }
    }
    setTeachLabel('');
    setIsNamingSelectedObject(false);
  }, [teachLabel, clickPos, sendCommand, apiBaseUrl]);

  const handleDeleteAnchor = async (label: string) => {
    try {
      await fetch(`${apiBaseUrl}/api/cozmo/anchors/${encodeURIComponent(label)}`, {
        method: 'DELETE',
      });
      setTelemetry((prev) => ({
        ...prev,
        anchors: prev.anchors.filter((a) => a.label !== label),
      }));
    } catch (e) {
      console.error('Delete anchor failed:', e);
    }
  };

  // Autonomous Docking & 2-Way A* Handlers
  const handlePlanPath = useCallback(async () => {
    try {
      setStatusMessage('Calculating Two-Way A* Docking Path (50mm buffer)...');
      const res = await fetch(`${apiBaseUrl}/api/cozmo/plan_dock_path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clearance_mm: 50.0 }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setStatusMessage(
          `Computed 2-Way A* Path: ${data.plan?.waypoints_count} waypoints (${data.plan?.total_length_mm?.toFixed(0)}mm) in ${data.plan?.execution_time_ms}ms`
        );
      } else {
        setStatusMessage(data.detail || 'Path planning failed.');
      }
    } catch (e) {
      console.error('Plan path request failed:', e);
    }
  }, [apiBaseUrl]);

  const handleSimulateDock = useCallback(async () => {
    try {
      setStatusMessage('Locking charger & calculating Two-Way A* path (50mm clearance)...');
      const res = await fetch(`${apiBaseUrl}/api/cozmo/simulation/dock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clearance_mm: 50.0 }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setStatusMessage(
          telemetry.robot.is_connected
            ? 'Autonomous Docking Active: Real Cozmo navigating to charger with 5cm clearance!'
            : 'Simulation Active: Cozmo returning to charger avoiding cubes with 5cm clearance!'
        );
      } else {
        setStatusMessage(data.detail || 'Docking request failed.');
      }
    } catch (e) {
      console.error('Docking request failed:', e);
    }
  }, [apiBaseUrl, telemetry.robot.is_connected]);

  const handleSpawnBlock = useCallback(async (x: number, y: number) => {
    try {
      const blockId = `cube_${Date.now() % 10000}`;
      await fetch(`${apiBaseUrl}/api/cozmo/blocks`, {
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
      setStatusMessage(`Spawned Light Cube at (${(x / 10).toFixed(1)}, ${(y / 10).toFixed(1)})cm.`);
      handlePlanPath();
    } catch (e) {
      console.error('Spawn block failed:', e);
    }
  }, [apiBaseUrl, handlePlanPath]);

  const handleDeleteBlock = useCallback(async (blockId: string) => {
    try {
      await fetch(`${apiBaseUrl}/api/cozmo/blocks/${encodeURIComponent(blockId)}`, {
        method: 'DELETE',
      });
      setStatusMessage(`Deleted block ${blockId}`);
      handlePlanPath();
    } catch (e) {
      console.error('Delete block failed:', e);
    }
  }, [apiBaseUrl, handlePlanPath]);

  const handleResetBlocks = useCallback(async () => {
    try {
      await fetch(`${apiBaseUrl}/api/cozmo/blocks/reset`, {
        method: 'POST',
      });
      setStatusMessage('Reset blocks to default 3-cube layout.');
      handlePlanPath();
    } catch (e) {
      console.error('Reset blocks failed:', e);
    }
  }, [apiBaseUrl, handlePlanPath]);

  const handleResetSimulation = useCallback(async () => {
    try {
      await fetch(`${apiBaseUrl}/api/cozmo/simulation/reset`, {
        method: 'POST',
      });
      setStatusMessage('Simulation reset: Cozmo pose returned to origin (0, 0, 0°).');
    } catch (e) {
      console.error('Reset simulation failed:', e);
    }
  }, [apiBaseUrl]);

  const batteryColor =
    telemetry.robot.battery_voltage >= 3.8
      ? 'text-emerald-400'
      : telemetry.robot.battery_voltage >= 3.65
        ? 'text-amber-400'
        : 'text-rose-400 animate-pulse';

  const isForwardActive = pressedKeys.has('w') || pressedKeys.has('arrowup');
  const isBackwardActive = pressedKeys.has('s') || pressedKeys.has('arrowdown');
  const isLeftActive = pressedKeys.has('a') || pressedKeys.has('arrowleft');
  const isRightActive = pressedKeys.has('d') || pressedKeys.has('arrowright');

  return (
    <div
      className={`relative w-full max-w-full min-h-screen ${isBlackIce ? 'bg-[#020407]' : isRoyal ? 'bg-[#030407]' : isIT ? 'bg-[#020503]' : 'bg-[#030407]'
        } text-slate-100 font-sans select-none overflow-x-hidden overflow-y-auto transition-colors duration-700`}
    >
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
                : 'linear-gradient(180deg, #030407 0%, #05060a 50%, #020305 100%)',
        }}
      />

      {/* Dynamic Shader Canvas per active theme */}
      {isBlackIce && <ConstellationFieldBackground className="fixed inset-0 pointer-events-none z-0" />}
      {isRoyal && <GoldVeinsBackground className="fixed inset-0 pointer-events-none z-0" />}
      {isIT && <ParticleDriftBackground className="fixed inset-0 pointer-events-none z-0" />}

      {/* Royal Atmospheric Warm Glow Orbs */}
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

      {/* Subtle Digital Matrix Dot Overlay */}
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
          backgroundSize: '28px 28px',
        }}
      />

      {/* 1. Global Navigation Bar */}
      <Header defaultActive="cozmo" />

      {/* 2. Flagship Hero & Telemetry Masthead */}
      <header className="relative z-10 pt-28 md:pt-36 pb-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Left Column: Megrim Display Title & Project Narrative */}
          <div className="lg:col-span-7 flex flex-col items-start">
            <div className="relative inline-block mb-3">
              <h1 className="font-megrim text-4xl sm:text-5xl lg:text-6xl text-white tracking-wider leading-[1.15]">
                Cozmo Mission Control
              </h1>
              <div className="brand-underline mt-2.5" />
            </div>

            <p className="text-slate-200 text-base sm:text-lg leading-relaxed mt-3 font-sans">
              <strong style={{ color: 'var(--brand-light)' }} className="font-semibold">
                Autonomous Physical Embodiment
              </strong>{' '}
              bridging MoKa&apos;s cognitive brain with real-world spatial perception, computer vision, and kinetic motor execution.
            </p>

            <p className="text-slate-400 text-xs sm:text-sm leading-relaxed mt-2 font-sans max-w-2xl">
              Equipped with live DINO zero-shot semantic reticle tracking, real-time 3D spatial occupancy mapping, and 2-way A* autonomous charger docking with a 50mm safety buffer.
            </p>

            {/* Quick Hardware Action Bar */}
            <div className="flex flex-wrap items-center gap-3 mt-6">
              {telemetry.robot.is_connected ? (
                <div className="flex items-center gap-2">
                  <div className="theme-badge px-3.5 py-2 rounded-xl flex items-center gap-2.5 font-mono text-xs border-emerald-500/40 bg-emerald-950/60 text-emerald-300 shadow-[0_0_16px_rgba(52,211,153,0.25)]">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_10px_#34d399] animate-pulse" />
                    <span className="font-bold tracking-wider">HARDWARE LINKED</span>
                  </div>
                  <button
                    onClick={handleConnectCozmo}
                    className="dock-btn h-9 px-3 text-xs font-mono flex items-center gap-1.5"
                    title="Reconnect Wi-Fi Handshake"
                  >
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="23 4 23 10 17 10" />
                      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                    </svg>
                    <span>RECONNECT</span>
                  </button>
                  <button
                    onClick={handleDisconnectCozmo}
                    className="dock-btn dock-btn-rose h-9 px-3 text-xs font-mono flex items-center gap-1.5 hover:bg-rose-950/80 transition-all"
                    title="Disconnect Robot Wi-Fi"
                  >
                    <svg className="w-3.5 h-3.5 text-rose-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                    <span>DISCONNECT</span>
                  </button>
                </div>
              ) : isConnecting || telemetry.robot.is_connecting ? (
                <div className="flex items-center gap-2">
                  <button
                    disabled
                    className="theme-badge px-4 py-2 rounded-xl flex items-center gap-2.5 font-mono text-xs border-amber-500/50 bg-amber-950/70 text-amber-300 cursor-wait animate-pulse"
                  >
                    <svg className="w-4 h-4 animate-spin text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span className="font-bold">CONNECTING WI-FI...</span>
                  </button>
                  <button
                    onClick={handleDisconnectCozmo}
                    className="dock-btn dock-btn-rose h-9 px-3 text-xs font-mono"
                    title="Cancel connection attempt"
                  >
                    CANCEL
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleConnectCozmo}
                  className="theme-btn px-6 py-3 rounded-2xl text-white font-bold tracking-wide flex items-center gap-3 cursor-pointer group shadow-[0_12px_32px_rgba(0,0,0,0.6)]"
                  title="Connect via Wi-Fi to Cozmo_XXXXXX"
                >
                  <div className="theme-icon-box w-7 h-7 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                    <svg className="w-4 h-4 text-current" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M5 12.55a11 11 0 0 1 14.08 0" />
                      <path d="M1.42 9a16 16 0 0 1 21.16 0" />
                      <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
                      <line x1="12" y1="20" x2="12.01" y2="20" strokeWidth="3" />
                    </svg>
                  </div>
                  <span className="text-xs sm:text-sm font-semibold tracking-wider">CONNECT TO COZMO</span>
                </button>
              )}

              {/* Status Message Toast */}
              <div className="theme-badge px-3.5 py-2 rounded-xl flex items-center gap-2 font-mono text-[11px] text-slate-300">
                <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-cyan-400 animate-pulse shadow-[0_0_8px_#00f3ff]' : 'bg-rose-500'}`} />
                <span className="truncate max-w-[280px] sm:max-w-md">{statusMessage}</span>
              </div>
            </div>
          </div>

          {/* Right Column: 3 Frosted Glass Telemetry Metrics Cards */}
          <div className="lg:col-span-5 grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-3.5">
            {/* Card 1: Hardware State & Telemetry Link */}
            <div className="theme-card rounded-2xl p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="theme-icon-box w-10 h-10 rounded-xl flex items-center justify-center">
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="4" y="4" width="16" height="16" rx="2" />
                    <rect x="9" y="9" width="6" height="6" />
                    <line x1="9" y1="1" x2="9" y2="4" />
                    <line x1="15" y1="1" x2="15" y2="4" />
                    <line x1="9" y1="20" x2="9" y2="23" />
                    <line x1="15" y1="20" x2="15" y2="23" />
                    <line x1="20" y1="9" x2="23" y2="9" />
                    <line x1="20" y1="14" x2="23" y2="14" />
                    <line x1="1" y1="9" x2="4" y2="9" />
                    <line x1="1" y1="14" x2="4" y2="14" />
                  </svg>
                </div>
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-widest text-slate-400">HARDWARE LINK</div>
                  <div className="text-sm font-bold text-white tracking-wide">
                    {telemetry.robot.is_connected ? 'ROBOT LINKED' : 'STANDBY / WEBCAM'}
                  </div>
                </div>
              </div>
              <span className="theme-badge px-2.5 py-1 rounded-lg text-[10px] font-mono uppercase font-bold text-slate-300">
                {telemetry.robot.action || 'IDLE'}
              </span>
            </div>

            {/* Card 2: Spatial Kinematics Vector */}
            <div className="theme-card rounded-2xl p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="theme-icon-box w-10 h-10 rounded-xl flex items-center justify-center">
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
                  </svg>
                </div>
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-widest text-slate-400">CHASSIS POSE & HEADING</div>
                  <div className="text-sm font-bold text-white font-mono">
                    ({(telemetry.robot.x / 10).toFixed(1)}, {(telemetry.robot.y / 10).toFixed(1)}) cm · {telemetry.robot.theta_deg.toFixed(0)}°
                  </div>
                </div>
              </div>
              <span className="theme-badge px-2.5 py-1 rounded-lg text-[10px] font-mono uppercase text-slate-300">
                HEAD {(telemetry.robot.head_pitch_deg ?? 15) >= 0 ? `+${telemetry.robot.head_pitch_deg ?? 15}` : telemetry.robot.head_pitch_deg}°
              </span>
            </div>

            {/* Card 3: Battery & Perception Telemetry */}
            <div className="theme-card rounded-2xl p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="theme-icon-box w-10 h-10 rounded-xl flex items-center justify-center">
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="7" width="16" height="10" rx="2" />
                    <line x1="22" y1="11" x2="22" y2="13" />
                  </svg>
                </div>
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-widest text-slate-400">BATTERY & PERCEPTION</div>
                  <div className={`text-sm font-bold font-mono ${batteryColor}`}>
                    {telemetry.robot.battery_voltage.toFixed(2)}V · {cameraSource.toUpperCase()}
                  </div>
                </div>
              </div>
              <span className="theme-badge px-2.5 py-1 rounded-lg text-[10px] font-mono uppercase text-slate-300">
                {wsConnected ? '20Hz STREAM' : 'OFFLINE'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* 3. SECTION 1: Neural Vision & Cockpit Pilotage ("The Optical Cortex") */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mb-16">
        <div className="mb-6">
          <div className="relative inline-block mb-2">
            <h2 className="font-megrim text-3xl md:text-4xl text-white tracking-wider">
              Neural Vision & Cockpit Pilotage
            </h2>
            <div className="brand-underline" />
          </div>
          <p className="text-slate-400 text-xs md:text-sm font-mono tracking-wider">
            REAL-TIME DUAL-PANE OPTICAL FEED · DINO ZERO-SHOT RETICLE · ROBOTIC MOTOR PILOTAGE
          </p>
        </div>

        {/* Master Vision & Teleoperation Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* Left: Dual-Pane Optical & DINO Stream Viewport (7 cols) */}
          <div className="lg:col-span-7 flex flex-col">
            <div className="theme-card rounded-3xl overflow-hidden shadow-[0_24px_64px_rgba(0,0,0,0.85)] flex flex-col flex-1">
              {/* Monitor Header */}
              <div className="min-h-14 py-2 px-5 bg-white/[0.02] border-b border-white/[0.08] flex flex-wrap items-center justify-between gap-3 text-xs backdrop-blur-xl">
                <div className="flex items-center gap-2.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_#34d399]" />
                  <span className="font-bold text-white font-mono tracking-wider text-xs sm:text-sm">
                    {cameraSource === 'cozmo' ? 'COZMO DUAL-PANE OPTICAL' : 'WEBCAM DUAL-PANE OPTICAL'}
                  </span>
                  <span className="theme-badge px-2 py-0.5 rounded-md text-[10px] font-mono uppercase font-bold text-emerald-300 border-emerald-500/40">
                    RAW + DINO
                  </span>
                </div>

                {/* Camera Source Selector Dock */}
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">SOURCE:</span>
                  <div className="dock-nav-bar">
                    <button
                      onClick={() => handleSetCameraSource('cozmo')}
                      className={`dock-btn ${cameraSource === 'cozmo' ? 'dock-btn-active' : ''}`}
                      title="Switch to Cozmo robot camera"
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${cameraSource === 'cozmo' ? 'bg-black animate-ping' : 'bg-slate-500'}`} />
                      Cozmo Cam
                    </button>
                    <button
                      onClick={() => handleSetCameraSource('webcam')}
                      className={`dock-btn ${cameraSource === 'webcam' ? 'dock-btn-active' : ''}`}
                      title="Switch to PC webcam"
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${cameraSource === 'webcam' ? 'bg-black animate-ping' : 'bg-slate-500'}`} />
                      PC Webcam
                    </button>
                  </div>
                </div>
              </div>

              {/* Video Stream Canvas */}
              <div
                className="relative aspect-[16/8] md:aspect-[16/7] min-h-[280px] sm:min-h-[340px] w-full bg-black/95 flex items-center justify-center cursor-crosshair overflow-hidden group select-none"
                onClick={handleVideoClick}
                onContextMenu={(e) => {
                  e.preventDefault();
                  handleCancelTeach();
                }}
              >
                <img
                  ref={imgRef}
                  src={streamUrl}
                  alt="Cozmo Optical & DINO Stream"
                  className="w-full h-full object-contain pointer-events-none select-none"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src =
                      'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480"><rect width="640" height="480" fill="%23030407"/><text x="50%" y="50%" fill="%23e4e4e7" font-family="monospace" font-size="14" text-anchor="middle" dominant-baseline="middle">CONNECTING TO VIDEO STREAM...</text></svg>';
                  }}
                />

                {/* Recognized Labels Overlay Chip - only shown when camera feed is actively streaming */}
                {telemetry.detections &&
                  telemetry.detections.length > 0 &&
                  (cameraSource === 'webcam' ? webcamEnabled : telemetry.robot.is_connected) && (
                    <div className="absolute top-3 left-3 bg-emerald-950/85 border border-emerald-500/50 text-emerald-300 px-3 py-1.5 rounded-xl text-xs backdrop-blur-md shadow-xl flex items-center gap-2 pointer-events-none font-mono">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                      <span>
                        RECOGNIZED: {telemetry.detections.map((d) => `${d.label.toUpperCase()} (${(d.confidence * 100).toFixed(0)}%)`).join(', ')}
                      </span>
                    </div>
                  )}

                {/* Selection / Teach Prompt Overlay */}
                {(cameraSource === 'webcam' ? webcamEnabled : telemetry.robot.is_connected) && (
                  <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity bg-black/75 border border-white/10 text-slate-300 px-3 py-1.5 rounded-xl text-[11px] font-mono pointer-events-none backdrop-blur-md">
                    {isNamingSelectedObject ? 'Target acquired · Enter label below' : 'Click object to select · Right-click to clear'}
                  </div>
                )}

                {/* Cozmo Offline State Text (Minimalist Typography - No Box, No Buttons) */}
                {cameraSource === 'cozmo' && !telemetry.robot.is_connected && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center select-none pointer-events-none">
                      <span className="text-sm sm:text-base font-bold text-white font-mono tracking-wider mb-2 uppercase">
                        COZMO NOT CONNECTED
                      </span>
                      <p className="text-xs text-slate-400 font-mono">
                        Cannot connect to Cozmo robot.
                      </p>
                      <p className="text-[11px] text-slate-500 font-mono mt-1">
                        Please connect to Cozmo Wi-Fi or switch to PC Webcam.
                      </p>
                    </div>
                )}

                    {/* Webcam Disabled State Text (Minimalist Typography - No Box, No Buttons) */}
                    {cameraSource === 'webcam' && !webcamEnabled && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center select-none pointer-events-none">
                          <span className="text-sm sm:text-base font-bold text-white font-mono tracking-wider mb-2 uppercase">
                            WEBCAM DISABLED
                          </span>
                          <p className="text-xs text-slate-400 font-mono">
                            Webcam device closed & DINO stopped.
                          </p>
                          <p className="text-[11px] text-slate-500 font-mono mt-1">
                            Click 'Inference (OFF)' button below to re-enable.
                          </p>
                        </div>
                )}
                      </div>

              {/* Inline Landmark Registration Bar (Docked Directly Below Video Canvas) */}
                    {isNamingSelectedObject && (
                      <div className="p-3 bg-gradient-to-r from-fuchsia-950/50 via-purple-950/40 to-black/80 border-t border-fuchsia-500/40 backdrop-blur-xl flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 text-xs animate-in fade-in duration-200">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span className="relative flex h-2.5 w-2.5 shrink-0">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-fuchsia-400 opacity-75" />
                            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-fuchsia-500" />
                          </span>
                          <div className="flex flex-col min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-[11px] font-bold text-fuchsia-300 uppercase tracking-wider">
                                Target Selected (Purple Box)
                              </span>
                              <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">
                                · Verify bounding box on stream above
                              </span>
                            </div>
                            <span className="text-[11px] text-slate-300 truncate">
                              Type landmark name & press <strong className="text-white font-mono">Enter</strong> to register neural anchor
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <div className="relative">
                            <input
                              ref={teachInputRef}
                              type="text"
                              value={teachLabel}
                              onChange={(e) => setTeachLabel(e.target.value)}
                              placeholder="e.g. ME, ChargingDock, CoffeeMug..."
                              className="bg-black/80 border border-fuchsia-500/50 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-fuchsia-400 focus:ring-1 focus:ring-fuchsia-400 font-mono w-48 sm:w-60 shadow-inner"
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  e.preventDefault();
                                  handleSaveTeach();
                                } else if (e.key === 'Escape') {
                                  e.preventDefault();
                                  handleCancelTeach();
                                }
                              }}
                            />
                          </div>
                          <button
                            onClick={handleSaveTeach}
                            disabled={!teachLabel.trim()}
                            className="dock-btn dock-btn-active bg-fuchsia-600 hover:bg-fuchsia-500 text-white font-mono text-xs px-3.5 py-1.5 disabled:opacity-40 disabled:pointer-events-none"
                            title="Register object anchor (Enter)"
                          >
                            <span>Save (↵)</span>
                          </button>
                          <button
                            onClick={handleCancelTeach}
                            className="dock-btn hover:bg-white/10 text-slate-300 font-mono text-xs px-2.5 py-1.5"
                            title="Clear selection (Esc)"
                          >
                            <span>Cancel (Esc)</span>
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Bottom Integrated Vision Deck */}
                    <div className="p-3 bg-white/[0.02] border-t border-white/[0.08] flex flex-wrap items-center justify-between gap-3 text-xs backdrop-blur-xl">
                      <div className="flex items-center gap-2">
                        {/* Headlights Toggle */}
                        <button
                          onClick={() => sendCommand('headlight')}
                          className={`dock-btn ${telemetry.robot.headlight_on ? 'dock-btn-amber dock-btn-active' : ''}`}
                          title="Toggle Cozmo LED headlights"
                        >
                          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="5" />
                            <line x1="12" y1="1" x2="12" y2="3" />
                            <line x1="12" y1="21" x2="12" y2="23" />
                          </svg>
                          <span>Headlights ({telemetry.robot.headlight_on ? 'ON' : 'OFF'})</span>
                        </button>

                        {/* Webcam Toggle */}
                        <button
                          onClick={async () => {
                            const targetState = !webcamEnabled;
                            setWebcamEnabled(targetState);
                            try {
                              const res = await sendCommand('toggle_webcam', { enabled: targetState });
                              if (res && typeof res.webcam_enabled === 'boolean') {
                                setWebcamEnabled(res.webcam_enabled);
                              }
                            } catch (err) {
                              console.error('Toggle webcam failed:', err);
                            }
                            setStreamKey(Date.now());
                          }}
                          className={`dock-btn ${webcamEnabled ? 'dock-btn-emerald dock-btn-active' : 'dock-btn-rose'}`}
                          title="Toggle PC Webcam Inference Engine"
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${webcamEnabled ? 'bg-black animate-ping' : 'bg-rose-400'}`} />
                          <span>Inference ({webcamEnabled ? 'ON' : 'OFF'})</span>
                        </button>
                      </div>

                      {/* Brightness Controls */}
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-slate-400 font-mono uppercase">BRIGHT:</span>
                        <button
                          onClick={() => sendCommand('brightness', { delta: -10 })}
                          className="dock-btn h-7 px-2 text-[10px]"
                          title="Dim video stream"
                        >
                          -10
                        </button>
                        <button
                          onClick={() => sendCommand('brightness', { delta: 10 })}
                          className="dock-btn h-7 px-2 text-[10px]"
                          title="Brighten video stream"
                        >
                          +10
                        </button>
                      </div>
                    </div>
                  </div>
          </div>

              {/* Right: Cockpit Teleoperation Console (5 cols) */}
              <div className="lg:col-span-5 flex flex-col">
                <div className="theme-card rounded-3xl p-6 flex flex-col justify-between flex-1 shadow-[0_24px_64px_rgba(0,0,0,0.85)]">
                  <div>
                    <div className="flex items-center justify-between border-b border-white/[0.08] pb-3 mb-5">
                      <div className="flex items-center gap-2.5">
                        <div className="theme-icon-box w-8 h-8 rounded-xl flex items-center justify-center">
                          <svg className="w-4 h-4 text-current" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <polygon points="5 3 19 12 5 21 5 3" />
                          </svg>
                        </div>
                        <div>
                          <h3 className="text-sm font-bold text-white tracking-wide font-mono">KINEMATICS PILOT DECK</h3>
                          <p className="text-[10px] text-slate-400 font-mono tracking-wider">MOTOR DRIVE & HEAD PITCH</p>
                        </div>
                      </div>
                      <span className="theme-badge px-2.5 py-1 rounded-md text-[10px] font-mono text-cyan-300">
                        20Hz DIRECT
                      </span>
                    </div>

                    {/* Tactile Virtual D-Pad with Live Keyboard Press Illumination */}
                    <div className="flex flex-col items-center justify-center my-4">
                      <div className="flex flex-col items-center gap-2">
                        {/* Forward (W) */}
                        <button
                          onPointerDown={() => startContinuousDriving('forward')}
                          onPointerUp={stopContinuousDriving}
                          onPointerLeave={stopContinuousDriving}
                          className={`theme-btn w-14 h-14 rounded-2xl flex flex-col items-center justify-center font-bold text-sm text-white transition-all cursor-pointer select-none active:scale-95 ${isForwardActive ? 'dock-btn-active scale-105' : 'hover:scale-105'
                            }`}
                          title="Drive Forward (W / Up Arrow)"
                        >
                          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="18 15 12 9 6 15" />
                          </svg>
                          <span className="text-[9px] font-mono text-slate-400 mt-0.5 font-bold">W</span>
                        </button>

                        {/* Middle Row: Left (A), Stop, Right (D) */}
                        <div className="flex items-center gap-2">
                          <button
                            onPointerDown={() => startContinuousDriving('left')}
                            onPointerUp={stopContinuousDriving}
                            onPointerLeave={stopContinuousDriving}
                            className={`theme-btn w-14 h-14 rounded-2xl flex flex-col items-center justify-center font-bold text-sm text-white transition-all cursor-pointer select-none active:scale-95 ${isLeftActive ? 'dock-btn-active scale-105' : 'hover:scale-105'
                              }`}
                            title="Turn Left (A / Left Arrow)"
                          >
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="15 18 9 12 15 6" />
                            </svg>
                            <span className="text-[9px] font-mono text-slate-400 mt-0.5 font-bold">A</span>
                          </button>

                          {/* Emergency Brake Button */}
                          <button
                            onClick={stopContinuousDriving}
                            className="w-14 h-14 rounded-2xl bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/50 text-rose-300 flex flex-col items-center justify-center font-bold text-xs transition cursor-pointer select-none active:scale-90 shadow-lg"
                            title="Emergency Brake (Space / X)"
                          >
                            <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
                              <rect x="4" y="4" width="16" height="16" rx="2" />
                            </svg>
                            <span className="text-[8px] font-mono text-rose-300 mt-0.5 font-bold">STOP</span>
                          </button>

                          <button
                            onPointerDown={() => startContinuousDriving('right')}
                            onPointerUp={stopContinuousDriving}
                            onPointerLeave={stopContinuousDriving}
                            className={`theme-btn w-14 h-14 rounded-2xl flex flex-col items-center justify-center font-bold text-sm text-white transition-all cursor-pointer select-none active:scale-95 ${isRightActive ? 'dock-btn-active scale-105' : 'hover:scale-105'
                              }`}
                            title="Turn Right (D / Right Arrow)"
                          >
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="9 18 15 12 9 6" />
                            </svg>
                            <span className="text-[9px] font-mono text-slate-400 mt-0.5 font-bold">D</span>
                          </button>
                        </div>

                        {/* Backward (S) */}
                        <button
                          onPointerDown={() => startContinuousDriving('backward')}
                          onPointerUp={stopContinuousDriving}
                          onPointerLeave={stopContinuousDriving}
                          className={`theme-btn w-14 h-14 rounded-2xl flex flex-col items-center justify-center font-bold text-sm text-white transition-all cursor-pointer select-none active:scale-95 ${isBackwardActive ? 'dock-btn-active scale-105' : 'hover:scale-105'
                            }`}
                          title="Drive Backward (S / Down Arrow)"
                        >
                          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="6 9 12 15 18 9" />
                          </svg>
                          <span className="text-[9px] font-mono text-slate-400 mt-0.5 font-bold">S</span>
                        </button>
                      </div>
                    </div>

                    {/* Head Tilt Steppers & Presets */}
                    <div className="mt-4 pt-4 border-t border-white/[0.08]">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-mono font-semibold text-slate-300">HEAD PITCH CONTROL</span>
                        <span className="text-xs font-mono font-bold text-white">
                          {(telemetry.robot.head_pitch_deg ?? 15) >= 0 ? `+${telemetry.robot.head_pitch_deg ?? 15}` : telemetry.robot.head_pitch_deg}°
                        </span>
                      </div>
                      <div className="dock-nav-bar w-full justify-between">
                        <button
                          onClick={() => sendCommand('tilt_head', { angle_deg: -20 })}
                          className="dock-btn flex-1 h-7 text-[10px]"
                        >
                          -20° Floor
                        </button>
                        <button
                          onClick={() => sendCommand('tilt_head', { angle_deg: 0 })}
                          className="dock-btn flex-1 h-7 text-[10px]"
                        >
                          0° Level
                        </button>
                        <button
                          onClick={() => sendCommand('tilt_head', { angle_deg: 15 })}
                          className="dock-btn flex-1 h-7 text-[10px]"
                        >
                          +15° Horizon
                        </button>
                        <button
                          onClick={() => sendCommand('tilt_head', { angle_deg: 40 })}
                          className="dock-btn flex-1 h-7 text-[10px]"
                        >
                          +40° Sky
                        </button>
                      </div>
                    </div>

                    {/* Autonomous Mission Shortcut */}
                    <div className="mt-4 pt-4 border-t border-white/[0.08]">
                      <button
                        onClick={handleSimulateDock}
                        className="w-full theme-btn py-3 rounded-xl flex items-center justify-center gap-2.5 font-mono text-xs font-bold text-white hover:scale-[1.02] active:scale-98 transition shadow-lg cursor-pointer"
                        title="Lock charger and navigate along 2-way A* trajectory"
                      >
                        <svg className="w-4 h-4 text-amber-400 fill-current" viewBox="0 0 24 24">
                          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                        </svg>
                        <span>AUTONOMOUS RETURN-TO-DOCK</span>
                      </button>
                    </div>
                  </div>

                  {/* Keyboard Shortcuts Prompt */}
                  <div className="text-center font-mono text-[10px] text-slate-500 mt-4 pt-3 border-t border-white/[0.05]">
                    WASD / Arrows (Drive) · Space (Stop) · I / K (Head) · O (Lights)
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* 4. SECTION 2: Spatial Intelligence & Neural Memory ("The Spatial Mind") */}
          <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
            <div className="mb-6">
              <div className="relative inline-block mb-2">
                <h2 className="font-megrim text-3xl md:text-4xl text-white tracking-wider">
                  Spatial Map & Neural Memory
                </h2>
                <div className="brand-underline" />
              </div>
              <p className="text-slate-400 text-xs md:text-sm font-mono tracking-wider">
                3D PHOTOREALISTIC DIGITAL TWIN · 2D OCCUPANCY GRID · PERSISTENT ZERO-SHOT LANDMARKS
              </p>
            </div>

            {/* Master Spatial Grid (2/3 Map and 1/3 Intelligence Deck) */}
            <div className="flex flex-col lg:flex-row gap-6 w-full items-stretch">
              {/* 2/3 Width: World Map Viewport (3D Digital Twin or 2D Semantic Grid) */}
              <div className="w-full lg:w-2/3 min-w-0 theme-card rounded-3xl overflow-hidden flex flex-col min-h-[580px] shadow-[0_24px_64px_rgba(0,0,0,0.85)]">
                {/* Viewport Control Bar */}
                <div className="h-14 bg-white/[0.02] border-b border-white/[0.08] px-5 flex items-center justify-between text-xs backdrop-blur-xl">
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-white flex items-center gap-2 font-mono tracking-wider text-xs sm:text-sm">
                      <svg className="w-4 h-4 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
                        <line x1="8" y1="2" x2="8" y2="18" />
                        <line x1="16" y1="6" x2="16" y2="22" />
                      </svg>
                      <span>{mapViewMode === '3d' ? '3D COZMO DIGITAL TWIN' : '2D SEMANTIC OCCUPANCY MAP'}</span>
                    </span>

                    {/* 2D / 3D Mode Toggle Switch */}
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

                  {/* Dynamic Pose Pill */}
                  <div className="flex items-center gap-3">
                    <span className="theme-badge px-3 py-1 rounded-lg text-xs font-mono text-slate-300">
                      Pose: ({(telemetry.robot.x / 10).toFixed(1)}, {(telemetry.robot.y / 10).toFixed(1)})cm | Heading: {telemetry.robot.theta_deg.toFixed(0)}°
                    </span>
                  </div>
                </div>

                {/* Canvas Viewport */}
                <div className="flex-1 relative min-h-[520px]">
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

              {/* 1/3 Width: Cubes & Neural Memory Sidebar */}
              <div className="w-full lg:w-1/3 min-w-0 flex flex-col gap-5 min-h-[580px]">
                {/* Card 1: Phase 5 Bidirectional A* & Light Cubes */}
                <div className="theme-card rounded-3xl p-5 shadow-[0_24px_64px_rgba(0,0,0,0.85)] flex flex-col gap-3.5">
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-white/[0.08]">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold font-mono tracking-wider text-amber-300 flex items-center gap-1.5">
                        LIGHT CUBES
                      </span>
                      <span className="theme-badge px-2 py-0.5 rounded-md text-[10px] font-mono text-emerald-400">
                        50mm BUFFER
                      </span>
                    </div>
                    <div className="dock-nav-bar">
                      <button
                        onClick={handleResetSimulation}
                        className="dock-btn dock-btn-amber h-6 px-2 text-[10px]"
                        title="Reset Cozmo pose to origin (0, 0, 0°)"
                      >
                        Reset Pose
                      </button>
                      <button
                        onClick={handleResetBlocks}
                        className="dock-btn h-6 px-2 text-[10px]"
                        title="Reset default 3-cube layout"
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
                        className="flex items-center justify-between bg-white/[0.02] border border-white/[0.07] p-2.5 rounded-xl text-xs font-mono hover:border-white/[0.18] transition"
                      >
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-sm bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.6)]" />
                          <span className="text-white font-semibold">{blk.label}</span>
                          <span className="text-[10px] text-slate-400">
                            ({(blk.x / 10).toFixed(1)}, {(blk.y / 10).toFixed(1)})cm
                          </span>
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

                  {/* 2-Way A* Telemetry Matrix HUD */}
                  <div className="bg-black/40 p-3 rounded-2xl border border-white/[0.08] text-[10px] font-mono text-slate-300 grid grid-cols-2 gap-2 shadow-inner">
                    <div>
                      <span className="text-slate-500">2-Way Waypoints:</span>{' '}
                      <span className="text-cyan-300 font-bold">{telemetry.path?.length || 0} pts</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Path Length:</span>{' '}
                      <span className="text-white font-bold">{((telemetry.path_info?.total_length_mm || 0) / 10).toFixed(1)} cm</span>
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

                {/* Card 2: Persistent Visual Anchors & Neural Memory */}
                <div className="theme-card rounded-3xl p-5 shadow-[0_24px_64px_rgba(0,0,0,0.85)] flex flex-col flex-1">
                  <div className="flex items-center justify-between pb-3 border-b border-white/[0.08] mb-3">
                    <span className="text-xs font-bold text-white flex items-center gap-1.5 font-mono tracking-wider">
                      <svg className="w-3.5 h-3.5 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                      </svg>
                      <span>NEURAL VISUAL ANCHORS</span>
                    </span>
                    <span className="theme-badge px-2.5 py-0.5 rounded-md text-[10px] text-slate-400 font-mono">
                      {telemetry.anchors.length} Registered
                    </span>
                  </div>

                  <div className="flex-1 overflow-y-auto pr-1 space-y-2">
                    {telemetry.anchors.length === 0 ? (
                      <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 font-mono text-xs">
                        <svg className="w-8 h-8 text-slate-600 mb-2 opacity-60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                          <circle cx="12" cy="12" r="10" />
                          <line x1="12" y1="8" x2="12" y2="12" />
                          <line x1="12" y1="16" x2="12.01" y2="16" />
                        </svg>
                        <p className="text-slate-400 font-semibold mb-1">No Neural Anchors Yet</p>
                        <p className="text-[11px] text-slate-500">Click anywhere on the live camera stream to register an object landmark.</p>
                      </div>
                    ) : (
                      telemetry.anchors.map((anchor) => (
                        <div
                          key={anchor.label}
                          className="flex items-center justify-between bg-white/[0.02] border border-white/[0.07] hover:border-white/[0.18] p-3 rounded-2xl text-xs transition-all"
                        >
                          <div className="flex flex-col gap-0.5">
                            <div className="flex items-center gap-1.5">
                              <span className="text-white font-semibold text-xs font-mono">{anchor.label}</span>
                              {anchor.is_locked && (
                                <span className="theme-badge px-1.5 py-0.2 rounded text-[9px] font-mono text-amber-300 border border-amber-500/40">
                                  LOCKED
                                </span>
                              )}
                            </div>
                            <span className="text-[10px] text-slate-400 font-mono">
                              ({(anchor.x / 10).toFixed(1)}, {(anchor.y / 10).toFixed(1)})cm
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            {anchor.label.toLowerCase().includes('charger') && (
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={async () => {
                                    const action = anchor.is_locked ? 'unlock' : 'lock';
                                    await fetch(`${apiBaseUrl}/api/cozmo/anchors/${encodeURIComponent(anchor.label)}/${action}`, {
                                      method: 'POST',
                                    });
                                    setStatusMessage(`Charger coordinates ${action === 'lock' ? 'locked' : 'unlocked'}.`);
                                  }}
                                  className={`dock-btn ${anchor.is_locked ? 'dock-btn-amber dock-btn-active' : ''} h-6 px-1.5 text-[10px]`}
                                  title={anchor.is_locked ? 'Click to unlock location' : 'Click to lock location'}
                                >
                                  {anchor.is_locked ? '🔒' : '🔓'}
                                </button>
                                <button
                                  onClick={handleSimulateDock}
                                  className="dock-btn dock-btn-emerald dock-btn-active h-6 px-2 text-[10px]"
                                  title="Navigate to charger along 2-way A* trajectory"
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

        </div>
        );
};

        export default CozmoDashboard;
