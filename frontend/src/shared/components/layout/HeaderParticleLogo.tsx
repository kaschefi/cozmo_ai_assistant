import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { clearTabActiveSession } from '../../../features/chat/services/chatHistory';
import { useTheme } from '../../../shared/context/ThemeContext';

// =========================================================================
// 🎛️ PARTICLE DENSITY & STEPPING CONFIGURATION
// You can adjust these values right here to control the number of particles!
// - Larger STEP values = FEWER, cleaner, more spaced-out dots.
// - Smaller STEP values = MORE, denser, tightly-packed dots.
// =========================================================================
export const LOGO_PARTICLE_CONFIG = {
  // Horizontal & vertical dot spacing for the eyes (in reference 1200x600 space)
  // Previously: STEP_X = 5, STEP_Y = 8 (resulted in ~2,600 overcrowded dots in a 38px mini eye)
  // Optimal clean matrix: STEP_X = 12, STEP_Y = 16 (~500 crisp OLED-style dots)
  DEFAULT_EYE_STEP_X: 12,
  DEFAULT_EYE_STEP_Y: 16,

  // Horizontal & vertical dot spacing for the "MOKA" text shape
  DEFAULT_MOKA_STEP_X: 6,
  DEFAULT_MOKA_STEP_Y: 10,
};

export interface HeaderParticleLogoProps {
  className?: string;
  onClick?: () => void;
  cycleIntervalMs?: number;
  /** Horizontal dot spacing for the eyes (larger = fewer particles) */
  eyeStepX?: number;
  /** Vertical dot spacing for the eyes (larger = fewer particles) */
  eyeStepY?: number;
  /** Horizontal dot spacing for MOKA text (larger = fewer particles) */
  mokaStepX?: number;
  /** Vertical dot spacing for MOKA text (larger = fewer particles) */
  mokaStepY?: number;
}

interface LogoParticle {
  x: number;
  y: number;
  eyeX: number;
  eyeY: number;
  mokaX: number;
  mokaY: number;
  size: number;
  alpha: number;
  mokaAlpha: number;
  seed: number;
  speedOffset: number;
}

interface ThemeColorConfig {
  rgb: string;
  ring: string;
}

/**
 * Returns theme-specific palette parameters:
 * - Royal: 24k Gold particles
 * - IT: Cyber Neon Green particles
 * - Black Ice / Default: Glacial Cyan particles
 */
const getThemeColorConfig = (theme: string): ThemeColorConfig => {
  if (theme === 'royal') {
    return {
      rgb: '234, 179, 8', // 24k Gold
      ring: 'focus-visible:ring-amber-400/50',
    };
  }

  if (theme === 'it') {
    return {
      rgb: '0, 255, 102', // Cyber Neon Green (#00ff66)
      ring: 'focus-visible:ring-emerald-400/50',
    };
  }

  // Black Ice & Default (Glacial Cyan)
  return {
    rgb: '0, 243, 255',
    ring: 'focus-visible:ring-cyan-400/50',
  };
};

/**
 * HeaderParticleLogo
 * 
 * Reusable animated vector dot-matrix logo for the header navigation bar.
 * Smoothly morphs particles between the "MOKA" text shape and the miniature interactive
 * Cozmo eye system, with real-time mouse gaze tracking, blinks, particle avoidance,
 * and clean theme-accurate dot colors (Gold for Royal, Neon Green for IT, Cyan for Black Ice).
 */
