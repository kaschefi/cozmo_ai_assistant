import React, { useEffect, useRef } from 'react';

interface VoiceWaveformProps {
  isHovered: boolean;
}

interface WaveConfig {
  frequency: number;
  amplitude: number;
  speed: number;
  opacity: number;
  lineWidth: number;
  phaseOffset: number; // unique phase offset to prevent overlapping waves from tracking exactly
}

// 5 overlapping, fluid sine waves with varying configurations
const WAVES: WaveConfig[] = [
  { frequency: 0.012, amplitude: 32, speed: 0.015, opacity: 0.75, lineWidth: 2, phaseOffset: 0 },
  { frequency: 0.022, amplitude: 20, speed: 0.025, opacity: 0.45, lineWidth: 1.5, phaseOffset: Math.PI / 4 },
  { frequency: 0.008, amplitude: 40, speed: 0.01, opacity: 0.25, lineWidth: 1.2, phaseOffset: Math.PI / 2 },
  { frequency: 0.03, amplitude: 12, speed: 0.04, opacity: 0.55, lineWidth: 1.0, phaseOffset: Math.PI * 0.75 },
  { frequency: 0.018, amplitude: 26, speed: 0.02, opacity: 0.35, lineWidth: 1.0, phaseOffset: Math.PI },
];

export const VoiceWaveform: React.FC<VoiceWaveformProps> = ({ isHovered }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameId = useRef<number | null>(null);
  const multiplierRef = useRef<number>(1.0);
  const timeRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Handle high-DPI/Retina screens scaling
    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;

      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;

      ctx.scale(dpr, dpr);
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const render = () => {
      timeRef.current += 1;
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;

      // Clear the canvas each frame
      ctx.clearRect(0, 0, width, height);

      // Smoothly interpolate the activity/amplitude multiplier
      // 1.0 when idle, 1.5 when hovered
      const targetMultiplier = isHovered ? 1.4 : 1.0;
      multiplierRef.current += (targetMultiplier - multiplierRef.current) * 0.06;

      ctx.lineCap = 'round';

      // Draw each wave ribbon
      for (let wIdx = 0; wIdx < WAVES.length; wIdx++) {
        const wave = WAVES[wIdx];
        ctx.beginPath();

        for (let x = 0; x < width; x++) {
          // A center-fade sinusoidal envelope (flat at left and right edges, full height in the center)
          const envelope = Math.sin((x / width) * Math.PI);

          // Standard sine formula with frequency, phase-offset, time progress, speed, and active multiplier
          const angle = x * wave.frequency + timeRef.current * wave.speed * multiplierRef.current + wave.phaseOffset;
          const y = height / 2 + Math.sin(angle) * wave.amplitude * multiplierRef.current * envelope;

          if (x === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }

        // Signature neon cyan color with varying opacity
        ctx.strokeStyle = `rgba(0, 243, 255, ${wave.opacity})`;
        ctx.lineWidth = wave.lineWidth;

        // Add a subtle outer glow to the more visible waveforms
        if (wave.opacity > 0.4) {
          ctx.shadowBlur = 8;
          ctx.shadowColor = 'rgba(0, 243, 255, 0.4)';
        } else {
          ctx.shadowBlur = 0;
        }

        ctx.stroke();
      }

      // Reset shadow blur to avoid affecting other canvas contexts or elements
      ctx.shadowBlur = 0;

      animationFrameId.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, [isHovered]);

  return (
    <div className="relative w-full h-[200px] md:h-[260px] flex items-center justify-center rounded-2xl bg-slate-950/20 border border-slate-900/40 backdrop-blur-sm p-4 overflow-hidden">
      {/* Waveform Canvas */}
      <canvas
        ref={canvasRef}
        className="w-full h-full block"
      />
      {/* Decorative cyber grid or ambient shadows inside container */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_40%,rgba(2,5,18,0.4)_100%)] pointer-events-none" />
    </div>
  );
};

export default VoiceWaveform;
