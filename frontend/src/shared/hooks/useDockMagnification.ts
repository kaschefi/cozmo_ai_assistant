import { useEffect, useRef } from 'react';

export interface DockMagnificationOptions {
  /** Proximity radius in pixels within which buttons respond to the cursor */
  proximity?: number;
  /** Spring physics stiffness coefficient (0.1 - 0.4) */
  spring?: number;
  /** Spring physics damping coefficient (0.5 - 0.85) */
  damping?: number;
  /** Maximum upward pop translation in pixels */
  popDistance?: number;
  /** Maximum scaling factor growth */
  scaleGrowth?: number;
}

/**
 * useDockMagnification Hook
 *
 * Implements macOS-style dock spring physics for segmented button controls.
 * When the cursor hovers over any button, that button pops up and expands,
 * and neighboring buttons within proximity also pop up proportionally based on distance.
 */
export function useDockMagnification<T extends HTMLElement = HTMLDivElement>(
  options: DockMagnificationOptions = {}
) {
  const containerRef = useRef<T | null>(null);

  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;

    const reducedQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const precisionQuery = window.matchMedia('(hover:hover) and (pointer:fine)');
    if (reducedQuery.matches || !precisionQuery.matches) return;

    const proximityRadius = options.proximity ?? 85;
    const spring = options.spring ?? 0.22;
    const damping = options.damping ?? 0.68;
    const popDistance = options.popDistance ?? 4;
    const scaleGrowth = options.scaleGrowth ?? 0.04;

    type ItemState = {
      element: HTMLElement;
      value: number;
      velocity: number;
      target: number;
    };

    let items: ItemState[] = [];
    let frameId = 0;
    let isMoving = false;
    let isPointerInside = false;

    const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v));

    const syncItems = () => {
      const elements = Array.from(root.querySelectorAll<HTMLElement>('[data-dock-item]'));
      // Keep existing physics values if elements match
      items = elements.map((element) => {
        const existing = items.find((it) => it.element === element);
        return existing || { element, value: 0, velocity: 0, target: 0 };
      });
    };

    syncItems();

    const onPointerMove = (e: PointerEvent) => {
      isPointerInside = true;
      syncItems();
      const clientX = e.clientX;
      const rects = items.map((s) => s.element.getBoundingClientRect());

      for (let i = 0; i < items.length; i++) {
        const center = rects[i].left + rects[i].width * 0.5;
        const dist = Math.abs(clientX - center);
        const prox = clamp(1 - dist / proximityRadius, 0, 1);
        // Cubic smoothstep curve: 3p^2 - 2p^3
        const influence = prox * prox * (3 - 2 * prox);
        items[i].target = influence;
      }
      isMoving = true;
    };

    const resetTargets = () => {
      isPointerInside = false;
      for (const item of items) {
        item.target = 0;
      }
      isMoving = true;
    };

    const updateLoop = () => {
      if (isMoving) {
        let stillMoving = false;

        for (const item of items) {
          item.velocity += (item.target - item.value) * spring;
          item.velocity *= damping;
          item.value += item.velocity;

          if (Math.abs(item.target - item.value) < 0.002 && Math.abs(item.velocity) < 0.002) {
            item.value = item.target;
            item.velocity = 0;
          } else {
            stillMoving = true;
          }

          const v = clamp(item.value, 0, 1.1);
          const y = -(v * popDistance);
          const s = 1 + v * scaleGrowth;

          item.element.style.transform = `translateY(${y.toFixed(2)}px) scale(${s.toFixed(3)})`;
          item.element.style.zIndex = v > 0.1 ? '10' : '1';
        }

        if (!stillMoving && !isPointerInside) {
          isMoving = false;
          for (const item of items) {
            item.element.style.transform = '';
            item.element.style.zIndex = '';
          }
        }
      }

      frameId = requestAnimationFrame(updateLoop);
    };

    root.addEventListener('pointermove', onPointerMove);
    root.addEventListener('pointerleave', resetTargets);
    frameId = requestAnimationFrame(updateLoop);

    return () => {
      cancelAnimationFrame(frameId);
      root.removeEventListener('pointermove', onPointerMove);
      root.removeEventListener('pointerleave', resetTargets);
      for (const item of items) {
        item.element.style.transform = '';
        item.element.style.zIndex = '';
      }
    };
  }, [options.proximity, options.spring, options.damping, options.popDistance, options.scaleGrowth]);

  return containerRef;
}

export default useDockMagnification;

