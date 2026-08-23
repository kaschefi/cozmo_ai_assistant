import React, { useEffect, useRef } from 'react';

/**
 * ParticleDriftBackground component.
 * Implementation of ThreeUI Particle Drift (Zenith ASCII Compute Network engine)
 * Features:
 * - Interactive drifting ASCII matrix glyph nodes with dynamic random character swapping.
 * - Proximity lines interconnecting nearby ASCII nodes.
 * - Interactive mouse connector rays tracking pointer position with glowing intensity.
 * - 75% opacity as requested.
 * - Styled in Cyber Green (#00ff66) over deep Cyber Black (#020503).
 */

export interface ParticleDriftProps {
  className?: string;
  nodeCount?: number;
  primaryColor?: string;
}

interface Node {
  x: number;
  y: number;
  vy: number;
  char: string;
}

export const ParticleDriftBackground: React.FC<ParticleDriftProps> = ({
  className = '',
  nodeCount,
  primaryColor = '#00ff66',
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
    let nodes: Node[] = [];
    const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%&*()'.split('');
    const mouse = { x: -1000, y: -1000 };
    let animId = 0;

    const totalNodes =
      nodeCount ?? (typeof window !== 'undefined' && window.innerWidth < 768 ? 45 : 95);

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
      nodes = Array.from({ length: totalNodes }).map(() => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vy: Math.random() * 0.35 + 0.1,
        char: chars[Math.floor(Math.random() * chars.length)],
      }));
    }

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
    };

    const handleMouseLeave = () => {
      mouse.x = -1000;
      mouse.y = -1000;
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    window.addEventListener('mouseleave', handleMouseLeave, { passive: true });
    window.addEventListener('resize', () => {
      resize();
      initParticles();
    });

    resize();
    initParticles();

    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, width, height);

      // Interactive Nodes (ASCII)
      ctx.font = '12px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      // Proximity Grid Lines (Grey by default, green if near cursor)
      ctx.lineWidth = 0.5;
      for (let i = 0; i < nodes.length; i++) {
        const n1 = nodes[i];
        const dMouse1 = Math.hypot(mouse.x - n1.x, mouse.y - n1.y);
        for (let j = i + 1; j < nodes.length; j++) {
          const n2 = nodes[j];
          const d = Math.hypot(n1.x - n2.x, n1.y - n2.y);
          if (d < 120) {
            const dMouse2 = Math.hypot(mouse.x - n2.x, mouse.y - n2.y);
            const isNearMouse = dMouse1 < 180 || dMouse2 < 180;

            if (isNearMouse) {
              ctx.strokeStyle = `rgba(0, 255, 102, ${0.25 * (1 - d / 120)})`;
            } else {
              ctx.strokeStyle = `rgba(156, 163, 175, ${0.12 * (1 - d / 120)})`;
            }

            ctx.beginPath();
            ctx.moveTo(n1.x, n1.y);
            ctx.lineTo(n2.x, n2.y);
            ctx.stroke();
          }
        }
      }

      // ASCII Node Drawing and Mouse Tethering
      nodes.forEach((n) => {
        n.y += n.vy; // Slow gentle drift
        if (n.y > height + 20) {
          n.y = -20;
          n.x = Math.random() * width;
        }

        const dist = Math.hypot(mouse.x - n.x, mouse.y - n.y);

        // Dynamic Character Swap
        if (dist < 180 || Math.random() > 0.985) {
          n.char = chars[Math.floor(Math.random() * chars.length)];
        }

        // Mouse Connection Ray (Green)
        if (dist < 180) {
          ctx.strokeStyle = `rgba(0, 255, 102, ${0.5 * (1 - dist / 180)})`;
          ctx.lineWidth = 0.8;
          ctx.beginPath();
          ctx.moveTo(n.x, n.y);
          ctx.lineTo(mouse.x, mouse.y);
          ctx.stroke();
        }

        // Connected to cursor: Vibrant Cyber Green (#00ff66). Default: Sleek Grey (#9ca3af at 75% opacity)
        if (dist < 180) {
          ctx.fillStyle = primaryColor; // '#00ff66'
        } else {
          ctx.fillStyle = 'rgba(156, 163, 175, 0.75)'; // Sleek Grey at 75%
        }

        ctx.fillText(n.char, n.x, n.y);
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
    };
  }, [nodeCount, primaryColor]);

  return (
    <div
      ref={containerRef}
      className={`fixed inset-0 w-full h-full pointer-events-none z-0 overflow-hidden ${className}`}
      style={{ background: '#020503', opacity: 0.75 }}
    >
      <canvas ref={canvasRef} className="w-full h-full block relative z-10" />
    </div>
  );
};

export default ParticleDriftBackground;
