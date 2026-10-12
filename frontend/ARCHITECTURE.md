# Frontend Architecture & Directory Structure

This document outlines the **Feature-Oriented (Vertical Slice)** architecture adopted by the frontend application.

---

## 1. Directory Structure Overview

The source tree is organized by **business domain / feature** rather than arbitrary technical layers (such as flat `components/`, `hooks/`, `utils/`). High-cohesion code stays together, making features easy to locate, test, refactor, and safely delete.

```text
src/
├── assets/                        # Static assets (images, vector graphics)
│
├── features/                      # Business Domains (Vertical Slices)
│   ├── landing/                   # Moka Landing & Ecosystem Showcase
│   │   ├── components/            # MokaLanding, Hero, Intro, Marquee, TalkSection
│   │   ├── data/                  # mokaPagesData.ts (page copy & specs)
│   │   └── index.ts               # Public feature exports
│   │
│   ├── chat/                      # AI Assistant & Chat Interface
│   │   ├── components/            # ChatInterface, Drawers, Rails, Telemetry, VoiceWaveform
│   │   ├── services/              # chatHistory.ts (REST APIs, LangSmith, LocalStorage)
│   │   └── index.ts               # Public feature exports
│   │
│   └── cozmo/                     # Robotics & Spatial Dashboard
│       ├── components/            # CozmoDashboard, 2D/3D World Maps, Model Previews
│       ├── hooks/                 # useCozmoEyeTracking.ts
│       └── index.ts               # Public feature exports
│
├── shared/                        # Domain-Agnostic Reusable Foundation
│   ├── components/
│   │   ├── layout/                # Header, ThemeSelector, AnimatedTopDock, Controllers
│   │   └── backgrounds/           # Theme shader backgrounds (Constellation, GoldVeins, etc.)
│   ├── context/                   # ThemeContext (Global theme state & provider)
│   ├── hooks/                     # useLocation (router), useMouseTracking (parallax)
│   ├── shaders/                   # Three.js animation pipelines, shaders & typography
│   ├── utils/                     # Utility functions (cn, class mergers)
│   └── index.ts                   # Top-level shared module exports
│
├── App.css
├── App.tsx                        # Root router routing to feature entries
├── index.css
└── main.tsx                       # React DOM root & ThemeProvider mounting
```

---

## 2. Decision Rule: "Feature-Local" vs. "Shared"

When creating or refactoring any component, hook, or utility, the following rules dictate where it lives:

### 1. Domain Specificity (The Co-location Principle)
* **Feature-Local (`src/features/<feature-name>/`)**:
  If a file relies on or handles domain concepts specific to one area (e.g. chat messages, robot pose/telemetry, or landing marketing sections), it **must** remain inside that feature.
* **Shared (`src/shared/`)**:
  If a piece of code is completely domain-agnostic (it does not know or care whether the app is an AI assistant, robot dashboard, or ecommerce store—e.g. `ThemeSelector`, `Header`, `Button`, `useLocation`, `formatDate`), it belongs in `shared/`.

### 2. The Rule of Three & Premature Abstraction
* **Never preemptively extract to `shared/`**.
* A component or utility is only promoted to `shared/` if **at least 2–3 distinct features** genuinely need it, and its interface can be decoupled from domain logic.

### 3. Unidirectional Dependency Rule
The import graph flows strictly in one direction:

```text
App / Root
   │
   ▼
features/*  ────────►  can import from  ────────►  shared/*
   │                                                     │
   │                                                     └── NEVER imports from features/
   └── NEVER cross-imports internal files of peer features!
```

1. **Features can import from `shared/`**.
2. **`shared/` must NEVER import from any `features/`**.
3. **Features should not reach into other features' internals**. If Feature A needs a capability from Feature B, Feature B must explicitly export it through its public `index.ts` barrel, or the coordination should happen at the root (`App.tsx`).

---

## 3. How to Add a New Feature

To add a new feature (e.g. `settings` or `analytics`):

1. Create a directory: `src/features/<feature-name>/`
2. Structure the internal folders as needed:
   * `components/` (UI elements specific to this feature)
   * `hooks/` (Custom hooks specific to this feature)
   * `services/` or `api/` (Data fetching & business logic)
   * `types/` (TypeScript definitions)
3. Create an `index.ts` barrel that exports only the public surface (typically the main view component).
4. Register the route or render entry point in `src/App.tsx`.
