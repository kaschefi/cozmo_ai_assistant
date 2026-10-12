import { useState, useEffect } from 'react';

export interface EyeTrackingOffsets {
  offsetX: number;
  offsetY: number;
}

/**
 * Custom React hook that tracks the mouse pointer's position relative to the center of the viewport.
 * Calculates clamped 2D cartesian offsets for look-around animations.
 *
 * @param maxRadius - The maximum offset radius in pixels (defaults to 16).
 */
export function useCozmoEyeTracking(maxRadius = 16): EyeTrackingOffsets {
  const [offsets, setOffsets] = useState<EyeTrackingOffsets>({ offsetX: 0, offsetY: 0 });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleMouseMove = (event: MouseEvent): void => {
      const centerX = window.innerWidth / 2;
      const centerY = window.innerHeight / 2;

      // Measure delta from center of the screen
      const dx = event.clientX - centerX;
      const dy = event.clientY - centerY;

      // Calculate angle relative to the center
      const angle = Math.atan2(dy, dx);

      // Measure total distance from center
      const distance = Math.sqrt(dx * dx + dy * dy);

      // Clamp target radius
      const clampedRadius = Math.min(distance * 0.05, maxRadius);

      // Project bounded movement back to cartesian coordinates
      setOffsets({
        offsetX: Math.cos(angle) * clampedRadius,
        offsetY: Math.sin(angle) * clampedRadius,
      });
    };

    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [maxRadius]);

  return offsets;
}

export default useCozmoEyeTracking;
