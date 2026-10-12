import { useState, useEffect } from 'react';

export interface MouseCoordinates {
  x: number;
  y: number;
}

/**
 * Custom hook that tracks the mouse pointer's coordinates relative to the viewport.
 * Uses React state to allow components that depend on coordinates to re-render.
 */
export function useMouseTracking(): MouseCoordinates {
  const [coords, setCoords] = useState<MouseCoordinates>({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent): void => {
      setCoords({
        x: event.clientX,
        y: event.clientY,
      });
    };

    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  return coords;
}
