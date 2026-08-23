import React, { useEffect, useRef } from 'react';

/**
 * GoldVeinsBackground component for the "Royal" theme.
 * "Liquid Kintsugi" - Minimalist, organic 24k Gold veins flowing across deep obsidian stone.
 * Features:
 * - Dynamic scroll-reactive opacity: 10% at top hero section, ramping up to 75% on scroll.
 * - Minimal, elegant primary gold fracture trunks positioned along flanks to ensure zero clutter and pristine text legibility.
 * - Multi-layered 24k gold rendering: warm outer glow, rich 24k gold body, specular gold-white core.
 * - Harmonic molten energy pulses continuously traveling along the veins.
 * - Drifting 24k gold leaf micro-glitter / embers with gentle organic shimmer.
 * - Interactive cursor proximity vein illumination with warm specular highlights.
 */

export interface GoldVeinsProps {
  className?: string;
  baseOpacity?: number; // Base opacity when at top (default: 0.10)
  maxOpacity?: number;  // Max opacity on scroll (default: 0.75)
}

interface Point {
  x: number;
  y: number;
}

interface VeinSegment {
  p1: Point;
  p2: Point;
  width: number;
  length: number;
  branchIndex: number;
  phaseOffset: number;
}

interface GoldFleck {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  baseAlpha: number;
  twinkleSpeed: number;
  phase: number;
}

