import React, { useEffect, useRef } from 'react';

/**
 * ConstellationFieldBackground component.
 * Exact implementation of ThreeUI Constellation Field with Cyber Green & Black theme.
 * Features:
 * - Dynamic drifting constellation nodes with velocity damping and edge bouncing.
 * - Interactive pointer gravity tracker that pulls nearby constellation nodes toward the mouse cursor.
 * - Distance-based alpha link lines connecting clustered cyber nodes.
 * - Pulsing glowing node cores with soft halo glow.
 * - Cyber Green (`#00ff66`, `#10b981`) over deep cyber obsidian black (`#020503`).
 */

export interface ConstellationFieldProps {
  className?: string;
  nodeColor?: string;
  linkColor?: string;
  maxNodes?: number;
  linkDistance?: number;
}

interface Node {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
}

export const ConstellationFieldBackground: React.FC<ConstellationFieldProps> = ({
  className = '',
  nodeColor = '#00ff66',
  linkColor = '#00ff66',
  maxNodes,
  linkDistance = 160,
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
    const pointer = { x: -1000, y: -1000 };
    let animId = 0;

    const computedMaxNodes =
      maxNodes ?? (typeof window !== 'undefined' && window.innerWidth < 768 ? 45 : 90);

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

    function initNodes() {
      nodes = [];
      for (let i = 0; i < computedMaxNodes; i++) {
        nodes.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35,
          radius: Math.random() * 2.2 + 1.6,
        });
      }
    }

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointer.x = e.clientX - rect.left;
      pointer.y = e.clientY - rect.top;
    };

    const handleMouseLeave = () => {
      pointer.x = -1000;
      pointer.y = -1000;
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    window.addEventListener('mouseleave', handleMouseLeave, { passive: true });
    window.addEventListener('resize', () => {
      resize();
      initNodes();
    });

    resize();
    initNodes();

    function dist(a: { x: number; y: number }, b: { x: number; y: number }) {
      return Math.hypot(a.x - b.x, a.y - b.y);
    }

    function animate() {
      if (!ctx) return;
      ctx.clearRect(0, 0, width, height);
      ctx.lineCap = 'butt';
      ctx.lineJoin = 'miter';

      // 1. Draw Links
      ctx.strokeStyle = linkColor;
      ctx.lineWidth = 1;
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const d = dist(nodes[i], nodes[j]);
          if (d < linkDistance) {
            ctx.globalAlpha = 0.18 + (1 - d / linkDistance) * 0.45;
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.stroke();
          }
        }
      }

      // 2. Update & Draw Nodes
      const now = Date.now() * 0.001;
      nodes.forEach((node) => {
        node.x += node.vx;
        node.y += node.vy;

        // Bounce off bounds
        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;

        // Gentle Pointer gravity
        const pd = dist(node, pointer);
        if (pd < 220) {
          node.x -= (node.x - pointer.x) * 0.006;
          node.y -= (node.y - pointer.y) * 0.006;
        }

        // Draw Node (Cyber Green Glow & Core)
        const pulse = 0.78 + Math.sin(now + node.x * 0.05) * 0.22;
        ctx.fillStyle = nodeColor;

        // Halo
        ctx.globalAlpha = pulse * 0.28;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius * 2.4, 0, Math.PI * 2);
        ctx.fill();

        // Core
        ctx.globalAlpha = pulse;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fill();
      });

      ctx.globalAlpha = 1;
      animId = requestAnimationFrame(animate);
    }

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!prefersReducedMotion) {
      animate();
    } else {
      animate();
      cancelAnimationFrame(animId);
    }

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('resize', resize);
    };
  }, [linkColor, nodeColor, maxNodes, linkDistance]);

  return (
    <div
      ref={containerRef}
      className={`fixed inset-0 w-full h-full pointer-events-none z-0 overflow-hidden ${className}`}
      style={{ background: '#020503' }}
    >
      {/* Background cyber radial glow */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-40"
        style={{
          background: 'radial-gradient(ellipse at 50% 40%, rgba(0, 255, 102, 0.08) 0%, rgba(2, 5, 3, 0.95) 80%)'
        }}
      />
      <canvas ref={canvasRef} className="w-full h-full block relative z-10" />
    </div>
  );
};

export default ConstellationFieldBackground;
