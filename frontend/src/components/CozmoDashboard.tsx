import React, { useState, useEffect, useRef, useCallback } from 'react';
import SemanticGridMap, { type VisualAnchorData, type ObstacleData, type RobotPose } from './SemanticGridMap';

interface TelemetryData {

  robot: RobotPose & {
    battery_voltage: number;
    headlight_on: boolean;
    state: string;
    action: string;
    lift_height_mm: number;
  };
  anchors: VisualAnchorData[];
  obstacles: ObstacleData[];
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
  onBackToChat,
  onBackToLanding,
}) => {
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
      state: 'STANDBY',
      action: 'IDLE',
    },
    anchors: [],
    obstacles: [],
    detections: [],
    path: [],
  });

  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [teachLabel, setTeachLabel] = useState<string>('');
  const [showTeachModal, setShowTeachModal] = useState<boolean>(false);
  const [clickPos, setClickPos] = useState<{ x: number; y: number } | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('Connecting to Cozmo WebSocket...');
  const [activeTab, setActiveTab] = useState<'stream' | 'map' | 'split'>('split');
  const wsRef = useRef<WebSocket | null>(null);

  const apiHost = window.location.hostname || 'localhost';
  const apiPort = '8000';
  const streamUrl = `http://${apiHost}:${apiPort}/api/cozmo/video_feed`;
  const wsUrl = `ws://${apiHost}:${apiPort}/ws/cozmo/telemetry`;

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
          setTelemetry(data);
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

  // Send Command to Backend API
  const sendCommand = useCallback(async (action: string, params: Record<string, any> = {}) => {
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

  // Keyboard Shortcuts (WASD Drive + Head Tilt + Space Stop)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'w':
          sendCommand('drive', { speed_mms: 60.0 });
          break;
        case 's':
          sendCommand('drive', { speed_mms: -60.0 });
          break;
        case 'a':
          sendCommand('drive', { turn_rate: 45.0 });
          break;
        case 'd':
          sendCommand('drive', { turn_rate: -45.0 });
          break;
        case ' ':
        case 'x':
          sendCommand('stop');
          break;
        case 'i':
          sendCommand('tilt_head', { angle_deg: Math.min(44, (telemetry.robot.head_pitch_deg || 15) + 6) });
          break;
        case 'k':
          sendCommand('tilt_head', { angle_deg: Math.max(-25, (telemetry.robot.head_pitch_deg || 15) - 6) });
          break;
        case 'o':
        case 'p':
          sendCommand('headlight');
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [sendCommand, telemetry.robot.head_pitch_deg]);

  // Handle Video Click to Teach
  const handleVideoClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = (e.clientX - rect.left) / rect.width;
    const clickY = (e.clientY - rect.top) / rect.height;
    setClickPos({ x: clickX, y: clickY });
    setShowTeachModal(true);
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

  const batteryColor =
    telemetry.robot.battery_voltage >= 3.8
      ? 'text-emerald-400'
      : telemetry.robot.battery_voltage >= 3.65
      ? 'text-amber-400'
      : 'text-rose-500 animate-pulse';

  return (
    <div className="w-screen h-screen flex flex-col bg-[#07090e] text-slate-100 font-sans select-none overflow-hidden">
      {/* 1. Futuristic Mission Control Header */}
      <header className="h-14 bg-slate-950/90 border-b border-cyan-900/40 px-5 flex items-center justify-between backdrop-blur-md z-30">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">🤖</span>
            <h1 className="text-base font-bold tracking-wider text-cyan-300 flex items-center gap-2">
              COZMO AUTONOMOUS MISSION CONTROL
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-400 border border-cyan-700/50">
                v5.2
              </span>
            </h1>
          </div>

          <div className="h-4 w-px bg-slate-800" />

          {/* Telemetry Status Badges */}
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
              <span>🔋</span>
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


        {/* View Mode & Nav Links */}
        <div className="flex items-center gap-3">
          <div className="flex bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setActiveTab('stream')}
              className={`px-3 py-1 rounded transition ${activeTab === 'stream' ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-white'}`}
            >
              📹 Camera Feed
            </button>
            <button
              onClick={() => setActiveTab('split')}
              className={`px-3 py-1 rounded transition ${activeTab === 'split' ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-white'}`}
            >
              🔲 Split View
            </button>
            <button
              onClick={() => setActiveTab('map')}
              className={`px-3 py-1 rounded transition ${activeTab === 'map' ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-white'}`}
            >
              🗺️ 2D Semantic Map
            </button>
          </div>

          <div className="h-4 w-px bg-slate-800" />

          {onBackToChat && (
            <button
              onClick={onBackToChat}
              className="px-3 py-1.5 text-xs font-semibold text-cyan-300 bg-cyan-950/60 hover:bg-cyan-900 border border-cyan-800/60 rounded-md transition flex items-center gap-1.5"
            >
              💬 MoKa Chat
            </button>
          )}

          {onBackToLanding && (
            <button
              onClick={onBackToLanding}
              className="px-3 py-1.5 text-xs font-semibold text-slate-400 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-md transition"
            >
              🏠 Home
            </button>
          )}
        </div>
      </header>

      {/* 2. Main Mission Control Work Area */}
      <div className="flex-1 flex overflow-hidden p-3 gap-3">
        {/* LEFT VIEWPORT: Live Video & DINO Heatmap Feed */}
        {(activeTab === 'stream' || activeTab === 'split') && (
          <div className={`relative flex flex-col bg-slate-950 rounded-xl border border-cyan-900/40 overflow-hidden ${activeTab === 'split' ? 'w-1/2' : 'w-full'}`}>
            <div className="h-9 bg-slate-900/90 border-b border-slate-800/80 px-4 flex items-center justify-between text-xs">
              <span className="font-bold text-cyan-400 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                LIVE DINO VISION STREAM
              </span>
              <div className="flex items-center gap-2 text-slate-400">
                <span className="text-[11px] bg-slate-800 px-2 py-0.5 rounded text-cyan-300">
                  {telemetry.robot.action}
                </span>
                <span className="text-[11px]">Click object on stream to Teach</span>
              </div>
            </div>

            {/* Video Canvas / Stream Container */}
            <div
              className="relative flex-1 bg-black flex items-center justify-center cursor-crosshair overflow-hidden group"
              onClick={handleVideoClick}
            >
              <img
                src={streamUrl}
                alt="Cozmo DINO Live Vision Stream"
                className="w-full h-full object-contain pointer-events-none"
                onError={(e) => {
                  (e.target as HTMLImageElement).src =
                    'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480"><rect width="640" height="480" fill="%23090d16"/><text x="50%" y="50%" fill="%2300f0ff" font-family="monospace" font-size="16" text-anchor="middle" dominant-baseline="middle">CONNECTING TO COZMO VIDEO STREAM...</text></svg>';
                }}
              />

              {/* Detections Overlay Banner */}
              {telemetry.detections && telemetry.detections.length > 0 && (
                <div className="absolute top-3 left-3 bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 px-3 py-1 rounded-md text-xs backdrop-blur-md shadow-lg flex items-center gap-2 pointer-events-none">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  <span>
                    RECOGNIZED: {telemetry.detections.map((d) => `${d.label.toUpperCase()} (${(d.confidence * 100).toFixed(0)}%)`).join(', ')}
                  </span>
                </div>
              )}

              {/* Quick Stream Controls Overlay */}
              <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity bg-slate-950/80 backdrop-blur-md p-2 rounded-lg border border-slate-800">
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      sendCommand('headlight');
                    }}
                    className={`px-3 py-1 rounded text-xs font-semibold border transition ${
                      telemetry.robot.headlight_on
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/60 shadow-[0_0_10px_rgba(245,158,11,0.3)]'
                        : 'bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800'
                    }`}
                  >
                    💡 Headlights ({telemetry.robot.headlight_on ? 'ON' : 'OFF'})
                  </button>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      sendCommand('brightness', { delta: 10 });
                    }}
                    className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 rounded text-xs"
                    title="Increase Camera Brightness"
                  >
                    ☀️ +10
                  </button>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      sendCommand('brightness', { delta: -10 });
                    }}
                    className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 rounded text-xs"
                    title="Decrease Camera Brightness"
                  >
                    🌙 -10
                  </button>
                </div>

                <span className="text-[11px] text-cyan-300">
                  Left-Click stream to label an object
                </span>
              </div>
            </div>
          </div>
        )}

        {/* RIGHT VIEWPORT: 2D Interactive Semantic Grid Map & Anchors Inspector */}
        {(activeTab === 'map' || activeTab === 'split') && (
          <div className={`flex flex-col gap-3 ${activeTab === 'split' ? 'w-1/2' : 'w-full'}`}>
            {/* 2D Interactive Canvas */}
            <div className="flex-1 bg-slate-950 rounded-xl border border-cyan-900/40 overflow-hidden flex flex-col">
              <div className="h-9 bg-slate-900/90 border-b border-slate-800/80 px-4 flex items-center justify-between text-xs">
                <span className="font-bold text-cyan-300 flex items-center gap-2">
                  🗺️ 2D SEMANTIC WORLD MAP
                </span>
                <span className="text-[11px] text-slate-400 font-mono">
                  Pose: ({telemetry.robot.x.toFixed(0)}, {telemetry.robot.y.toFixed(0)}) | Hdg: {telemetry.robot.theta_deg.toFixed(0)}°
                </span>
              </div>

              <div className="flex-1 relative">
                <SemanticGridMap
                  robot={telemetry.robot}
                  anchors={telemetry.anchors}
                  obstacles={telemetry.obstacles}
                  path={telemetry.path}
                  onPointClick={(wx, wy) => {
                    sendCommand('drive', { target_x: wx, target_y: wy });
                  }}
                  onAnchorClick={(a) => {
                    if (a.label.toLowerCase().includes('charger') || a.label.toLowerCase().includes('dock')) {
                      sendCommand('dock');
                    }
                  }}
                />
              </div>
            </div>

            {/* Persistent Visual Anchors List Card */}
            <div className="h-40 bg-slate-950 rounded-xl border border-cyan-900/40 p-3 flex flex-col overflow-hidden">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 mb-2">
                <span className="text-xs font-bold text-cyan-300 flex items-center gap-1.5">
                  ⭐ PERSISTENT VISUAL ANCHORS ({telemetry.anchors.length})
                </span>
                <span className="text-[10px] text-slate-500">Auto-Relocated on Move</span>
              </div>

              <div className="flex-1 overflow-y-auto pr-1 space-y-1.5">
                {telemetry.anchors.length === 0 ? (
                  <div className="text-center text-xs text-slate-500 py-3">
                    No visual anchors saved yet. Click an object on the camera stream to teach it!
                  </div>
                ) : (
                  telemetry.anchors.map((anchor) => (
                    <div
                      key={anchor.label}
                      className="flex items-center justify-between bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-lg text-xs hover:border-cyan-700/60 transition"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-cyan-400 font-semibold">{anchor.label}</span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          ({anchor.x.toFixed(0)}, {anchor.y.toFixed(0)})mm
                        </span>
                        <span className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
                          Hits: {anchor.observation_count || 1}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {anchor.label.toLowerCase().includes('charger') && (
                          <button
                            onClick={() => sendCommand('dock')}
                            className="px-2 py-0.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/50 rounded text-[11px] transition"
                          >
                            ⚡ Dock
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteAnchor(anchor.label)}
                          className="text-rose-400 hover:text-rose-300 text-xs px-1.5 py-0.5 rounded hover:bg-rose-950/40 transition"
                          title="Delete Anchor"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 3. Bottom Robot Teleoperation Deck */}
      <footer className="h-20 bg-slate-950 border-t border-cyan-900/40 px-5 flex items-center justify-between z-20">
        {/* Driving D-Pad */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <button
              onMouseDown={() => sendCommand('drive', { turn_rate: 40.0 })}
              onMouseUp={() => sendCommand('stop')}
              className="w-10 h-10 bg-slate-900 hover:bg-cyan-600 active:bg-cyan-500 text-white rounded-lg border border-slate-800 flex items-center justify-center font-bold text-sm transition shadow"
              title="Turn Left (A)"
            >
              ◀
            </button>
            <div className="flex flex-col gap-1.5">
              <button
                onMouseDown={() => sendCommand('drive', { speed_mms: 60.0 })}
                onMouseUp={() => sendCommand('stop')}
                className="w-10 h-10 bg-slate-900 hover:bg-cyan-600 active:bg-cyan-500 text-white rounded-lg border border-slate-800 flex items-center justify-center font-bold text-sm transition shadow"
                title="Drive Forward (W)"
              >
                ▲
              </button>
              <button
                onMouseDown={() => sendCommand('drive', { speed_mms: -60.0 })}
                onMouseUp={() => sendCommand('stop')}
                className="w-10 h-10 bg-slate-900 hover:bg-cyan-600 active:bg-cyan-500 text-white rounded-lg border border-slate-800 flex items-center justify-center font-bold text-sm transition shadow"
                title="Drive Backward (S)"
              >
                ▼
              </button>
            </div>
            <button
              onMouseDown={() => sendCommand('drive', { turn_rate: -40.0 })}
              onMouseUp={() => sendCommand('stop')}
              className="w-10 h-10 bg-slate-900 hover:bg-cyan-600 active:bg-cyan-500 text-white rounded-lg border border-slate-800 flex items-center justify-center font-bold text-sm transition shadow"
              title="Turn Right (D)"
            >
              ▶
            </button>
          </div>

          <button
            onClick={() => sendCommand('stop')}
            className="h-10 px-3 bg-rose-950/60 hover:bg-rose-900 border border-rose-800/80 text-rose-300 rounded-lg text-xs font-bold transition flex items-center gap-1"
          >
            🛑 STOP
          </button>
        </div>

        {/* Head Tilt & Lift Arm Controls */}
        <div className="flex items-center gap-4">
          <div className="flex flex-col items-center gap-1">
            <span className="text-[10px] text-slate-400 font-semibold tracking-wide">HEAD PITCH</span>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => sendCommand('tilt_head', { angle_deg: Math.min(44, (telemetry.robot.head_pitch_deg || 15) + 6) })}
                className="px-2.5 py-1 bg-slate-900 hover:bg-cyan-600 text-slate-200 border border-slate-800 rounded text-xs transition"
              >
                UP (+5°)
              </button>
              <button
                onClick={() => sendCommand('tilt_head', { angle_deg: 0 })}
                className="px-2 py-1 bg-slate-900 hover:bg-slate-800 text-slate-400 border border-slate-800 rounded text-xs transition"
              >
                0°
              </button>
              <button
                onClick={() => sendCommand('tilt_head', { angle_deg: Math.max(-25, (telemetry.robot.head_pitch_deg || 15) - 6) })}
                className="px-2.5 py-1 bg-slate-900 hover:bg-cyan-600 text-slate-200 border border-slate-800 rounded text-xs transition"
              >
                DN (-5°)
              </button>
            </div>
          </div>

          <div className="h-8 w-px bg-slate-800" />

          {/* Quick Action Dock & Explore */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => sendCommand('dock')}
              className="px-4 py-2 bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-slate-950 font-bold rounded-lg text-xs shadow-[0_0_12px_rgba(245,158,11,0.35)] transition flex items-center gap-1.5"
            >
              ⚡ DOCK AT CHARGER
            </button>
          </div>
        </div>

        {/* Status Prompt */}
        <div className="text-right">
          <div className="text-[11px] text-cyan-400 font-mono">{statusMessage}</div>
          <div className="text-[10px] text-slate-500">
            Keyboard: WASD (Drive) | Space (Stop) | I/K (Head Tilt) | O (Headlight)
          </div>
        </div>
      </footer>

      {/* 4. Interactive Object Labeling / Teach Modal */}
      {showTeachModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-cyan-500/50 rounded-xl p-5 max-w-sm w-full shadow-2xl">
            <h3 className="text-sm font-bold text-cyan-300 mb-2 flex items-center gap-2">
              🏷️ TEACH OBJECT ANCHOR
            </h3>
            <p className="text-xs text-slate-300 mb-4">
              Enter a name for the selected object (e.g. <code>ChargingDock</code>, <code>CoffeeMug</code>, <code>Me</code>).
              Its pure 384-D fingerprint and floor location will be stored permanently.
            </p>

            <input
              type="text"
              value={teachLabel}
              onChange={(e) => setTeachLabel(e.target.value)}
              placeholder="Object Label..."
              autoFocus
              className="w-full bg-slate-950 border border-cyan-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400 mb-4"
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveTeach();
                if (e.key === 'Escape') setShowTeachModal(false);
              }}
            />

            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setShowTeachModal(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveTeach}
                disabled={!teachLabel.trim()}
                className="px-4 py-1.5 text-xs font-bold bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-lg transition shadow-md shadow-cyan-600/30"
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