export const HeaderParticleLogo: React.FC<HeaderParticleLogoProps> = ({
  className = '',
  onClick,
  cycleIntervalMs = 4000,
  eyeStepX = LOGO_PARTICLE_CONFIG.DEFAULT_EYE_STEP_X,
  eyeStepY = LOGO_PARTICLE_CONFIG.DEFAULT_EYE_STEP_Y,
  mokaStepX = LOGO_PARTICLE_CONFIG.DEFAULT_MOKA_STEP_X,
  mokaStepY = LOGO_PARTICLE_CONFIG.DEFAULT_MOKA_STEP_Y,
}) => {
  const { theme } = useTheme();
  const themeConfig = useMemo(() => getThemeColorConfig(theme), [theme]);
  const themeRef = useRef<string>(theme);

  useEffect(() => {
    themeRef.current = theme;
  }, [theme]);

  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [mode, setMode] = useState<'moka' | 'eyes'>('moka');
  const modeRef = useRef<'moka' | 'eyes'>('moka');

  const mouseTargetRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const mouseRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const mousePosLocalRef = useRef<{ x: number; y: number }>({ x: -9999, y: -9999 });

  const animationFrameId = useRef<number | null>(null);

  // Cycle between "MOKA" text and "eyes" every cycleIntervalMs
  useEffect(() => {
    const interval = setInterval(() => {
      const next = modeRef.current === 'moka' ? 'eyes' : 'moka';
      modeRef.current = next;
      setMode(next);
    }, cycleIntervalMs);

    return () => clearInterval(interval);
  }, [cycleIntervalMs]);

  // Default navigation handler: return to Landing / Home
  const handleClick = useCallback(() => {
    if (onClick) {
      onClick();
      return;
    }

    clearTabActiveSession();
    if (window.location.pathname !== '/' && window.location.pathname !== '') {
      window.history.pushState({}, '', '/');
      window.dispatchEvent(new Event('popstate'));
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [onClick]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const logicalW = 144;
    const logicalH = 44;

    const drawRoundedRect = (
      c: CanvasRenderingContext2D,
      x: number,
      y: number,
      w: number,
      h: number,
      r: number
    ) => {
      c.beginPath();
      c.moveTo(x + r, y);
      c.lineTo(x + w - r, y);
      c.quadraticCurveTo(x + w, y, x + w, y + r);
      c.lineTo(x + w, y + h - r);
      c.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      c.lineTo(x + r, y + h);
      c.quadraticCurveTo(x, y + h, x, y + h - r);
      c.lineTo(x, y + r);
      c.quadraticCurveTo(x, y, x + r, y);
      c.closePath();
      c.fill();
    };

    // --- 1. Generate Eye Pixel Targets in 1200x600 space ---
    // Change eyeStepX / eyeStepY to adjust eye particle density
    const eyeCanvasW = 1200;
    const eyeCanvasH = 600;
    const tempCanvasEyes = document.createElement('canvas');
    tempCanvasEyes.width = eyeCanvasW;
    tempCanvasEyes.height = eyeCanvasH;
    const tempCtxEyes = tempCanvasEyes.getContext('2d');
    if (!tempCtxEyes) return;

    tempCtxEyes.fillStyle = '#000000';
    tempCtxEyes.fillRect(0, 0, eyeCanvasW, eyeCanvasH);
    tempCtxEyes.fillStyle = '#ffffff';

    // Left and Right eye locations in reference space
    drawRoundedRect(tempCtxEyes, 280, 180, 240, 240, 40);
    drawRoundedRect(tempCtxEyes, 680, 180, 240, 240, 40);

    const eyeImgData = tempCtxEyes.getImageData(0, 0, eyeCanvasW, eyeCanvasH);
    const eyeData = eyeImgData.data;
    const eyeTargets: { x: number; y: number }[] = [];

        for (let y = 0; y < eyeCanvasH; y += eyeStepY) {
          for (let x = 0; x < eyeCanvasW; x += eyeStepX) {
            const idx = (y * eyeCanvasW + x) * 4;
            if (eyeData[idx] > 128) {
              eyeTargets.push({ x, y });
            }
          }
        }

        // --- 2. Generate MOKA Logo Text Pixel Targets ---
        // Change mokaStepX / mokaStepY to adjust MOKA letter particle density
        const tempCanvasMoka = document.createElement('canvas');
        tempCanvasMoka.width = eyeCanvasW;
        tempCanvasMoka.height = eyeCanvasH;
        const tempCtxMoka = tempCanvasMoka.getContext('2d');
        const mokaTargets: { x: number; y: number }[] = [];

        let mokaBoundsWidth = 300;
        let mokaBoundsHeight = 75;

        if (tempCtxMoka) {
          tempCtxMoka.fillStyle = '#000000';
          tempCtxMoka.fillRect(0, 0, eyeCanvasW, eyeCanvasH);
          tempCtxMoka.fillStyle = '#ffffff';
          tempCtxMoka.font = 'bold 100px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
          tempCtxMoka.textAlign = 'left';
          tempCtxMoka.textBaseline = 'top';
          tempCtxMoka.fillText('MOKA', 0, 0);

          const mokaImgData = tempCtxMoka.getImageData(0, 0, eyeCanvasW, eyeCanvasH);
          const mokaData = mokaImgData.data;

          let minX = eyeCanvasW, maxX = 0, minY = eyeCanvasH, maxY = 0;

              for (let y = 0; y < eyeCanvasH; y += mokaStepY) {
                for (let x = 0; x < eyeCanvasW; x += mokaStepX) {
                  const idx = (y * eyeCanvasW + x) * 4;
                  if (mokaData[idx] > 128) {
                    mokaTargets.push({ x, y });
                    if (x < minX) minX = x;
                    if (x > maxX) maxX = x;
                    if (y < minY) minY = y;
                    if (y > maxY) maxY = y;
                  }
                }
              }

              if (maxX > minX) mokaBoundsWidth = maxX - minX;
              if (maxY > minY) mokaBoundsHeight = maxY - minY;
            }

            const shuffledMoka = [...mokaTargets].sort(() => Math.random() - 0.5);

                // --- 3. Initialize Particle Ensembles (Clean 1:1 Morphing) ---
                const totalParticles = Math.max(eyeTargets.length, shuffledMoka.length);
                const particles: LogoParticle[] = [];

                for(let i = 0; i<totalParticles; i++) {
                  const eyeT = eyeTargets[i % eyeTargets.length];
            const mokaT = shuffledMoka.length > 0 ? shuffledMoka[i % shuffledMoka.length] : { x: 0, y: 0 };
            particles.push({
              x: (eyeT.x - 600) * 0.16 + logicalW / 2 + (Math.random() - 0.5) * 6,
              y: (eyeT.y - 300) * 0.16 + logicalH / 2 + (Math.random() - 0.5) * 6,
              eyeX: eyeT.x,
              eyeY: eyeT.y,
              mokaX: mokaT.x,
              mokaY: mokaT.y,
              size: Math.random() * 0.6 + 1.8,
              alpha: 1.0,
              mokaAlpha: 1.0,
              seed: Math.random() * 100,
              speedOffset: Math.random(),
});
    }

let time = 0;
let blinkTimer = 0;
let blinkFactor = 1.0;
let lastTimestamp = performance.now();

// High-DPI physical scale setup
const dpr = Math.min(window.devicePixelRatio || 1, 2);
canvas.width = logicalW * dpr;
canvas.height = logicalH * dpr;

// --- 4. Animation Render Loop ---
const render = (now: number = performance.now()) => {
  const rawDelta = (now - lastTimestamp) / 1000;
  lastTimestamp = now;
  const delta = Math.min(Math.max(rawDelta, 0.001), 0.05);
  const dt = delta * 60;
  time += dt;

  ctx.save();
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, logicalW, logicalH);

  // Dynamically resolve theme color: Gold for royal, Neon Green for IT, Cyan for black-ice/default
  const activeTheme = themeRef.current;
  let rgb = '0, 243, 255';
  if (activeTheme === 'royal') {
    rgb = '234, 179, 8'; // Gold
  } else if (activeTheme === 'it') {
    rgb = '0, 255, 102'; // Neon green
  } else {
    const cssColor = getComputedStyle(document.documentElement).getPropertyValue('--particle-rgb').trim();
    rgb = cssColor || '0, 243, 255';
  }

  // Periodic natural blinking
  if (blinkTimer > 0) {
    blinkTimer -= dt;
    if (blinkTimer > 8) {
      blinkFactor = Math.max(0, (blinkTimer - 8) / 8);
    } else {
      blinkFactor = Math.min(1, (8 - blinkTimer) / 8);
    }
  } else {
    blinkFactor = 1.0;
    if (Math.random() < 0.007 * dt) {
      blinkTimer = 16;
    }
  }

  // Smooth mouse lerp
  mouseRef.current.x += (mouseTargetRef.current.x - mouseRef.current.x) * Math.min(0.2 * dt, 1);
  mouseRef.current.y += (mouseTargetRef.current.y - mouseRef.current.y) * Math.min(0.2 * dt, 1);

  const currentMode = modeRef.current;
  const logoScale = 0.38;
  const mokaOffsetX = Math.max(0, (logicalW - mokaBoundsWidth * logoScale) / 2);
  const mokaOffsetY = Math.max(0, (logicalH - mokaBoundsHeight * logoScale) / 2);

  const miniScale = 0.16;
  const headerCenterX = logicalW / 2;
  const headerCenterY = logicalH / 2;

  for (let i = 0; i < particles.length; i++) {
    const p = particles[i];
    let targetX = 0;
    let targetY = 0;

    if (currentMode === 'moka') {
      // MOKA logo text shape
      targetX = mokaOffsetX + p.mokaX * logoScale;
      targetY = mokaOffsetY + p.mokaY * logoScale;
    } else {
      // Miniature interactive eyes shape
      const cx = p.eyeX < 600 ? 400 : 800;
      const cy = 300;

      const dx_eye = p.eyeX - cx;
      const dy_eye = p.eyeY - cy;

      const isLeftEye = p.eyeX < 600;
      const eyeScale = isLeftEye
        ? (1.0 - mouseRef.current.x * 0.14)
        : (1.0 + mouseRef.current.x * 0.14);

      const scaledX = cx + dx_eye * eyeScale;
      const scaledY = cy + dy_eye * eyeScale * blinkFactor;

      const maxShift = 4;
      const shiftX = mouseRef.current.x * maxShift;
      const shiftY = mouseRef.current.y * maxShift;

      const idleX = Math.sin(time * 0.07 + p.seed * 5) * 0.25;
      const idleY = Math.cos(time * 0.07 + p.seed * 5) * 0.2;

      const relativeX = (scaledX - 600) * miniScale;
      const relativeY = (scaledY - 300) * miniScale;

      targetX = headerCenterX + relativeX + shiftX + idleX;
      targetY = headerCenterY + relativeY + shiftY + idleY;
    }

    // Local mouse hover repelling effect
    const dxMouse = targetX - mousePosLocalRef.current.x;
    const dyMouse = targetY - mousePosLocalRef.current.y;
    const distMouse = Math.hypot(dxMouse, dyMouse);
    const avoidanceRadius = 32;

    if (distMouse < avoidanceRadius && distMouse > 0) {
      const force = (avoidanceRadius - distMouse) / avoidanceRadius;
      const strength = force * 16;
      targetX += (dxMouse / distMouse) * strength;
      targetY += (dyMouse / distMouse) * strength;
    }

    // Dynamic easing for fluid flight between MOKA and eyes
    const dxDist = targetX - p.x;
    const dyDist = targetY - p.y;
    const dist = Math.hypot(dxDist, dyDist);
    const ease = dist > 35 ? (0.13 + p.speedOffset * 0.04) : (0.12 + p.speedOffset * 0.08);
    const effectiveEase = Math.min(1 - Math.pow(Math.max(0, 1 - ease), dt), 1);

    p.x += (targetX - p.x) * effectiveEase;
    p.y += (targetY - p.y) * effectiveEase;

      const currentSize = p.size * 0.62; // Crisp dot size (~1.1px - 1.5px radius)

    // Clean particle dot
    ctx.fillStyle = `rgba(${rgb}, ${p.alpha})`;
    ctx.beginPath();
    ctx.arc(p.x, p.y, currentSize, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.restore();
  animationFrameId.current = requestAnimationFrame(render);
};

render();

// Mouse movement listener (Window gaze + Local canvas hover)
const handleMouseMove = (e: MouseEvent) => {
  const cx = window.innerWidth / 2;
  const cy = window.innerHeight / 2;
  mouseTargetRef.current = {
    x: Math.max(-1, Math.min(1, (e.clientX - cx) / cx)),
    y: Math.max(-1, Math.min(1, (e.clientY - cy) / cy)),
  };

  if (containerRef.current) {
    const rect = containerRef.current.getBoundingClientRect();
    mousePosLocalRef.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }
};

const handleMouseLeave = () => {
  mousePosLocalRef.current = { x: -9999, y: -9999 };
};

window.addEventListener('mousemove', handleMouseMove);
const container = containerRef.current;
if (container) {
  container.addEventListener('mouseleave', handleMouseLeave);
}

return () => {
  window.removeEventListener('mousemove', handleMouseMove);
  if (container) {
    container.removeEventListener('mouseleave', handleMouseLeave);
  }
  if (animationFrameId.current) {
    cancelAnimationFrame(animationFrameId.current);
  }
};
  }, [eyeStepX, eyeStepY, mokaStepX, mokaStepY]);

return (
  <div
    ref={containerRef}
    onClick={handleClick}
    onKeyDown={handleKeyDown}
    role="button"
    tabIndex={0}
    title="MoKa Home"
    aria-label="MoKa Home Navigation"
    data-header-mode={mode}
    className={`relative h-11 w-36 sm:w-40 flex items-center justify-center cursor-pointer select-none rounded-xl transition-all duration-200 hover:scale-[1.03] active:scale-[0.98] focus:outline-none focus-visible:ring-1 ${themeConfig.ring} ${className}`}
  >
    <canvas
      ref={canvasRef}
      style={{
        width: '144px',
        height: '44px',
      }}
      className="block pointer-events-none"
    />
  </div>
);
};

export default HeaderParticleLogo;
