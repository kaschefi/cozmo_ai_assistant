import React, { useRef, useState, useEffect, useCallback } from 'react';

export interface AnimatedTopDockProps {
  proximity?: number;
  spring?: number;
  damping?: number;
  widthGrowth?: number;
  heightGrowth?: number;
  drop?: number;
  className?: string;
  activeId?: string;
  onItemSelect?: (id: string) => void;
}

export const ANIMATED_TOP_DOCK_DEFAULTS = {
  proximity: 122,
  spring: 0.19,
  damping: 0.7,
  widthGrowth: 17,
  heightGrowth: 16,
  drop: 3.5,
} as const;

interface DockItemDef {
  id: string;
  label: string;
  href?: string;
  isExternal?: boolean;
  icon: React.ReactNode;
}

const DOCK_ITEMS: DockItemDef[] = [
  {
    id: 'cozmo',
    label: 'COZMO',
    href: '/cozmo',
    icon: (
      <svg viewBox="0 0 16 16" className="w-3.5 h-3.5 fill-none stroke-current stroke-[1.3] stroke-linecap-round stroke-linejoin-round">
        {/* Robot / Cozmo Face */}
        <rect x="2.5" y="4" width="11" height="8.5" rx="2" />
        <circle cx="5.5" cy="8.25" r="1" fill="currentColor" />
        <circle cx="10.5" cy="8.25" r="1" fill="currentColor" />
        <path d="M8 2v2M4.5 14.5v-2M11.5 14.5v-2" />
      </svg>
    ),
  },
  {
    id: 'chat',
    label: 'CHAT',
    href: '/chat',
    icon: (
      <svg viewBox="0 0 16 16" className="w-3.5 h-3.5 fill-none stroke-current stroke-[1.3] stroke-linecap-round stroke-linejoin-round">
        {/* Chat / Speech Wave */}
        <path d="M2.5 3.5h11a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H6l-3.5 2.5V4.5a1 1 0 0 1 1-1Z" />
        <path d="M5.5 7.5h.01M8 7.5h.01M10.5 7.5h.01" />
      </svg>
    ),
  },
  {
    id: 'system',
    label: 'SYSTEM',
    href: '#project-intro',
    icon: (
      <svg viewBox="0 0 16 16" className="w-3.5 h-3.5 fill-none stroke-current stroke-[1.3] stroke-linecap-round stroke-linejoin-round">
        {/* System Matrix / Grid */}
        <rect x="2.25" y="2.25" width="4.5" height="4.5" rx="0.8" />
        <rect x="9.25" y="2.25" width="4.5" height="4.5" rx="0.8" />
        <rect x="2.25" y="9.25" width="4.5" height="4.5" rx="0.8" />
        <rect x="9.25" y="9.25" width="4.5" height="4.5" rx="0.8" />
      </svg>
    ),
  },
  {
    id: 'features',
    label: 'FEATURES',
    href: '#features',
    icon: (
      <svg viewBox="0 0 16 16" className="w-3.5 h-3.5 fill-none stroke-current stroke-[1.3] stroke-linecap-round stroke-linejoin-round">
        {/* Method / Network */}
        <circle cx="3" cy="8" r="1.5" />
        <circle cx="12.5" cy="3.5" r="1.5" />
        <circle cx="12.5" cy="12.5" r="1.5" />
        <path d="M4.5 7.3 11 4.2M4.5 8.7l6.5 3.1" />
      </svg>
    ),
  },
  {
    id: 'talk',
    label: 'TALK',
    href: '#talk',
    icon: (
      <svg viewBox="0 0 16 16" className="w-3.5 h-3.5 fill-none stroke-current stroke-[1.3] stroke-linecap-round stroke-linejoin-round">
        {/* Audio / Voice Wave */}
        <path d="M2.5 8h1M5 5.5v5M8 3v10M11 5.5v5M13.5 8h1" />
      </svg>
    ),
  },
];

const clamp = (val: number, min: number, max: number) => Math.max(min, Math.min(max, val));

