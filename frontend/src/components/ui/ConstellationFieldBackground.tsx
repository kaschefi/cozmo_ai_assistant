import React, { useEffect, useRef } from 'react';

/**
 * ConstellationFieldBackground component for the "Black Ice" theme.
 * Direct native implementation of ThreeUI ConstellationField (Variant: Interface Lines).
 * Features:
 * - Dynamic scroll-reactive opacity: ~20% at the top hero section, scaling up to ~85% on scroll.
 * - Scroll-driven upward kinetic drift: particles accelerate upward as user scrolls through the page.
 * - Drifting network particles with velocity vectors and boundary wrapping/bouncing.
 * - Geometric proximity interface lines between nearby nodes with distance-based alpha.
 * - Precision square node vertices (1.5px) in specular ice white.
 * - Interactive cursor proximity illumination and subtle particle deflection.
 * - Glacial Cyan (#00f3ff) and Ice White (#e0f8ff) over deep obsidian black (#020407).
 */

export interface ConstellationFieldProps {
  className?: string;
  particleCount?: number;
  linkDistance?: number;
  baseOpacity?: number; // Base opacity when at top (default: 0.20)
  maxOpacity?: number;  // Max opacity after scroll (default: 0.75)
  strokeWidth?: number;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

export const ConstellationFieldBackground: React.FC<ConstellationFieldProps> = ({
  className = '',
  particleCount,
  linkDistance = 130,
  baseOpacity = 0.20,
  maxOpacity = 0.75,
  strokeWidth = 1,
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
    let particles: Particle[] = [];
    const mouse = { x: -1000, y: -1000, active: false };
    let animId = 0;

    // Scroll state tracking
    let currentScrollY = window.scrollY || 0;
    let prevScrollY = currentScrollY;
    let scrollVelocity = 0;
    let dynamicOpacity = baseOpacity;

    const count =
      particleCount ?? (typeof window !== 'undefined' && window.innerWidth < 640 ? 35 : 75);

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
      ctx!.imageSmoothingEnabled = false;
    }

    function initParticles() {
      particles = [];
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.4,
          vy: -Math.random() * 0.35 - 0.08, // Initial gentle upward float
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
      initParticles();
    });

    resize();
    initParticles();

    function drawLines() {
      if (!ctx) return;

      // 1. Smoothly calculate scroll progress (0 at top, 1 at 550px down)
      const scrollProgress = Math.min(1, Math.max(0, currentScrollY / 550));
      const targetOpacity = baseOpacity + (maxOpacity - baseOpacity) * scrollProgress;
      dynamicOpacity += (targetOpacity - dynamicOpacity) * 0.08;

      // 2. Calculate scroll velocity for upward impulse
      const scrollDelta = currentScrollY - prevScrollY;
      prevScrollY = currentScrollY;
      scrollVelocity += (scrollDelta - scrollVelocity) * 0.15;

      ctx.clearRect(0, 0, width, height);
      ctx.lineWidth = strokeWidth;
      ctx.lineCap = 'butt';
      ctx.lineJoin = 'miter';

      // 3. Update and link particles
      const upwardScrollBoost = Math.max(0, scrollVelocity * 0.08);

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        // Upward drift + additional upward momentum when scrolling down
        p.y += p.vy - upwardScrollBoost;

        // Horizontal bounce off bounds
        if (p.x < 0) {
          p.x = 0;
          p.vx *= -1;
        } else if (p.x > width) {
          p.x = width;
          p.vx *= -1;
        }

        // Vertical wrapping when ascending beyond top edge
        if (p.y < -10) {
          p.y = height + 10;
          p.x = Math.random() * width;
        } else if (p.y > height + 10) {
          p.y = -10;
          p.x = Math.random() * width;
        }

        // Gentle cursor push & glow
        if (mouse.active) {
          const mdx = p.x - mouse.x;
          const mdy = p.y - mouse.y;
          const mdist = Math.hypot(mdx, mdy);
          if (mdist < 140 && mdist > 0) {
            const force = (1 - mdist / 140) * 0.45;
            p.x += (mdx / mdist) * force;
            p.y += (mdy / mdist) * force;
          }
        }

        // Draw geometric connection lines to subsequent particles
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p.x - p2.x;
          const dy = p.y - p2.y;
          const dist = Math.hypot(dx, dy);

          if (dist < linkDistance) {
            const lineAlpha = (0.22 + (1 - dist / linkDistance) * 0.52) * dynamicOpacity;

            ctx.beginPath();
            // Subtle glacial cyan tint with specular ice white core
            ctx.strokeStyle = `rgba(0, 243, 255, ${lineAlpha * 0.65})`;
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();

            ctx.beginPath();
            ctx.strokeStyle = `rgba(224, 248, 255, ${lineAlpha * 0.85})`;
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }

        // Draw precision square node vertices (ThreeUI signature 1.5px micro-nodes)
        const nodeAlpha = dynamicOpacity;
        ctx.fillStyle = `rgba(0, 243, 255, ${0.4 * nodeAlpha})`;
        ctx.fillRect(p.x - 1.5, p.y - 1.5, 3, 3);

        ctx.fillStyle = `rgba(255, 255, 255, ${0.9 * nodeAlpha})`;
        ctx.fillRect(p.x - 0.75, p.y - 0.75, 1.5, 1.5);
      }

      animId = requestAnimationFrame(drawLines);
    }

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!prefersReducedMotion) {
      drawLines();
    } else {
      drawLines();
      cancelAnimationFrame(animId);
    }

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', resize);
    };
  }, [baseOpacity, maxOpacity, linkDistance, particleCount, strokeWidth]);

  return (
    <div
      ref={containerRef}
      className={`fixed inset-0 w-full h-full pointer-events-none z-0 overflow-hidden ${className}`}
      style={{ background: '#020407' }}
    >
      {/* Glacial Cyan Ambient Depth Glow */}
      <div
        className="absolute inset-0 pointer-events-none opacity-25"
        style={{
          background:
            'radial-gradient(ellipse at 50% 40%, rgba(0, 243, 255, 0.1) 0%, rgba(2, 4, 7, 0.95) 75%)',
        }}
      />
      <canvas ref={canvasRef} className="w-full h-full block relative z-10" />
    </div>
  );
};

export default ConstellationFieldBackground;
