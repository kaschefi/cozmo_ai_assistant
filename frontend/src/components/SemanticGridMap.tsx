import React, { useRef, useEffect, useState, useCallback } from 'react';

export interface RobotPose {
  x: number;
  y: number;
  theta_deg: number;
  head_pitch_deg?: number;
  is_connected?: boolean;
}

export interface VisualAnchorData {
  label: string;
  x: number;
  y: number;
  confidence_threshold?: number;
  is_permanent?: boolean;
  observation_count?: number;
  last_seen_at?: number;
}

export interface ObstacleData {
  id: string;
  x: number;
  y: number;
  radius: number;
  confidence?: number;
}

export interface SemanticGridMapProps {
  robot: RobotPose;
  anchors: VisualAnchorData[];
  obstacles: ObstacleData[];
  path?: number[][];
  onPointClick?: (worldX: number, worldY: number) => void;
  onAnchorClick?: (anchor: VisualAnchorData) => void;
  className?: string;
}

export const SemanticGridMap: React.FC<SemanticGridMapProps> = ({
  robot,
  anchors,
  obstacles,
  path = [],
  onPointClick,
  onAnchorClick,
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [scale, setScale] = useState<number>(0.65); // pixels per mm
  const [offset, setOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [trail, setTrail] = useState<{ x: number; y: number }[]>([]);

  // Track robot breadcrumbs
  useEffect(() => {
    if (robot.x !== 0 || robot.y !== 0) {
      setTrail((prev) => {
        const last = prev[prev.length - 1];
        if (!last || Math.hypot(last.x - robot.x, last.y - robot.y) > 15) {
          const nextTrail = [...prev, { x: robot.x, y: robot.y }];
          return nextTrail.slice(-120); // Keep last 120 points
        }
        return prev;
      });
    }
  }, [robot.x, robot.y]);

  // Center on Cozmo
  const handleRecenter = useCallback(() => {
    setOffset({ x: 0, y: 0 });
    setScale(0.65);
  }, []);

  // Main Canvas Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2 + offset.x;
    const centerY = height / 2 + offset.y;

    // 1. Clear background (Dark blueprint theme)
    ctx.fillStyle = '#0a0d14';
    ctx.fillRect(0, 0, width, height);

    // 2. Draw 2D Coordinate Grid
    const gridSizeMm = 100; // 10 cm major grid
    const gridPixelSize = gridSizeMm * scale;

    ctx.save();
    ctx.lineWidth = 1;

    // Minor grid (50mm)
    const minorPixelSize = (gridSizeMm / 2) * scale;
    if (minorPixelSize > 15) {
      ctx.strokeStyle = 'rgba(30, 45, 75, 0.4)';
      const startX = (centerX % minorPixelSize);
      const startY = (centerY % minorPixelSize);
      ctx.beginPath();
      for (let x = startX; x < width; x += minorPixelSize) {
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
      }
      for (let y = startY; y < height; y += minorPixelSize) {
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
      }
      ctx.stroke();
    }

    // Major grid (100mm)
    ctx.strokeStyle = 'rgba(0, 180, 255, 0.15)';
    const majorStartX = (centerX % gridPixelSize);
    const majorStartY = (centerY % gridPixelSize);
    ctx.beginPath();
    for (let x = majorStartX; x < width; x += gridPixelSize) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
    }
    for (let y = majorStartY; y < height; y += gridPixelSize) {
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
    }
    ctx.stroke();

    // Origin Axes (0,0)
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.5)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(centerX, 0);
    ctx.lineTo(centerX, height);
    ctx.moveTo(0, centerY);
    ctx.lineTo(width, centerY);
    ctx.stroke();
    ctx.restore();

    // Transform World coordinates to Canvas pixels
    const worldToCanvas = (wx: number, wy: number) => ({
      cx: centerX + wx * scale,
      cy: centerY - wy * scale, // Invert Y so +Y is forward/up
    });

    // 3. Draw Robot Breadcrumbs / Odometry Trail
    if (trail.length > 1) {
      ctx.save();
      ctx.strokeStyle = 'rgba(0, 255, 200, 0.4)';
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      const first = worldToCanvas(trail[0].x, trail[0].y);
      ctx.moveTo(first.cx, first.cy);
      for (let i = 1; i < trail.length; i++) {
        const pt = worldToCanvas(trail[i].x, trail[i].y);
        ctx.lineTo(pt.cx, pt.cy);
      }
      ctx.stroke();
      ctx.restore();
    }

    // 4. Draw Planned Navigation Path
    if (path.length > 1) {
      ctx.save();
      ctx.strokeStyle = '#00ff88';
      ctx.lineWidth = 3;
      ctx.shadowColor = '#00ff88';
      ctx.shadowBlur = 8;
      ctx.beginPath();
      const firstP = worldToCanvas(path[0][0], path[0][1]);
      ctx.moveTo(firstP.cx, firstP.cy);
      for (let i = 1; i < path.length; i++) {
        const pt = worldToCanvas(path[i][0], path[i][1]);
        ctx.lineTo(pt.cx, pt.cy);
      }
      ctx.stroke();
      ctx.restore();
    }

    // 5. Draw Unnamed Ground Obstacles
    obstacles.forEach((obs) => {
      const { cx, cy } = worldToCanvas(obs.x, obs.y);
      const rPix = Math.max(12, obs.radius * scale);

      ctx.save();
      ctx.fillStyle = 'rgba(255, 80, 40, 0.25)';
      ctx.strokeStyle = 'rgba(255, 100, 50, 0.85)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, rPix, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      // Obstacle Center Dot
      ctx.fillStyle = '#ff4422';
      ctx.beginPath();
      ctx.arc(cx, cy, 3, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#ff9988';
      ctx.font = '10px sans-serif';
      ctx.fillText('OBSTACLE', cx - 24, cy - rPix - 4);
      ctx.restore();
    });

    // 6. Draw Named Visual Anchors (ChargingDock, DeskLamp, Me, etc.)
    anchors.forEach((a) => {
      const { cx, cy } = worldToCanvas(a.x, a.y);
      const isDock = a.label.toLowerCase().includes('charger') || a.label.toLowerCase().includes('dock');

      ctx.save();
      const color = isDock ? '#ffe600' : '#00e5ff';

      // Outer Pulse Ring
      ctx.strokeStyle = color;
      ctx.shadowColor = color;
      ctx.shadowBlur = 10;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, 14, 0, Math.PI * 2);
      ctx.stroke();

      // Inner Icon Circle
      ctx.fillStyle = isDock ? 'rgba(255, 230, 0, 0.3)' : 'rgba(0, 229, 255, 0.3)';
      ctx.beginPath();
      ctx.arc(cx, cy, 10, 0, Math.PI * 2);
      ctx.fill();

      // Anchor Center Point
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(cx, cy, 3.5, 0, Math.PI * 2);
      ctx.fill();

      // Anchor Label Badge
      ctx.font = 'bold 11px sans-serif';
      ctx.shadowBlur = 0;
      const textWidth = ctx.measureText(a.label.toUpperCase()).width;
      ctx.fillStyle = 'rgba(15, 20, 30, 0.9)';
      ctx.fillRect(cx - textWidth / 2 - 6, cy + 18, textWidth + 12, 18);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.strokeRect(cx - textWidth / 2 - 6, cy + 18, textWidth + 12, 18);

      ctx.fillStyle = color;
      ctx.fillText(a.label.toUpperCase(), cx, cy + 27);
      ctx.restore();
    });

    // 7. Draw Cozmo Robot Avatar with Glowing Camera Field-of-View Cone
    const radHeading = (robot.theta_deg * Math.PI) / 180;
    const robCx = centerX + robot.x * scale;
    const robCy = centerY - robot.y * scale;

    ctx.save();
    ctx.translate(robCx, robCy);
    ctx.rotate(-radHeading);

    // Camera FOV Cone (~60 degrees horizontal FOV, 220mm length)
    const fovLen = 220 * scale;
    const fovHalfAngle = (30 * Math.PI) / 180;
    const grad = ctx.createRadialGradient(0, 0, 10, 0, 0, fovLen);
    grad.addColorStop(0, 'rgba(0, 255, 200, 0.35)');
    grad.addColorStop(0.8, 'rgba(0, 255, 200, 0.08)');
    grad.addColorStop(1, 'rgba(0, 255, 200, 0)');

    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(fovLen * Math.sin(fovHalfAngle), -fovLen * Math.cos(fovHalfAngle));
    ctx.arc(0, 0, fovLen, -Math.PI / 2 - fovHalfAngle, -Math.PI / 2 + fovHalfAngle);
    ctx.closePath();
    ctx.fill();

    // Robot Body (Chassis: 55mm x 72mm)
    const bodyW = 55 * scale;
    const bodyH = 72 * scale;

    // Tread Tracks
    ctx.fillStyle = '#1e2430';
    ctx.strokeStyle = '#00f0ff';
    ctx.lineWidth = 1.5;
    ctx.fillRect(-bodyW / 2 - 6, -bodyH / 2, 6, bodyH);
    ctx.strokeRect(-bodyW / 2 - 6, -bodyH / 2, 6, bodyH);
    ctx.fillRect(bodyW / 2, -bodyH / 2, 6, bodyH);
    ctx.strokeRect(bodyW / 2, -bodyH / 2, 6, bodyH);

    // Main Chassis
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(-bodyW / 2, -bodyH / 2, bodyW, bodyH);
    ctx.strokeRect(-bodyW / 2, -bodyH / 2, bodyW, bodyH);

    // Head / Display Screen
    ctx.fillStyle = '#00e5ff';
    ctx.shadowColor = '#00e5ff';
    ctx.shadowBlur = 8;
    ctx.fillRect(-bodyW / 4, -bodyH / 2 + 4, bodyW / 2, 12);

    // Directional Pointer Arrow
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.moveTo(0, -bodyH / 2 - 8);
    ctx.lineTo(6, -bodyH / 2 + 2);
    ctx.lineTo(-6, -bodyH / 2 + 2);
    ctx.closePath();
    ctx.fill();

    ctx.restore();

    // 8. On-Canvas HUD Coordinates & Scale Indicator
    ctx.save();
    ctx.fillStyle = 'rgba(10, 15, 25, 0.85)';
    ctx.strokeStyle = 'rgba(0, 200, 255, 0.3)';
    ctx.lineWidth = 1;
    ctx.fillRect(10, 10, 180, 50);
    ctx.strokeRect(10, 10, 180, 50);

    ctx.fillStyle = '#00f0ff';
    ctx.font = 'bold 11px monospace';
    ctx.fillText(`COZMO POSE:`, 18, 26);
    ctx.fillStyle = '#ffffff';
    ctx.fillText(`X: ${robot.x.toFixed(1)}mm  Y: ${robot.y.toFixed(1)}mm`, 18, 40);
    ctx.fillText(`HDG: ${robot.theta_deg.toFixed(1)}°`, 18, 52);
    ctx.restore();

  }, [robot, anchors, obstacles, path, scale, offset, trail]);

  // Mouse Interaction: Pan & Drag
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDragging) {
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  // Mouse Wheel Zoom
  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    setScale((prev) => Math.max(0.15, Math.min(2.5, prev * zoomFactor)));
  };

  // Click on Map to Command Cozmo to Drive to (X, Y)
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDragging) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const centerX = canvas.width / 2 + offset.x;
    const centerY = canvas.height / 2 + offset.y;

    const worldX = (mouseX - centerX) / scale;
    const worldY = (centerY - mouseY) / scale;

    // Check if clicked an anchor
    const clickedAnchor = anchors.find(
      (a) => Math.hypot(a.x - worldX, a.y - worldY) < 35
    );

    if (clickedAnchor && onAnchorClick) {
      onAnchorClick(clickedAnchor);
    } else if (onPointClick) {
      onPointClick(Math.round(worldX), Math.round(worldY));
    }
  };

  return (
    <div className={`relative w-full h-full overflow-hidden bg-[#0a0d14] rounded-xl border border-cyan-900/40 ${className}`}>
      <canvas
        ref={canvasRef}
        width={750}
        height={500}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        onClick={handleCanvasClick}
        className="w-full h-full cursor-crosshair block"
      />

      {/* Top-Right Canvas Controls */}
      <div className="absolute top-3 right-3 flex items-center gap-2 bg-slate-900/80 backdrop-blur-md p-1.5 rounded-lg border border-cyan-800/40">
        <button
          onClick={() => setScale((s) => Math.min(2.5, s * 1.2))}
          className="w-7 h-7 flex items-center justify-center bg-slate-800 hover:bg-cyan-600 text-white rounded text-sm transition"
          title="Zoom In"
        >
          +
        </button>
        <button
          onClick={() => setScale((s) => Math.max(0.15, s * 0.8))}
          className="w-7 h-7 flex items-center justify-center bg-slate-800 hover:bg-cyan-600 text-white rounded text-sm transition"
          title="Zoom Out"
        >
          -
        </button>
        <button
          onClick={handleRecenter}
          className="px-2.5 h-7 flex items-center justify-center bg-slate-800 hover:bg-cyan-600 text-cyan-300 hover:text-white rounded text-xs font-mono transition"
          title="Center on Robot"
        >
          Recenter
        </button>
      </div>

      {/* Bottom Hint */}
      <div className="absolute bottom-2 left-3 text-[11px] text-slate-400 font-mono pointer-events-none select-none">
        Click on map to drive Cozmo to coordinate | Drag to Pan | Scroll to Zoom
      </div>
    </div>
  );
};

export default SemanticGridMap;