export const AnimatedTopDock: React.FC<AnimatedTopDockProps> = ({
  proximity = ANIMATED_TOP_DOCK_DEFAULTS.proximity,
  spring = ANIMATED_TOP_DOCK_DEFAULTS.spring,
  damping = ANIMATED_TOP_DOCK_DEFAULTS.damping,
  widthGrowth = ANIMATED_TOP_DOCK_DEFAULTS.widthGrowth,
  heightGrowth = ANIMATED_TOP_DOCK_DEFAULTS.heightGrowth,
  drop = ANIMATED_TOP_DOCK_DEFAULTS.drop,
  className = '',
  activeId,
  onItemSelect,
}) => {
  const navRef = useRef<HTMLElement | null>(null);
  const [selectedId, setSelectedId] = useState<string>(activeId || 'system');
  const paramsRef = useRef({ proximity, spring, damping, widthGrowth, heightGrowth, drop });

  useEffect(() => {
    paramsRef.current = { proximity, spring, damping, widthGrowth, heightGrowth, drop };
  }, [proximity, spring, damping, widthGrowth, heightGrowth, drop]);

  useEffect(() => {
    if (activeId) setSelectedId(activeId);
  }, [activeId]);

  // Spring Physics Controller (ThreeUI Architecture)
  useEffect(() => {
    const nav = navRef.current;
    if (!nav) return;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const canHover = window.matchMedia('(hover:hover) and (pointer:fine)');

    const items = Array.from(nav.querySelectorAll<HTMLElement>('[data-dock-item]')).map((el) => ({
      element: el,
      baseWidth: 0,
      baseHeight: 0,
      value: 0,
      velocity: 0,
      target: 0,
    }));

    let isEnabled = false;
    let isTrackingPointer = false;
    let isSpringActive = false;
    let rafId = 0;

    const checkEnabled = () =>
      !prefersReducedMotion.matches &&
      nav.clientWidth > 0 &&
      window.innerWidth > 600 &&
      canHover.matches;

    const handleResize = () => {
      isEnabled = checkEnabled();
      for (const item of items) {
        item.element.style.width = '';
        item.element.style.height = '';
        item.element.style.transform = '';
        item.element.dataset.dockNear = 'false';
      }
      for (const item of items) {
        const rect = item.element.getBoundingClientRect();
        item.baseWidth = rect.width;
        item.baseHeight = rect.height;
        item.value = 0;
        item.velocity = 0;
        item.target = 0;
      }
      isTrackingPointer = false;
      isSpringActive = false;
      nav.dataset.dockState = isEnabled ? 'idle' : 'static';
      nav.dataset.dockMax = '0.00';
    };

    const handlePointerMove = (clientX: number) => {
      if (!isEnabled) return;
      const p = paramsRef.current;
      const rects = items.map((it) => it.element.getBoundingClientRect());

      for (let i = 0; i < items.length; i++) {
        const itemCenterX = rects[i].left + rects[i].width * 0.5;
        const normDist = clamp(1 - Math.abs(clientX - itemCenterX) / Math.max(1, p.proximity), 0, 1);
        // Smoothstep interpolation
        const smoothed = normDist * normDist * (3 - 2 * normDist);
        items[i].target = smoothed;
        items[i].element.dataset.dockNear = smoothed > 0.08 ? 'true' : 'false';
      }

      isTrackingPointer = true;
      isSpringActive = true;
      nav.dataset.dockState = 'active';
    };

    const handleFocusItem = (targetEl: HTMLElement) => {
      if (!isEnabled) return;
      const idx = items.findIndex((it) => it.element === targetEl);
      if (idx < 0) return;

      items.forEach((it, i) => {
        it.target = i === idx ? 1 : Math.abs(i - idx) === 1 ? 0.24 : 0;
        it.element.dataset.dockNear = it.target > 0.08 ? 'true' : 'false';
      });

      isTrackingPointer = false;
      isSpringActive = true;
      nav.dataset.dockState = 'focus';
    };

    const handlePointerLeave = () => {
      isTrackingPointer = false;
      isSpringActive = true;
      items.forEach((it) => {
        it.target = 0;
        it.element.dataset.dockNear = 'false';
      });
    };

    const updatePhysics = () => {
      if (isEnabled && isSpringActive) {
        const p = paramsRef.current;
        let isMoving = false;
        let maxVal = 0;

        for (const item of items) {
          item.velocity += (item.target - item.value) * p.spring;
          item.velocity *= p.damping;
          item.value += item.velocity;

          if (Math.abs(item.target - item.value) < 1e-3 && Math.abs(item.velocity) < 1e-3) {
            item.value = item.target;
            item.velocity = 0;
          } else {
            isMoving = true;
          }

          const c = clamp(item.value, 0, 1.08);
          const isLogo = item.element.classList.contains('moka-dock__logo');
          const wGrowth = isLogo ? p.widthGrowth * (14 / 17) : Math.min(p.widthGrowth, item.baseWidth * 0.24);
          const hGrowth = isLogo ? p.heightGrowth * (14 / 16) : p.heightGrowth;

          item.element.style.width = `${(item.baseWidth + wGrowth * c).toFixed(2)}px`;
          item.element.style.height = `${(item.baseHeight + hGrowth * c).toFixed(2)}px`;
          item.element.style.transform = `translateY(${(c * p.drop).toFixed(2)}px)`;

          maxVal = Math.max(maxVal, c);
        }

        nav.dataset.dockMax = maxVal.toFixed(2);

        if (!isMoving) {
          isSpringActive = false;
          if (items.every((it) => it.target === 0)) {
            nav.dataset.dockState = 'idle';
          }
        }
      }

      rafId = requestAnimationFrame(updatePhysics);
    };

    const onPointerMoveEvent = (e: PointerEvent) => handlePointerMove(e.clientX);
    const onWindowPointerMove = (e: PointerEvent) => {
      if (!isTrackingPointer) return;
      const navRect = nav.getBoundingClientRect();
      const itemRects = items.map((it) => it.element.getBoundingClientRect());
      const maxBottom = Math.max(navRect.bottom, ...itemRects.map((r) => r.bottom));

      if (
        e.clientX < navRect.left ||
        e.clientX > navRect.right ||
        e.clientY < navRect.top ||
        e.clientY > maxBottom
      ) {
        handlePointerLeave();
      }
    };

    const onFocusIn = (e: FocusEvent) => {
      const target = (e.target as HTMLElement)?.closest<HTMLElement>('[data-dock-item]');
      if (target) handleFocusItem(target);
    };

    const onFocusOut = () => {
      requestAnimationFrame(() => {
        if (!nav.contains(document.activeElement)) {
          handlePointerLeave();
        }
      });
    };

    const onKeyDown = (e: KeyboardEvent) => {
      const target = (e.target as HTMLElement)?.closest<HTMLElement>('[data-dock-item]');
      if (target && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        target.click();
      }
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(nav.parentElement || nav);

    nav.addEventListener('pointermove', onPointerMoveEvent);
    nav.addEventListener('pointerleave', handlePointerLeave);
    nav.addEventListener('focusin', onFocusIn);
    nav.addEventListener('focusout', onFocusOut);
    nav.addEventListener('keydown', onKeyDown);
    nav.addEventListener('click', handlePointerLeave);
    window.addEventListener('pointermove', onWindowPointerMove, { passive: true });
    prefersReducedMotion.addEventListener('change', handleResize);
    canHover.addEventListener('change', handleResize);

    handleResize();
    rafId = requestAnimationFrame(updatePhysics);

    return () => {
      cancelAnimationFrame(rafId);
      resizeObserver.disconnect();
      nav.removeEventListener('pointermove', onPointerMoveEvent);
      nav.removeEventListener('pointerleave', handlePointerLeave);
      nav.removeEventListener('focusin', onFocusIn);
      nav.removeEventListener('focusout', onFocusOut);
      nav.removeEventListener('keydown', onKeyDown);
      nav.removeEventListener('click', handlePointerLeave);
      window.removeEventListener('pointermove', onWindowPointerMove);
      prefersReducedMotion.removeEventListener('change', handleResize);
      canHover.removeEventListener('change', handleResize);
    };
  }, []);

  const handleItemClick = useCallback(
    (item: DockItemDef | 'home', e?: React.MouseEvent) => {
      if (item === 'home') {
        setSelectedId('home');
        if (onItemSelect) onItemSelect('home');
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
      }

      setSelectedId(item.id);
      if (onItemSelect) onItemSelect(item.id);

      if (item.href?.startsWith('/')) {
        if (e) e.preventDefault();
        window.history.pushState({}, '', item.href);
        window.dispatchEvent(new Event('popstate'));
      } else if (item.href?.startsWith('#')) {
        if (e) e.preventDefault();
        const targetEl = document.querySelector(item.href);
        if (targetEl) {
          targetEl.scrollIntoView({ behavior: 'smooth' });
        }
      }
    },
    [onItemSelect]
  );

  return (
    <div className={`moka-top-dock-container relative flex items-center justify-center isolate pointer-events-auto ${className}`}>
      <nav
        ref={navRef}
        className="moka-dock__nav flex items-center gap-1.5 h-10 px-2 py-1 overflow-visible rounded-xl border border-cyan-500/20 bg-[#090d16]/85 backdrop-blur-xl shadow-[0_12px_34px_rgba(0,0,0,0.65),inset_0_1px_rgba(0,240,255,0.12)] transition-colors duration-200 isolation-isolate"
        aria-label="MoKa Autonomous Top Navigation Dock"
        data-dock-state="idle"
        data-dock-max="0.00"
      >
        {/* MoKa Brand Mark Item */}
        <button
          className="moka-dock__item moka-dock__logo relative z-[6] inline-flex flex-none items-center justify-center w-7 h-7 p-0 border border-transparent rounded-lg outline-none bg-gradient-to-br from-cyan-400 to-blue-600 shadow-[0_0_12px_rgba(0,243,255,0.3)] transition-all duration-200 cursor-pointer overflow-hidden group focus-visible:ring-2 focus-visible:ring-cyan-400"
          data-dock-item="true"
          type="button"
          aria-label="Home"
          onClick={(e) => handleItemClick('home', e)}
        >
          <svg viewBox="0 0 24 24" className="w-4 h-4 fill-none stroke-[#08090c] stroke-[2.2] stroke-linecap-round stroke-linejoin-round group-hover:scale-110 transition-transform">
            <path d="M4 19V5l8 6 8-6v14" />
          </svg>
        </button>

        {/* Navigation Items */}
        {DOCK_ITEMS.map((item) => {
          const isPressed = selectedId === item.id;
          return (
            <button
              key={item.id}
              className={`moka-dock__item moka-dock__link relative z-[6] inline-flex flex-none items-center justify-center gap-1.5 h-7 px-2.5 border rounded-lg outline-none font-mono text-[11px] font-semibold tracking-wider uppercase whitespace-nowrap transition-all duration-150 cursor-pointer select-none ${
                isPressed
                  ? 'text-slate-950 bg-gradient-to-r from-cyan-400 to-cyan-300 border-cyan-300 shadow-[0_0_16px_rgba(0,243,255,0.55)]'
                  : 'text-slate-400 bg-slate-900/80 border-slate-800/80 hover:text-cyan-300 hover:border-cyan-500/40 hover:bg-slate-850'
              }`}
              data-dock-item="true"
              type="button"
              aria-pressed={isPressed}
              onClick={(e) => handleItemClick(item, e)}
            >
              <span className="moka-dock__icon inline-flex flex-none items-center justify-center w-3.5 h-3.5 transition-opacity opacity-75 group-hover:opacity-100">
                {item.icon}
              </span>
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Dock CSS Enhancements */}
      <style>{`
        .moka-dock__item {
          transform-origin: 50% 0;
          will-change: width, height, transform;
          -webkit-backdrop-filter: blur(14px) saturate(70%);
          backdrop-filter: blur(14px) saturate(70%);
        }
        .moka-dock__item[data-dock-near="true"],
        .moka-dock__item:focus-visible {
          z-index: 7;
          border-color: rgba(0, 240, 255, 0.45);
          box-shadow: 0 8px 18px rgba(0, 0, 0, 0.4), 0 0 10px rgba(0, 243, 255, 0.25);
        }
        .moka-dock__item[data-dock-near="true"] .moka-dock__icon,
        .moka-dock__item:focus-visible .moka-dock__icon {
          opacity: 1;
        }
        @media (max-width: 600px) {
          .moka-dock__nav {
            gap: 2px;
            height: 34px;
            padding: 2px 4px;
          }
          .moka-dock__item {
            height: 26px !important;
            transform: none !important;
          }
          .moka-dock__logo {
            width: 26px !important;
            height: 26px !important;
          }
          .moka-dock__link {
            width: auto !important;
            padding: 0 6px;
            font-size: 9px;
            letter-spacing: 0.05em;
          }
          .moka-dock__icon {
            display: none;
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .moka-dock__item {
            transform: none !important;
          }
        }
      `}</style>
    </div>
  );
};

export default AnimatedTopDock;
