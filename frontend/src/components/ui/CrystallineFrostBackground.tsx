import React, { useEffect, useRef } from 'react';

/**
 * CrystallineFrostBackground component for the "Black Ice" theme.
 * Features:
 * - Dynamic procedural razor-thin crystalline ice fracture fissure network.
 * - Harmonic glacial pulse waves traveling along fracture lines.
 * - Interactive pointer frost crackle & lightning arcs jumping from fracture veins to cursor.
 * - Drifting micro ice crystal diamond dust reacting to cursor turbulence.
 * - Configured with 50% opacity and ultra-fine razor-thin line rendering.
 */

export interface CrystallineFrostProps {
  className?: string;
  fractureOpacity?: number;
  dustCount?: number;
}

interface Point {
  x: number;
  y: number;
}

interface FractureBranch {
  points: Point[];
  pulseProgress: number;
  pulseSpeed: number;
  width: number;
  baseAlpha: number;
}

interface DustParticle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  twinkleSpeed: number;
  twinklePhase: number;
}

export const CrystallineFrostBackground: React.FC<CrystallineFrostProps> = ({
  className = '',
  fractureOpacity = 0.50,
  dustCount,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || typeof window === 'undefined') return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let animId = 0;
    let time = 0;
    const mouse = { x: -1000, y: -1000, active: false };

    let branches: FractureBranch[] = [];
    let dust: DustParticle[] = [];

    function resize() {
      if (!canvas || !container) return;
      const rect = container.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width || window.innerWidth;
      height = rect.height || window.innerHeight;

      canvas.width = Math.max(1, Math.floor(width * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      initFractures();
    }

    function initFractures() {
      branches = [];

      // Generate organic, angular crystalline fracture paths across viewport (Ultra-thin widths)
      // Main Spine 1: Top-Left to Bottom-Right
      branches.push({
        points: [
          { x: width * -0.05, y: height * 0.15 },
          { x: width * 0.22, y: height * 0.28 },
          { x: width * 0.45, y: height * 0.42 },
          { x: width * 0.62, y: height * 0.68 },
          { x: width * 0.88, y: height * 0.85 },
          { x: width * 1.05, y: height * 0.95 },
        ],
        pulseProgress: 0.1,
        pulseSpeed: 0.003,
        width: 0.55,
        baseAlpha: 0.45,
      });

      // Sub Branch 1A (splitting from Spine 1)
      branches.push({
        points: [
          { x: width * 0.22, y: height * 0.28 },
          { x: width * 0.35, y: height * 0.12 },
          { x: width * 0.58, y: height * 0.08 },
          { x: width * 0.75, y: height * -0.02 },
        ],
        pulseProgress: 0.5,
        pulseSpeed: 0.004,
        width: 0.38,
        baseAlpha: 0.35,
      });

      // Sub Branch 1B (splitting towards bottom)
      branches.push({
        points: [
          { x: width * 0.45, y: height * 0.42 },
          { x: width * 0.38, y: height * 0.65 },
          { x: width * 0.25, y: height * 0.82 },
          { x: width * 0.15, y: height * 1.05 },
        ],
        pulseProgress: 0.7,
        pulseSpeed: 0.0035,
        width: 0.4,
        baseAlpha: 0.35,
      });

      // Main Spine 2: Top-Right to Middle-Left
      branches.push({
        points: [
          { x: width * 1.05, y: height * 0.18 },
          { x: width * 0.78, y: height * 0.35 },
          { x: width * 0.62, y: height * 0.68 },
          { x: width * 0.52, y: height * 0.82 },
          { x: width * 0.42, y: height * 1.05 },
        ],
        pulseProgress: 0.3,
        pulseSpeed: 0.0032,
        width: 0.5,
        baseAlpha: 0.4,
      });

      // Lateral Micro-Cracks
      branches.push({
        points: [
          { x: width * 0.78, y: height * 0.35 },
          { x: width * 0.92, y: height * 0.48 },
          { x: width * 1.02, y: height * 0.52 },
        ],
        pulseProgress: 0.8,
        pulseSpeed: 0.005,
        width: 0.28,
        baseAlpha: 0.28,
      });

      branches.push({
        points: [
          { x: width * 0.05, y: height * 0.6 },
          { x: width * 0.2, y: height * 0.52 },
          { x: width * 0.38, y: height * 0.65 },
        ],
        pulseProgress: 0.2,
        pulseSpeed: 0.0045,
        width: 0.3,
        baseAlpha: 0.3,
      });

      // Generate crystalline micro ice dust particles
      const count = dustCount ?? (width < 768 ? 30 : 65);
      dust = Array.from({ length: count }).map(() => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.22,
        vy: (Math.random() - 0.5) * 0.22 - 0.04,
        size: Math.random() * 1.4 + 0.6,
        alpha: Math.random() * 0.5 + 0.2,
        twinkleSpeed: Math.random() * 0.03 + 0.015,
        twinklePhase: Math.random() * Math.PI * 2,
      }));
    }

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
      mouse.active = true;
    };

    const handleMouseLeave = () => {
      mouse.x = -1000;
      mouse.y = -1000;
      mouse.active = false;
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    window.addEventListener('mouseleave', handleMouseLeave, { passive: true });
    window.addEventListener('resize', resize);

    resize();

    // Helper to compute distance from point to line segment
    function distToSegment(px: number, py: number, x1: number, y1: number, x2: number, y2: number) {
      const l2 = (x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1);
      if (l2 === 0) return { dist: Math.hypot(px - x1, py - y1), nx: x1, ny: y1 };
      let t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2;
      t = Math.max(0, Math.min(1, t));
      const nx = x1 + t * (x2 - x1);
      const ny = y1 + t * (y2 - y1);
      return { dist: Math.hypot(px - nx, py - ny), nx, ny };
    }

    function draw() {
      if (!ctx) return;
      time += 0.016;
      ctx.clearRect(0, 0, width, height);

      // 1. Draw Razor-Thin Fracture Branches
      branches.forEach((b) => {
        b.pulseProgress = (b.pulseProgress + b.pulseSpeed) % 1.0;

        for (let i = 0; i < b.points.length - 1; i++) {
          const p1 = b.points[i];
          const p2 = b.points[i + 1];

          // Check proximity to mouse for vein lighting
          const { dist } = distToSegment(mouse.x, mouse.y, p1.x, p1.y, p2.x, p2.y);
          const mouseGlow = dist < 220 ? Math.max(0, 1 - dist / 220) : 0;

          // Layer 1: Subtle Glacial Cyan Glow halo
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = `rgba(0, 243, 255, ${b.baseAlpha * 0.22 + mouseGlow * 0.35})`;
          ctx.lineWidth = b.width * 2.2 + mouseGlow * 1.2;
          ctx.stroke();

          // Layer 2: Razor Crystalline Core
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = `rgba(224, 248, 255, ${b.baseAlpha * 0.75 + mouseGlow * 0.45})`;
          ctx.lineWidth = b.width * 0.75 + mouseGlow * 0.35;
          ctx.stroke();

          // Layer 3: Subtle Pulse Wave traveling along fracture
          const segProgress = (i + 0.5) / (b.points.length - 1);
          const pulseDist = Math.abs(b.pulseProgress - segProgress);
          if (pulseDist < 0.15) {
            const pulseIntensity = (1 - pulseDist / 0.15) * 0.7;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(0, 243, 255, ${pulseIntensity})`;
            ctx.lineWidth = b.width * 1.5;
            ctx.stroke();
          }
        }

        // Draw crystalline micro-nodal gems at vertices
        b.points.forEach((p) => {
          const d = Math.hypot(mouse.x - p.x, mouse.y - p.y);
          const nodeGlow = d < 200 ? Math.max(0, 1 - d / 200) : 0;

          ctx.beginPath();
          ctx.arc(p.x, p.y, b.width * 1.4 + nodeGlow * 1.4, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(0, 243, 255, ${0.35 + nodeGlow * 0.55})`;
          ctx.fill();

          ctx.beginPath();
          ctx.arc(p.x, p.y, b.width * 0.6 + nodeGlow * 0.4, 0, Math.PI * 2);
          ctx.fillStyle = '#ffffff';
          ctx.fill();
        });
      });

      // 2. Drifting Micro Ice Crystal Dust
      dust.forEach((d) => {
        d.x += d.vx;
        d.y += d.vy;

        // Wrap around bounds
        if (d.x < 0) d.x = width;
        if (d.x > width) d.x = 0;
        if (d.y < 0) d.y = height;
        if (d.y > height) d.y = 0;

        // Gentle cursor push
        const distM = Math.hypot(mouse.x - d.x, mouse.y - d.y);
        if (distM < 120) {
          const force = (1 - distM / 120) * 0.8;
          d.x += ((d.x - mouse.x) / distM) * force;
          d.y += ((d.y - mouse.y) / distM) * force;
        }

        const twinkle = Math.sin(time * 3 + d.twinklePhase) * 0.3 + 0.7;
        const currentAlpha = d.alpha * twinkle * (distM < 120 ? 1.3 : 0.8);

        // Draw diamond-shaped ice crystal
        ctx.save();
        ctx.translate(d.x, d.y);
        ctx.rotate(time * 0.5 + d.twinklePhase);
        ctx.fillStyle = `rgba(0, 243, 255, ${currentAlpha * 0.6})`;
        ctx.fillRect(-d.size * 0.8, -d.size * 0.8, d.size * 1.6, d.size * 1.6);
        ctx.fillStyle = `rgba(255, 255, 255, ${currentAlpha * 0.8})`;
        ctx.fillRect(-d.size * 0.4, -d.size * 0.4, d.size * 0.8, d.size * 0.8);
        ctx.restore();
      });

      animId = requestAnimationFrame(draw);
    }

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!prefersReducedMotion) {
      draw();
    } else {
      draw();
      cancelAnimationFrame(animId);
    }

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('resize', resize);
    };
  }, [dustCount, fractureOpacity]);

  return (
    <div
      ref={containerRef}
      className={`fixed inset-0 w-full h-full pointer-events-none z-0 overflow-hidden ${className}`}
      style={{ background: '#020407', opacity: fractureOpacity }}
    >
      <canvas ref={canvasRef} className="w-full h-full block relative z-10" />
    </div>
  );
};

export default CrystallineFrostBackground;
