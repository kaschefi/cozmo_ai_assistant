# Dimensional Drawing Motion Video Workflow

A comprehensive engineering guide for converting any 2D dimensional drawing sheet created with the `dimensional-drawing` skill into a 60 FPS Apple-style technical motion film (`.mp4`) and an interactive browser player (`.html`).

---

## 1. Architecture & Core Concepts

A dimensional motion drawing mimics an Apple-style technical film: a precision technical pen traces components on white paper while a virtual camera glides over the sheet, pulls back to show the dual-eye/plan layout, lifts exploded layers into 3D axonometric space, and pulls back to reveal the complete engineering spec sheet with callouts and tables.

```
+-----------------------------------------------------------------------------------------+
|                                    CHOREOGRAPHY                                         |
|                                                                                         |
|  Beat 1 (0.0s - 2.2s)    Close-up aperture / header linework (camera z = 4.4x)          |
|  Beat 2 (2.2s - 4.2s)    Log-zoom pull back to plan view (z: 4.4x -> 1.7x)              |
|  Beat 3 (4.2s - 7.2s)    Axonometric layer stack lift off plan (z: 1.5x)                |
|  Beat 4 (7.2s - 9.2s)    Full-sheet resolve: borders, notes, tables, details (z = 1.0x) |
|  Beat 5 (9.2s - 11.0s)   Subtle push / hold drift (z: 0.998 -> 0.988)                   |
+-----------------------------------------------------------------------------------------+
```

### Pure Function of Time
The motion scene script (`<name>-scene.js`) **must be a pure function of time**:
```javascript
kit.scene('drawing', {
  init(kit) {
    // 1. Setup styles, camera wrapper (.dw-cam), and root SVG (1900 x 1060)
    // 2. Register drawing elements via at(start, stagger, duration) and mk()
    // 3. Register lifting layers via mg(z, start)
  },
  render(t) {
    // Set every visual property (transform, opacity, strokeDashoffset)
    // strictly from t alone, never from previous frames!
  }
});
```
This purity allows headless renderers (Playwright) to jump to any frame arbitrarily with deterministic rendering.

---

## 2. Prerequisites & Setup

The recommended headless rendering pipeline uses **Playwright** (Chromium) and **ffmpeg**:
- **Node.js**: v18+ (verified on Node v22)
- **ffmpeg**: installed and accessible on system `PATH` (verified on v8.1)
- **Adapter Location**: `.agents/skills/dimensional-drawing-motion/adapters/headless/`

### One-Time Environment Initialization
From the repository root:
```bash
# Navigate to the headless adapter directory
cd .agents/skills/dimensional-drawing-motion/adapters/headless

# Install Playwright and its bundled Chromium headless shell
npm install
```

---

## 3. Step-by-Step Production Guide

### Step 1: Extract Geometry from Static Drawing
Given a static drawing (`card-sheet.html`, `chat-sheet.html`, or `particles-sheet.html`):
1. Note the canvas logical dimensions (e.g. `1200 x 600`).
2. Choose a scaling factor `k` (typically `0.55` - `0.65`) and plan origin `PX, PY` so the plan fits neatly in the top-center half of the `1900 x 1060` motion stage.
3. Compute coordinates for features:
   $$\text{Sheet } X = PX + (\text{Logical } X) \cdot k$$
   $$\text{Sheet } Y = PY + (\text{Logical } Y) \cdot k$$

### Step 2: Formulate Camera Path (`DW_CAM`)
**Crucial Requirement**: The camera targets the **exact sheet coordinates** of elements, not logical units!
```javascript
const DW_CAM = [
  // Beat 1: Close-up on primary feature (e.g., left eye / top-left corner)
  { t: 0,   cx: LeftFeatureX, cy: LeftFeatureY, z: 4.4 },
  { t: 2.2, cx: LeftFeatureX + 6, cy: LeftFeatureY + 2, z: 4.2 },

  // Beat 2: Dual plan view center
  { t: 4.2, cx: PlanCenterX, cy: PlanCenterY, z: 1.75 },
  { t: 5.3, cx: PlanCenterX + 4, cy: PlanCenterY + 2, z: 1.71 },

  // Beat 3: Exploded view center (typically bottom-left)
  { t: 7.2, cx: ExplodedCenterX, cy: ExplodedCenterY, z: 1.55 },
  { t: 7.8, cx: ExplodedCenterX + 4, cy: ExplodedCenterY + 2, z: 1.52 },

  // Beat 4 & 5: Full sheet center (viewBox 1900x1060 -> 950, 530)
  { t: 9.2, cx: 950, cy: 530, z: 0.998 },
  { t: 13,  cx: 950, cy: 530, z: 0.988 }
];
```

Camera interpolation uses **log-zoom** to ensure steady visual velocity:
```javascript
const z = Math.exp(lerp(Math.log(c0.z), Math.log(c1.z), p));
const cx = lerp(c0.cx, c1.cx, p);
const cy = lerp(c0.cy, c1.cy, p);
this.cam.transform = `translate(${960 - cx * z}px, ${540 - cy * z}px) scale(${z})`;
```

