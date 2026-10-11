export type VerticalDockOptions = {
  proximity: number;
  spring: number;
  damping: number;
  widthGrowth: number;
  heightGrowth: number;
  nudge: number;
};

type DockItemState = {
  element: HTMLElement;
  labelElement: HTMLElement | null;
  baseWidth: number;
  baseHeight: number;
  value: number;
  velocity: number;
  target: number;
};

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

export const VERTICAL_DOCK_DEFAULTS: VerticalDockOptions = {
  proximity: 48,
  spring: 0.24,
  damping: 0.68,
  widthGrowth: 72,
  heightGrowth: 4,
  nudge: 6,
};

export function createVerticalDockController(
  root: HTMLElement,
  getOptions: () => VerticalDockOptions = () => VERTICAL_DOCK_DEFAULTS
) {
  const reducedQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  const precisionQuery = window.matchMedia("(hover:hover) and (pointer:fine)");

  const items: DockItemState[] = Array.from(root.querySelectorAll<HTMLElement>("[data-dock-item]")).map((element) => ({
    element,
    labelElement: element.querySelector<HTMLElement>("[data-dock-label]"),
    baseWidth: 40,
    baseHeight: 40,
    value: 0,
    velocity: 0,
    target: 0,
  }));

  let enabled = false;
  let pointerActive = false;
  let dirty = false;
  let frame = 0;

  const canAnimate = () => !reducedQuery.matches && precisionQuery.matches;

  const measure = () => {
    enabled = canAnimate();
    for (const state of items) {
      state.element.style.width = "";
      state.element.style.height = "";
      state.element.style.transform = "";
      state.element.dataset.dockNear = "false";
      if (state.labelElement) {
        state.labelElement.style.opacity = "0";
      }
    }
    for (const state of items) {
      const rect = state.element.getBoundingClientRect();
      state.baseWidth = rect.width > 0 ? rect.width : 40;
      state.baseHeight = rect.height > 0 ? rect.height : 40;
      state.value = 0;
      state.velocity = 0;
      state.target = 0;
    }
    pointerActive = false;
    dirty = false;
    root.dataset.dockState = enabled ? "idle" : "static";
  };

  const setTargets = (clientY: number) => {
    if (!enabled) return;
    const options = getOptions();
    const rects = items.map((state) => state.element.getBoundingClientRect());
    for (let index = 0; index < items.length; index += 1) {
      const center = rects[index].top + rects[index].height * 0.5;
      const proximity = clamp(1 - Math.abs(clientY - center) / Math.max(1, options.proximity), 0, 1);
      // Cubic easing for parabolic smooth proximity curve
      const influence = proximity * proximity * (3 - 2 * proximity);
      items[index].target = influence;
      items[index].element.dataset.dockNear = influence > 0.08 ? "true" : "false";
    }
    pointerActive = true;
    dirty = true;
    root.dataset.dockState = "active";
  };

  const reset = () => {
    pointerActive = false;
    dirty = true;
    items.forEach((state) => {
      state.target = 0;
      state.element.dataset.dockNear = "false";
    });
  };

  const draw = () => {
    if (enabled && dirty) {
      const options = getOptions();
      let moving = false;

      for (const state of items) {
        state.velocity += (state.target - state.value) * options.spring;
        state.velocity *= options.damping;
        state.value += state.velocity;

        if (Math.abs(state.target - state.value) < 0.001 && Math.abs(state.velocity) < 0.001) {
          state.value = state.target;
          state.velocity = 0;
        } else {
          moving = true;
        }

        const value = clamp(state.value, 0, 1.08);
        const extraWidth = options.widthGrowth * value;
        const extraHeight = options.heightGrowth * value;
        const nudgeX = options.nudge * value;

        state.element.style.width = `${(state.baseWidth + extraWidth).toFixed(1)}px`;
        state.element.style.height = `${(state.baseHeight + extraHeight).toFixed(1)}px`;
        state.element.style.transform = `translateX(${nudgeX.toFixed(1)}px)`;

        if (state.labelElement) {
          // Label smoothly fades in once the pill expands past initial width
          const labelOpacity = clamp((value - 0.28) / 0.68, 0, 1);
          state.labelElement.style.opacity = labelOpacity.toFixed(2);
        }
      }

      if (!moving) {
        dirty = false;
        if (items.every((state) => state.target === 0)) {
          root.dataset.dockState = "idle";
        }
      }
    }
    frame = requestAnimationFrame(draw);
  };

  const onPointerMove = (event: PointerEvent) => setTargets(event.clientY);
  const onWindowPointerMove = (event: PointerEvent) => {
    if (!pointerActive) return;
    const rootRect = root.getBoundingClientRect();
    const itemRects = items.map((state) => state.element.getBoundingClientRect());
    const right = Math.max(rootRect.right, ...itemRects.map((rect) => rect.right)) + 40;
    const top = Math.min(rootRect.top, ...itemRects.map((rect) => rect.top)) - 40;
    const bottom = Math.max(rootRect.bottom, ...itemRects.map((rect) => rect.bottom)) + 40;
    const left = rootRect.left - 20;

    const outside =
      event.clientX < left ||
      event.clientX > right ||
      event.clientY < top ||
      event.clientY > bottom;

    if (outside) reset();
  };

  const onFocusIn = (event: FocusEvent) => {
    const item = (event.target as HTMLElement | null)?.closest<HTMLElement>("[data-dock-item]");
    if (item) {
      const idx = items.findIndex((s) => s.element === item);
      if (idx >= 0) {
        items.forEach((s, i) => {
          s.target = i === idx ? 1 : Math.abs(i - idx) === 1 ? 0.3 : 0;
          s.element.dataset.dockNear = s.target > 0.08 ? "true" : "false";
        });
        pointerActive = false;
        dirty = true;
        root.dataset.dockState = "focus";
      }
    }
  };

  const onFocusOut = () =>
    requestAnimationFrame(() => {
      if (!root.contains(document.activeElement)) reset();
    });

  const onClick = () => reset();

  const resizeObserver = new ResizeObserver(measure);
  resizeObserver.observe(root.parentElement ?? root);

  root.addEventListener("pointermove", onPointerMove);
  root.addEventListener("pointerleave", reset);
  root.addEventListener("focusin", onFocusIn);
  root.addEventListener("focusout", onFocusOut);
  root.addEventListener("click", onClick);
  window.addEventListener("pointermove", onWindowPointerMove, { passive: true });
  reducedQuery.addEventListener("change", measure);
  precisionQuery.addEventListener("change", measure);

  measure();
  frame = requestAnimationFrame(draw);

  return () => {
    cancelAnimationFrame(frame);
    resizeObserver.disconnect();
    root.removeEventListener("pointermove", onPointerMove);
    root.removeEventListener("pointerleave", reset);
    root.removeEventListener("focusin", onFocusIn);
    root.removeEventListener("focusout", onFocusOut);
    root.removeEventListener("click", onClick);
    window.removeEventListener("pointermove", onWindowPointerMove);
    reducedQuery.removeEventListener("change", measure);
    precisionQuery.removeEventListener("change", measure);
  };
}
