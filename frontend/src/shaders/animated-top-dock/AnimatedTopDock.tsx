import { useEffect, useRef, useState } from "react";
import { createTopDockController } from "./topDockController";

export type AnimatedTopDockProps = {
  proximity?: number;
  spring?: number;
  damping?: number;
  widthGrowth?: number;
  heightGrowth?: number;
  drop?: number;
  className?: string;
  defaultActive?: string;
};


export const ANIMATED_TOP_DOCK_DEFAULTS = {
  proximity: 122,
  spring: 0.19,
  damping: 0.7,
  widthGrowth: 17,
  heightGrowth: 16,
  drop: 3.5,
} as const;

const ITEMS = [
  {
    id: "home",
    label: "HOME",
    icon: (
      <>
        <path d="M2.5 7.5L8 3l5.5 4.5v6a1 1 0 0 1-1 1h-9a1 1 0 0 1-1-1v-6Z" />
        <path d="M6 14.5v-4.5h4v4.5" />
      </>
    ),
  },
  {
    id: "chat",
    label: "CHAT",
    icon: (
      <>
        <path d="M2.5 3.5h11a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H6l-3.5 2.5V4.5a1 1 0 0 1 1-1Z" />
        <path d="M5.5 7.5h.01M8 7.5h.01M10.5 7.5h.01" />
      </>
    ),
  },
  {
    id: "cozmo",
    label: "COZMO",
    icon: (
      <>
        <rect x="2.5" y="4" width="11" height="8.5" rx="2" />
        <circle cx="5.5" cy="8.25" r="1" fill="currentColor" />
        <circle cx="10.5" cy="8.25" r="1" fill="currentColor" />
        <path d="M8 2v2M4.5 14.5v-2M11.5 14.5v-2" />
      </>
    ),
  },
  {
    id: "about",
    label: "ABOUT PROJECT",
    icon: (
      <>
        <rect x="2.25" y="2.25" width="4.5" height="4.5" rx=".8" />
        <rect x="9.25" y="2.25" width="4.5" height="4.5" rx=".8" />
        <rect x="2.25" y="9.25" width="4.5" height="4.5" rx=".8" />
        <rect x="9.25" y="9.25" width="4.5" height="4.5" rx=".8" />
      </>
    ),
  },
] as const;

export function AnimatedTopDock({ className = "", defaultActive = "home", ...props }: AnimatedTopDockProps) {
  const rootRef = useRef<HTMLElement>(null);
  const optionsRef = useRef({ ...ANIMATED_TOP_DOCK_DEFAULTS, ...props });
  optionsRef.current = { ...ANIMATED_TOP_DOCK_DEFAULTS, ...props };
  const [active, setActive] = useState(defaultActive);


  useEffect(() => {
    const root = rootRef.current;
    if (!root) return undefined;
    return createTopDockController(root, () => optionsRef.current);
  }, []);

  const handleClick = (id: string) => {
    setActive(id);
    if (id === "home") {
      if (window.location.pathname !== "/" && window.location.pathname !== "") {
        window.history.pushState({}, "", "/");
        window.dispatchEvent(new Event("popstate"));
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else if (id === "chat") {
      window.history.pushState({}, "", "/chat");
      window.dispatchEvent(new Event("popstate"));
    } else if (id === "cozmo") {
      window.history.pushState({}, "", "/cozmo");
      window.dispatchEvent(new Event("popstate"));
    } else if (id === "about") {
      if (window.location.pathname !== "/" && window.location.pathname !== "") {
        window.history.pushState({}, "", "/");
        window.dispatchEvent(new Event("popstate"));
        setTimeout(() => {
          document.querySelector("#project-intro")?.scrollIntoView({ behavior: "smooth" });
        }, 100);
      } else {
        document.querySelector("#project-intro")?.scrollIntoView({ behavior: "smooth" });
      }
    }
  };

  return (
    <div className={`animated-top-dock-component${className ? ` ${className}` : ""}`}>
      <nav ref={rootRef} className="animated-top-dock__nav" aria-label="Animated top dock" data-dock-state="idle" data-dock-max="0.00">
        {ITEMS.map((item) => (
          <button
            key={item.id}
            className="animated-top-dock__item animated-top-dock__link"
            data-dock-item
            type="button"
            aria-pressed={active === item.id}
            onClick={() => handleClick(item.id)}
          >
            <span className="animated-top-dock__icon" aria-hidden="true">
              <svg viewBox="0 0 16 16">{item.icon}</svg>
            </span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