### Step 3: Register Strokes and Morphs
Use `at(start, stagger, duration)`:
- Solid paths (`k = 'd'`): Normalized with `pathLength="1"`, animated using `strokeDashoffset: 1 - e` (where `e = eio(v)`). Fills fade in during the last 45% (`v: 0.55 -> 1.0`).
- Text & dashed lines (`k = 'f'`): Animated with opacity fade (`eo(v)`).
- Axonometric lifting layers:
  ```javascript
  const sc = 0.40, TX = 270, TY = 620, gap = 44;
  const ia = 0.94 * sc, ib = 0.17 * sc, ic = -0.34 * sc, id = 0.47 * sc;
  this.iso = [ia, ib, ic, id, TX, TY];
  this.flat = [k, 0, 0, k, PX, PY];
  ```

### Step 4: Test Still Frames Before Full Encode
Never encode 660 frames blindly! Test key still frames first:
```bash
cd .agents/skills/dimensional-drawing-motion/adapters/headless

# Test Beat 1 opening (close-up drawing underway)
node render.mjs --scene ../../../../particles-scene.js --css ../../templates/base.css --still 0.5 --out ../../../../scratch/test_0.5s.png

# Test Beat 2 plan view
node render.mjs --scene ../../../../particles-scene.js --css ../../templates/base.css --still 3.5 --out ../../../../scratch/test_3.5s.png

# Test Beat 3 exploded view
node render.mjs --scene ../../../../particles-scene.js --css ../../templates/base.css --still 6.6 --out ../../../../scratch/test_6.6s.png

# Test Beat 5 full resolved sheet
node render.mjs --scene ../../../../particles-scene.js --css ../../templates/base.css --still 10.5 --out ../../../../scratch/test_10.5s.png
```
Inspect each output PNG. Ensure:
- Camera is accurately centered on the active elements.
- Notes text does not collide with the plan view.
- Exploded view leader text does not clip the left border ($X \ge 20$).
- Detail titles and bottom borders do not clip the bottom ($Y \le 1040$).

### Step 5: Encode Final 60 FPS MP4 Video
Once the stills look perfect, encode the full motion video:
```bash
cd .agents/skills/dimensional-drawing-motion/adapters/headless

node render.mjs \
  --scene ../../../../particles-scene.js \
  --css   ../../templates/base.css \
  --out   ../../../../particles-motion.mp4 \
  --fps   60 \
  --duration 11 \
  --crf   16
```
- Output: 1920x1080 @ 60 FPS H.264 MP4 with faststart flags.
- Typical file size: 5 MB to 7 MB for an active drawing (vs ~37 KB for an empty white screen).

### Step 6: Update Standalone HTML Player
Copy the tested scene into `<name>-motion.html`. This allows client-side playback directly in any modern browser without needing Node or ffmpeg:
- Responsive stage auto-scaling: `scale = min(vw / 1920, vh / 1080)`.
- Player controls: Play/Pause, Reset, Scrubber range input, Beat badge, Speed toggle (0.5x, 1.0x, 1.5x, 2.0x).
- Keyboard shortcuts: <kbd>Space</kbd> (play/pause), <kbd>←</kbd> / <kbd>→</kbd> (step 0.1s), <kbd>R</kbd> (reset to 0.0s).

---

## 4. Key Troubleshooting & Lessons Learned

| Issue | Root Cause | Solution |
|---|---|---|
| **Blank white video (~37 KB)** | Camera `DW_CAM` keyframe `(cx, cy)` pointed at empty canvas margin at 4.4× zoom. | Calculate exact centroid: $X = PX + \text{feat}_x \cdot k$, $Y = PY + \text{feat}_y \cdot k$. Check still frame at $t=0.5$s. |
| **Blank white player on load** | Elements had `at()` windows starting at $t > 0$, rendering with `opacity: 0` at $t=0$. | Start first group with negative offset (e.g. `at(-0.8, 0, 2.2)`), so initial strokes are already 35% visible on initial paint. |
| **`Identifier 'seg' already declared`** | Outer HTML declared helpers `seg, lerp`, while imported scene also destructured `const { seg } = kit;`. | Use standard template structure where `kit` provides helpers, and keep scene cleanly registered into `kit.scene()`. |
| **Notes overlapping Plan View** | Notes text string too long for left column ($X=50 \rightarrow X=520$). | Keep notes concise (<65 characters per line), or shift $PX$ rightward ($PX = 620$). |
| **Leader text clipping left border** | Leader text used `text-anchor: end` with leader endpoint at $X=140$. | Shift text origin to $X \ge 220$ or use `text-anchor: start` with sufficient margin. |
| **CDP loop out of sync** | Running custom `requestAnimationFrame` while headless screenshot captures ran. | Use the official `render.mjs` adapter; it calls pure `window.R(i / FPS)` deterministically per frame. |

---

## 5. File Registry for Reference

- Reference static sheet: [`particles-sheet.html`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/particles-sheet.html)
- Pure motion scene: [`particles-scene.js`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/particles-scene.js)
- Standalone interactive player: [`particles-motion.html`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/particles-motion.html)
- Final rendered video: [`particles-motion.mp4`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/particles-motion.mp4)
- Headless adapter renderer: [`.agents/skills/dimensional-drawing-motion/adapters/headless/render.mjs`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant/.agents/skills/dimensional-drawing-motion/adapters/headless/render.mjs)