export const GoldVeinsBackground: React.FC<GoldVeinsProps> = ({
  className = '',
  baseOpacity = 0.10,
  maxOpacity = 0.65,
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
    let segments: VeinSegment[] = [];
    let flecks: GoldFleck[] = [];
    const mouse = { x: -1000, y: -1000, active: false };
    let animId = 0;

    // Scroll state tracking
    let currentScrollY = window.scrollY || 0;
    let prevScrollY = currentScrollY;
    let scrollVelocity = 0;
    let dynamicOpacity = baseOpacity;

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
      ctx!.imageSmoothingEnabled = true;
    }

    // Procedurally generate minimal, elegant Kintsugi gold vein pathways
    function generateVeins() {
      segments = [];

      // Only 2 to 3 main sweeping roots along the margins so the center remains clear
      const roots: { x: number; y: number; angle: number; steps: number; width: number }[] = [
        // Flank Left -> Sweeps from top-left diagonally down the left margin
        { x: -10, y: height * 0.15, angle: 0.48, steps: 22, width: 1.6 },
        // Flank Right -> Sweeps from mid-right diagonally across the lower-right margin
        { x: width + 10, y: height * 0.45, angle: 2.75, steps: 24, width: 1.5 },
        // Flank Bottom-Left -> Sweeps along the lower perimeter
        { x: width * 0.12, y: height + 10, angle: -0.85, steps: 18, width: 1.3 },
      ];

      let branchCounter = 0;

      function growBranch(
        startX: number,
        startY: number,
        angle: number,
        depth: number,
        maxSteps: number,
        baseWidth: number
      ) {
        let curX = startX;
        let curY = startY;
        let curAngle = angle;
        const branchIdx = branchCounter++;
        const phaseOffset = Math.random() * Math.PI * 2;

        for (let i = 0; i < maxSteps; i++) {
          // Smooth, longer steps for graceful flow
          const stepLen = 32 + Math.random() * 28;
          // Very gentle wander angle (low curvature to avoid wild spaghetti crossing)
          curAngle += (Math.random() - 0.5) * 0.28;

          const nextX = curX + Math.cos(curAngle) * stepLen;
          const nextY = curY + Math.sin(curAngle) * stepLen;

          const progress = i / maxSteps;
          const currentW = Math.max(0.35, baseWidth * (1 - progress * 0.55));

          segments.push({
            p1: { x: curX, y: curY },
            p2: { x: nextX, y: nextY },
            width: currentW,
            length: stepLen,
            branchIndex: branchIdx,
            phaseOffset,
          });

          // Minimal sub-branching (max depth 1, only 1 rare fork per trunk)
          if (depth === 0 && Math.random() < 0.09 && i > 4 && i < maxSteps - 4) {
            const forkAngle = curAngle + (Math.random() > 0.5 ? 1 : -1) * 0.55;
            growBranch(nextX, nextY, forkAngle, 1, 8, currentW * 0.6);
          }

          curX = nextX;
          curY = nextY;

          // Stop if far outside canvas
          if (curX < -60 || curX > width + 60 || curY < -60 || curY > height + 60) break;
        }
      }

      roots.forEach((root) => {
        growBranch(root.x, root.y, root.angle, 0, root.steps, root.width);
      });
    }

    // Generate sparse, elegant gold leaf flecks / embers
    function initFlecks() {
      flecks = [];
      const count = window.innerWidth < 768 ? 20 : 40;
      for (let i = 0; i < count; i++) {
        flecks.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.2,
          vy: -Math.random() * 0.3 - 0.08, // Floating gently upward
          size: Math.random() * 1.6 + 0.7,
          alpha: Math.random() * 0.5 + 0.2,
          baseAlpha: Math.random() * 0.45 + 0.2,
          twinkleSpeed: Math.random() * 0.025 + 0.01,
          phase: Math.random() * Math.PI * 2,
        });
      }
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

    const handleScroll = () => {
      currentScrollY = window.scrollY || 0;
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    window.addEventListener('mouseleave', handleMouseLeave, { passive: true });
    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', () => {
      resize();
      generateVeins();
      initFlecks();
    });

    resize();
    generateVeins();
    initFlecks();

    function distToSegment(p: Point, v: Point, w: Point) {
      const l2 = (v.x - w.x) ** 2 + (v.y - w.y) ** 2;
      if (l2 === 0) return Math.hypot(p.x - v.x, p.y - v.y);
      let t = ((p.x - v.x) * (w.x - v.x) + (p.y - v.y) * (w.y - v.y)) / l2;
      t = Math.max(0, Math.min(1, t));
      return Math.hypot(p.x - (v.x + t * (w.x - v.x)), p.y - (v.y + t * (w.y - v.y)));
    }

    let time = 0;

    function render() {
      if (!ctx) return;
      time += 0.02;

      // 1. Scroll-driven opacity ramp (10% at top -> 75% on scroll)
      const scrollProgress = Math.min(1, Math.max(0, currentScrollY / 550));
      const targetOpacity = baseOpacity + (maxOpacity - baseOpacity) * scrollProgress;
      dynamicOpacity += (targetOpacity - dynamicOpacity) * 0.08;

      // 2. Scroll velocity upward impulse
      const scrollDelta = currentScrollY - prevScrollY;
      prevScrollY = currentScrollY;
      scrollVelocity += (scrollDelta - scrollVelocity) * 0.15;
      const upwardScrollBoost = Math.max(0, scrollVelocity * 0.06);

      ctx.clearRect(0, 0, width, height);

      // --- 1. Draw Gold Veins ---
      for (let i = 0; i < segments.length; i++) {
        const seg = segments[i];

        // Harmonic traveling pulse along branch
        const pulse = 0.5 + 0.5 * Math.sin(time * 1.6 + seg.branchIndex * 0.7 + seg.phaseOffset);

        // Proximity to cursor
        let cursorInfluence = 0;
        if (mouse.active) {
          const d = distToSegment(mouse, seg.p1, seg.p2);
          if (d < 150) {
            cursorInfluence = (1 - d / 150) ** 1.6;
          }
        }

        const effectiveGlow = Math.min(1, 0.35 + pulse * 0.35 + cursorInfluence * 0.65);

        // PASS A: Broad Molten Gold Aura
        ctx.beginPath();
        ctx.moveTo(seg.p1.x, seg.p1.y);
        ctx.lineTo(seg.p2.x, seg.p2.y);
        ctx.lineWidth = seg.width * (3.5 + cursorInfluence * 2.0);
        ctx.lineCap = 'round';
        ctx.strokeStyle = `rgba(212, 175, 55, ${(0.15 * effectiveGlow) * dynamicOpacity})`;
        ctx.stroke();

        // PASS B: Rich 24k Gold Body
        ctx.beginPath();
        ctx.moveTo(seg.p1.x, seg.p1.y);
        ctx.lineTo(seg.p2.x, seg.p2.y);
        ctx.lineWidth = seg.width * 1.5;
        ctx.strokeStyle = `rgba(255, 215, 0, ${(0.45 + effectiveGlow * 0.45) * dynamicOpacity})`;
        ctx.stroke();

        // PASS C: Specular Warm-White Gold Core
        ctx.beginPath();
        ctx.moveTo(seg.p1.x, seg.p1.y);
        ctx.lineTo(seg.p2.x, seg.p2.y);
        ctx.lineWidth = Math.max(0.35, seg.width * 0.5);
        ctx.strokeStyle = `rgba(255, 248, 220, ${(0.65 + effectiveGlow * 0.35) * dynamicOpacity})`;
        ctx.stroke();
      }

      // --- 2. Draw Drifting 24k Gold Flecks ---
      for (let i = 0; i < flecks.length; i++) {
        const f = flecks[i];
        f.x += f.vx;
        f.y += f.vy - upwardScrollBoost;
        f.phase += f.twinkleSpeed;

        // Wrap around bounds
        if (f.y < -10) {
          f.y = height + 10;
          f.x = Math.random() * width;
        }
        if (f.x < -10) f.x = width + 10;
        if (f.x > width + 10) f.x = -10;

        const twinkle = 0.5 + 0.5 * Math.sin(f.phase);
        const fleckAlpha = (f.baseAlpha * 0.6 + twinkle * 0.4) * dynamicOpacity;

        // Soft gold halo
        ctx.fillStyle = `rgba(212, 175, 55, ${fleckAlpha * 0.35})`;
        ctx.beginPath();
        ctx.arc(f.x, f.y, f.size * 2.0, 0, Math.PI * 2);
        ctx.fill();

        // Bright gold core
        ctx.fillStyle = `rgba(255, 225, 120, ${fleckAlpha * 0.9})`;
        ctx.beginPath();
        ctx.arc(f.x, f.y, f.size, 0, Math.PI * 2);
        ctx.fill();
      }

      animId = requestAnimationFrame(render);
    }

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!prefersReducedMotion) {
      render();
    } else {
      render();
      cancelAnimationFrame(animId);
    }

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', resize);
    };
  }, [baseOpacity, maxOpacity]);

  return (
    <div
      ref={containerRef}
      className={`fixed inset-0 w-full h-full pointer-events-none z-0 overflow-hidden ${className}`}
      style={{ background: '#030407' }}
    >
      {/* Warm 24k Amber Vignette Depth Layer */}
      <div
        className="absolute inset-0 pointer-events-none opacity-30"
        style={{
          background:
            'radial-gradient(ellipse 90% 70% at 75% 25%, rgba(212, 175, 55, 0.1) 0%, rgba(30, 24, 12, 0.2) 45%, transparent 75%), radial-gradient(ellipse 60% 60% at 20% 80%, rgba(255, 215, 0, 0.06) 0%, transparent 70%)',
        }}
      />
      <canvas ref={canvasRef} className="w-full h-full block relative z-10" />
    </div>
  );
};

export default GoldVeinsBackground;
