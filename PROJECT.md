# MoKa AI Assistant & Tool-Routing Benchmark Ecosystem
## Complete Engineering Specification, Architecture, and Thesis Context

> **Project Reference Document**  
> **Author & Developer:** Mohammad Kashefirad  
> **Academic Supervisor:** Herr Christoph Vogl  
> **Academic Context:** Bachelor's Thesis (Winter 2026 / Spring 2027)  
> **Thesis Title:** *Routing-Strukturen für große Tool-Mengen in einem LLM-basierten Desktop-Roboter-Assistenten: Ein Vergleich von Genauigkeit, Token-Verbrauch und Latenz*  
> **Codebase Root:** [`c:/Users/mkrad/PycharmProjects/moka_ai_assistant`](file:///c:/Users/mkrad/PycharmProjects/moka_ai_assistant)  
> **Last Updated:** October 2026 (SRS Version 2.0 / Post-WP2 Baseline)

---

## 1. Executive Summary & Academic Purpose

### 1.1 The Core Scientific Problem
When building embodied conversational agents, user commands span physical hardware kinematics (e.g., motor emergency stops, rover navigation), workstation automations (e.g., workspace IDE setups, volume controls), system utilities (e.g., clock/date checks), and deep cognitive sub-agents (e.g., calendar scheduling, web search, code execution).

In conventional LLM architectures, all available tool descriptions are dumped into a single monolithic prompt, forcing the LLM to select an action on every turn. As the tool registry scales from 15 to 30, 50, and 100+ tools:
1. **Accuracy Degrades ("Lost in the Middle"):** Small and medium models experience attention dilution, confusing semantically adjacent tools or choosing non-existent tools (hallucination).
2. **Latency Explodes:** Prompt pre-fill latency for 100 tools (5,000+ tokens) surges to 2,000–8,000 ms on local hardware—unacceptable for safety-critical physical robot reflexes.
3. **Token Inefficiency:** Passing 100 schema definitions on every turn exhausts context windows and burns memory/compute.

### 1.2 Central Research Questions & Hypotheses
* **Main Research Question:** How do different routing structures for tool selection (flat monolithic LLM, embedding-based router, and two-tier hybrid routing) compare in terms of Top-1 accuracy, token consumption, and latency percentiles (P50, P90, P95) when the tool registry scales from ~20 to 100 tools?
* **Sub-Question 1 (FF1):** How severely does a flat LLM router degrade as tool counts scale?  
  *(Hypothesis H1: Accuracy and token efficiency collapse sharply once tool counts exceed 30–50 tools).*
* **Sub-Question 2 (FF2):** Can a two-layer hybrid router dramatically slash token usage and latency without sacrificing accuracy?  
  *(Hypothesis H2: Input tokens drop to $O(k)$ constant complexity, latency for physical commands drops to $<10$ ms, and routing accuracy remains $\ge$ monolithic LLM).*
* **Sub-Question 3 (FF3):** Where are the failure boundaries of semantic retrieval when tools are highly confusable?  
  *(Hypothesis H3: Pure vector retrieval fails on recall when tools share high lexical/semantic overlap unless paired with cross-attention classification).*

### 1.3 Dual-Subsystem Scope
The repository encapsulates two tightly integrated subsystems that run **both on physical Anki Cozmo hardware and 100% hardware-free in simulation**:
1. **Desktop AI Assistant (MoKa Core):** A local-first, multi-modal conversational companion featuring Silero VAD speech detection, Whisper speech-to-text, Kokoro-ONNX neural voice synthesis, LangGraph cognitive sub-agents, dual-layer PostgreSQL memory, DINOv3 visual memory, and Bidirectional A* path planning.
2. **Systematic Tool-Routing Benchmark & Evaluation Suite:** An automated testing harness integrated with LangSmith evaluating router architectures across scaled tool registries (20 real $\rightarrow$ 30, 50, 100 synthetic confusable tools).

---

## 2. High-Level System Architecture

```
                          USER INTERACTION
                ┌──────────────────────────────────┐
                │ Spoken Audio (Silero VAD/Whisper)│
                │ Web UI (/chat, /cozmo, REST, WS) │
                └────────────────┬─────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   UNIFIED BRAIN ROUTING PIPELINE                       │
│                   ([backend/core/routing/brain.py])                     │
├────────────────────────────────────────────────────────────────────────┤
│ TIER 1: Deterministic Semantic Reflexes (~5 ms)                        │
│ Engine: FastEmbed (bge-small-en-v1.5) + SemanticRouter                 │
│ Action Registry: 7 Physical Kinematic Actions + Clock/Date             │
│   ├── Match (Score > 0.80) ──► Execute Motor / Instant Reflex Reply    │
│   └── Miss / Low Confidence                                            │
│                                │                                       │
│                                ▼                                       │
│ TIER 2: Filtered Cognitive Decision Layer                              │
│ 1. Vector Gating: FAISS Tool Index retrieves Top-k candidates (k=3..5) │
│ 2. Decision Classifiers:                                               │
│    ├── Variant A: Monolithic Qwen2.5:3b (temp=0.0) [Baseline]          │
│    ├── Variant B: Top-k FAISS RAG + Qwen2.5:3b [2-Layer LLM]           │
│    └── Variant C: Top-k FAISS RAG + LAYA Decision Model [Production]   │
│                                │                                       │
│                ┌───────────────┴───────────────┐                       │
│                ▼                               ▼                       │
│        Target Tool Node                chat_node (Fallback)            │
│  (Calendar, Weather, Setups, etc.)    (Small talk, Memory Recall)      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The Tool-Routing Benchmark & Empirical Findings (WP2)

### 3.1 The 6 Benchmarked Router Paradigms
In Work Package 2 (WP2), 6 router architectures were evaluated against a 48-case curated benchmark in LangSmith project `WP2`:

| Paradigm ID | Architecture | Layer 1 Reflexes | Candidate Filtering | Decision Engine | Output Tokens |
|---|---|---|---|---|---|
| `WP2-Baseline-LLM` | Monolithic LLM | None | None (All 15 tools in prompt) | Local Ollama `qwen2.5:3b` | Heavy |
| `WP2-Two-Layer-LLM` | 2-Layer LLM | FastEmbed | FAISS Top-3 Tool RAG | Local Ollama `qwen2.5:3b` | Low |
| `WP2-Single-Layer-Laya` | Monolithic LAYA | None | None (All 15 tools as criteria) | `laya-typed-decisions` (135M) | **0** |
| `WP2-Two-Layer-Laya` | 2-Layer Monolithic LAYA | FastEmbed | None (All 15 tools to LAYA) | `laya-typed-decisions` (135M) | **0** |
| `WP2-Single-Layer-Laya-TopK` | Single-Layer Top-K LAYA | None | FAISS Top-3 Tool RAG | `laya-typed-decisions` (135M) | **0** |
| `WP2-Two-Layer-Laya-TopK` | **2-Layer Top-K LAYA (Winner)** | **FastEmbed** | **FAISS Top-3 Tool RAG** | **`laya-typed-decisions` (135M)** | **0** |

### 3.2 Empirical Results (LangSmith 48-Case Benchmark)

| Router Paradigm | Accuracy | P50 (Median) Latency | Mean Latency | P90 Latency | Generative Output Tokens |
|---|:---:|:---:|:---:|:---:|:---:|
| **`WP2-Baseline-LLM`** | 87.5% (42/48) | 1,142.9 ms | 1,455.6 ms | 3,107.9 ms | Generative Autoregressive |
| **`WP2-Two-Layer-LLM`** | 95.8% (46/48) | 6.5 ms | 241.6 ms | 866.8 ms | Autoregressive (Top-3 only) |
| **`WP2-Single-Layer-Laya`** | 60.4% (29/48) | 1,051.4 ms | 1,054.1 ms | 1,069.3 ms | **0** (Classification only) |
| **`WP2-Two-Layer-Laya`** | 91.7% (44/48) | 6.3 ms | 316.9 ms | 1,077.7 ms | **0** (Classification only) |
| **`WP2-Single-Layer-Laya-TopK`** | 83.3% (40/48) | 784.6 ms | 796.7 ms | 958.7 ms | **0** (Classification only) |
| **`WP2-Two-Layer-Laya-TopK`** | **95.8% (46/48)** | **5.5 ms** | **205.3 ms** | **746.0 ms** | **0 (Zero Output Tokens)** |

### 3.3 Critical Architectural Insights
1. **Monolithic LAYA Fails at Scale (Softmax Dilution):** When passed 16 choices at once, cross-encoder score distributions flatten, dropping accuracy to 60.4%.
2. **FAISS Gating Guarantees Constant Complexity ($O(k)$):** By pre-filtering to Top-3 candidates + `"none"`, LAYA only evaluates 4 typed choices. Softmax entropy remains near zero, restoring 95.8% accuracy.
3. **Sub-6ms Physical Reflexes:** FastEmbed absorbs 100% of physical movement commands in 5.5 ms, bypassing the LLM completely.
4. **Why Fine-Tuning LAYA is an Anti-Pattern:** `convaiinnovations/laya-typed-decisions` is a pre-trained zero-shot cross-encoder. Fine-tuning on small datasets triggers catastrophic forgetting. Semantic clarity in tool descriptions produces superior zero-shot results.

---

## 4. Scaling Methodology for the Bachelor's Thesis ($20 \rightarrow 100$ Tools)

### 4.1 Dataset & Splits
* **Query Set:** 150–300 curated queries covering:
  - Clear intent for specific tools
  - Highly confusable tool pairs (cosine similarity $> 0.80$)
  - Queries with no relevant tool (must route to `"none"`)
  - Multi-turn conversational small talk
* **Split Ratio:** 30% Development Set (parameter tuning, prompt engineering) and 70% Holdout Test Set (locked for final thesis evaluation).

### 4.2 Scaled Registries ($N = 20, 30, 50, 100$)
* **Real Tools (~20):** Physical robot kinematics, Google Calendar, Weather, Web Search, Code Executor, Todoist, Workstation Setups, System Clock/Date.
* **Synthetic Tool Generation (Up to 100):** Generated into thematic clusters (Smart Home, Multimedia, Cloud Ops, Data QA) containing deliberate confusable pairs (e.g., `spotify_play_playlist` vs `spotify_resume_track`, `philips_hue_brightness` vs `desk_lamp_dim`). Synthetic tools are mock handlers dispatched deterministically.

### 4.3 Degradation Dynamics Across Architectures
* **Monolithic LLM ($O(N)$ tokens):** Degrades sharply beyond 30 tools due to prompt bloat (5,000+ tokens) and 4–8 second local pre-fill latency.
* **Monolithic LAYA ($O(N)$ cross-attention):** Collapses to $<30\%$ accuracy due to softmax probability dilution.
* **Two-Layer Top-K LAYA ($O(k)$ constant):** Vector search across 100 tools in FAISS takes $<0.05$ ms. LAYA always sees $k=5$ choices. Latency and token consumption remain constant.

---

## 5. Subsystem Deep Dive & Technical Stack

### 5.1 Technology Stack Overview
* **Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2
* **Orchestration & Cognitive Brain:** LangGraph (`StateGraph`), LangChain Core, LangSmith
* **Memory & Storage:** PostgreSQL 15, `psycopg` (v3), `langgraph-checkpoint-postgres`, FAISS-CPU
* **AI & Embedding Models:**
  - FastEmbed (`BAAI/bge-small-en-v1.5`)
  - LAYA (`convaiinnovations/laya-typed-decisions`, 135M cross-encoder)
  - Ollama (`qwen2.5:3b`, `gemma4:e2b`, `qwen3.5:4b`)
  - Cloud Fallback: Azure OpenAI (`Phi-4-mini-instruct`)
* **Speech & Audio:**
  - Silero VAD (250ms threshold, voice activity detection)
  - `faster-whisper` (`small.en`, int8 CPU)
  - `kokoro-onnx` (v1.0 neural TTS, 24kHz audio, 20ms chunks)
* **Robotics & Computer Vision:**
  - `pycozmo` (hardware protocol client)
  - OpenCV, NumPy, Pillow, Torch (ViT-S DINOv3 features)
* **Frontend Web Application:**
  - React 19, TypeScript, Vite, Tailwind CSS v4
  - Three.js, `@react-three/fiber`, `@react-three/drei`
  - BorderBeam, Liquid Gooey, ThreeUI Fragment Shaders

---

### 5.2 Cognitive Layer & Dual Memory Architecture

```
LangGraph Execution Flow (cozmo_graph):
START ──► memory_retrieval_node ──► tool_retrieval_node ──► route_query
                                                                 │
                                          ┌──────────────────────┴──────────────────────┐
                                          ▼ (route in TOOL_REGISTRY)                    ▼ (route == 'none')
                                  execute_tool_node                                 chat_node
                                          │                                             │
                                          └──────────────────────┬──────────────────────┘
                                                                 ▼
                                                    summarize_conversation_node
                                                                 │
                                                                 ▼
                                                     memory_extraction_node ──► END
```

#### Dual-Layer Memory Engine:
1. **Short-Term Conversational Memory:**
   - Thread-level persistence via `PostgresSaver` in PostgreSQL table `checkpoints`.
   - Automatic Summarization (`summarize_conversation_node`): When conversation exceeds 6 messages, older turns are progressively condensed into a rolling summary and purged from active checkpoint history, preventing context bloat.
2. **Long-Term Biographical Memory:**
   - Asynchronous background thread (`memory_extraction_node`) filters recent user utterances for permanent traits (identity, occupation, persistent preferences).
   - Strict Guardrails: Discards temporary conditions (weather, clock time, calendar appointments) and hallucinations.
   - Vector Retrieval (`memory_retrieval_node`): Retrieves top-3 biographical facts via cosine similarity or retrieves all user facts on meta-queries (*"What do you know about me?"*).

---

### 5.3 Hardware, Safety, & Computer Vision Subsystem

#### 1. Reflex Safety Guard (`core/hardware/safety.py`)
Safety is completely decoupled from host AI lag. A dedicated thread intercepts PyCozmo motor commands:
* **Cliff Detection:** Instant stop + evasive backup on cliff sensor trip.
* **Pickup Detection:** Disables tracks when robot is lifted from the desk.
* **Shock Deceleration:** Detects physical collisions via accelerometer spike ($<-2200\text{ mm/s}^2$).
* **Camera Visual Stall Detection:** Compares sliding window camera frames during active drive commands to detect obstacles missed by wheels.

#### 2. DINOv3 & REMIND Spatial Visual Memory (`autonomous_cozmo/vision/`)
* **Feature Extraction:** 384-dimensional patch embeddings extracted via Vision Transformer.
* **Temporal Debouncer:** Debounces visual clusters across $N=3$ consecutive frames to eliminate lighting glints and transient sensor noise.
* **Visual Anchors & Landmark SLAM:** Corrects internal track odometry drift against persistent visual anchors (monitor stand, charger).
* **Click-to-Segment & Teach:** Users can click camera frames in the web UI to isolate objects, compute SVD Master PCA heatmaps, and label items in real time.

#### 3. Motion Planning & Autonomous Docking (`autonomous_cozmo/motion/`)
* **Bidirectional A\* Search (`bidirectional_astar.py`):** Simultaneous forward search from Cozmo's pose and backward search from the dock approach point, reducing state space to $O(b^{d/2})$.
* **50mm Safety Clearance:** Every obstacle (Cozmo cubes) is inflated with a strict 50mm buffer + robot footprint (35mm).
* **Kinematic String-Pulling:** Decimates jagged grid steps into smooth continuous waypoints.
* **Visual Servoing:** Switches from coarse A* waypoint following to millimeter-accurate backward visual servoing onto charger pins.

---

### 5.4 Audio & Speech Pipeline (`actions/physical/`)
* **VoiceListener (`listen.py`):** Continuous audio capture via `sounddevice`. Employs Silero VAD to detect user speech start/stop (250ms silence cutoff). Transcribes speech locally via `faster-whisper` (`int8` CPU). Supports conversational barge-in.
* **VoiceSpeaker (`speak.py`):** High-fidelity local speech synthesis using `kokoro-onnx` (`kokoro-v1.0.onnx`, 24kHz). Streams audio in non-blocking 20ms chunks. Immediately flushes audio queues upon user interruption.
* **VoiceBridge (`core/modes/voice_bridge.py`):** Manages WebSocket state broadcast (`IDLE`, `LISTENING`, `PROCESSING`, `SPEAKING`) to the React frontend.

---

### 5.5 Frontend User Experience & Design System (`frontend/`)

Designed under the creative north star **"Cybernetic Physical Embodiment & Frosted Obsidian Glass"**:
* **Multi-Theme Matrix (`DESIGN.md`):**
  - `default`: Minimal Monochrome Obsidian with white highlights.
  - `black-ice`: Glacial Cyan refraction with ThreeUI Constellation background.
  - `royal`: 24k Gold veins with Liquid Kintsugi shaders.
  - `it`: ASCII Cyber Matrix data network with electric green telemetry.
* **Key Routes & Features:**
  - `/chat`: Streaming token interface, live Cognitive Telemetry Card (displaying router stage, routing latency, retrieved candidate tools, memory hits), collapsible session drawer, local authentication (`X-Moka-Token`).
  - `/cozmo`: Interactive robotics mission control featuring 20Hz telemetry WebSocket, live MJPEG video stream with DINO heatmap overlay, 2D Semantic Grid Map & 3D WebGL World Map (`Cozmo3DWorldMap.tsx`), interactive draggable obstacles, click-to-teach visual segmentation, and simulated autonomous docking.

---

## 6. Comprehensive Repository File & Directory Map

```
c:\Users\mkrad\PycharmProjects\moka_ai_assistant\
├── 3DModel/                               # 3D assets for Cozmo and Charger visualization
│   └── Models/ (OBJ, USDZ, charger)
├── backend/
│   ├── actions/                           # Executable capabilities
│   │   ├── digital/
│   │   │   ├── langchain/                 # Weather agent & tooling
│   │   │   ├── langgraph/                 # Google Calendar & Todoist agents
│   │   │   ├── setups.py                  # Workstation environment automations
│   │   │   ├── system_tools.py            # Local time, date, utilities
│   │   │   └── n8n_agents.py              # Web search & webhook bridges
│   │   └── physical/
│   │       ├── movement.py                # Chassis kinematics & Layer 2 tool fallbacks
│   │       ├── charger.py                 # Docking actions & camera registration
│   │       ├── face.py                    # OLED 128x64 face graphics & weather display
│   │       ├── listen.py                  # Silero VAD + faster-whisper speech recognition
│   │       └── speak.py                   # Kokoro-ONNX studio neural TTS
│   ├── autonomous_cozmo/                  # Embodied autonomy & computer vision
│   │   ├── behavior/                      # Behavior Tree, battery monitor, idle engine
│   │   ├── motion/                        # Bidirectional A*, primitives, visual servoing
│   │   └── vision/                        # DINOv3 extractor, REMIND engine, heatmaps, SLAM
│   ├── core/
│   │   ├── hardware/                      # PyCozmo manager, connection, ReflexSafetyGuard
│   │   ├── modes/                         # Execution entry points
│   │   │   ├── brain.py                   # Unified Brain (Tier 1 + Tier 2 router dispatch)
│   │   │   ├── web_api.py                 # FastAPI backend (/api/chat, /api/history, tokens)
│   │   │   ├── cozmo_api.py               # Autonomous Cozmo hub (/api/cozmo, /ws/cozmo)
│   │   │   ├── voice_bridge.py            # WebSocket voice state & telemetry bridge
│   │   │   └── terminal_mode.py           # CLI interactive terminal chat
│   │   └── routing/
│   │       ├── encoder.py                 # FastEmbed singleton encoder
│   │       ├── llm_factory.py             # Local (Ollama) vs Cloud (Azure) dynamic toggle
│   │       ├── layer1/                    # FastEmbed semantic reflexes (sub-10ms)
│   │       ├── layer2/                    # LangGraph StateGraph, Tool RAG, LAYA classifier
│   │       └── baseline/                  # Monolithic LLM baseline router
│   ├── schemas/                           # Pydantic models, PostgreSQL chat history & memory
│   └── test/
│       ├── digital/routers/               # THE BENCHMARK HARNESS (Thesis WP2)
│       │   ├── tools/                     # Partitioned domain tool namespaces
│       │   │   ├── robot.py               # robot.* (physical kinematics, docking, sweep)
│       │   │   ├── desktop.py             # desktop.* (workstation setups, system clock/date)
│       │   │   ├── cognitive.py           # cognitive.* (search, calendar, weather, code, todoist)
│       │   │   ├── media.py               # media.* (Spotify, YouTube, media player)
│       │   │   ├── smart_home.py          # smart_home.* (IoT & home automations)
│       │   │   └── tools_config.py        # Master aggregator & RAG registry compiler
│       │   ├── models/                    # Modular router model implementations
│       │   │   ├── llm/                   # LLM router variants (baseline.py, two_layer.py)
│       │   │   └── laya/                  # LAYA router variants (single/two_layer, topk)
│       │   ├── benchmark_dataset.py       # 48 curated evaluation cases
│       │   ├── harness.py                 # LangSmith evaluation executor & metric calculator
│       │   └── compare_routers.py         # Batch runner generating 6-way comparison matrix
│       └── physical/                      # Hardware & simulation validation suites
├── frontend/
│   ├── dev-server.ts                      # Unified launcher (starts backend + frontend)
│   ├── src/
│   │   ├── features/
│   │   │   ├── chat/                      # Chat UI, SSE streaming, cognitive telemetry
│   │   │   └── cozmo/                     # Telemetry dashboard, 2D/3D map, visual teaching
│   │   └── shared/                        # Multi-theme CSS, ThreeUI shaders, backgrounds
├── docs/
│   ├── Expose_Bachelorarbeit.docx         # Official Bachelor's Thesis Exposé
│   └── Moka_AI_Assistant_SRS.docx         # Software Requirements Specification (SRS v2.0)
├── main.py                                # Master Python entrypoint (Terminal vs Robot mode)
├── moka_web_launch.bat                    # One-click Windows launcher for Web UI
├── docker-compose.yml                     # Docker environment (PostgreSQL, Backend, Frontend)
└── WP2_roadmap.md                         # Benchmark results & 100-tool scaling roadmap
```

---

## 7. Developer Operation & Commands Cheat Sheet

### 7.1 Running the Application
* **Web Mode (Backend + Frontend, Recommended):**
  ```bash
  # Option 1: Double-click moka_web_launch.bat
  # Option 2: From frontend directory
  cd frontend
  npm run dev
  # Access UI at http://localhost:5173/chat or /cozmo
  ```
* **Terminal Chat (Hardware-Free CLI):**
  ```bash
  python main.py
  # Select Option 1 (Terminal Mode)
  ```
* **Robot Hardware Server:**
  ```bash
  python main.py
  # Select Option 2 (Cozmo Mode on localhost:8000)
  ```
* **Docker Multi-Container Deployment:**
  ```bash
  docker compose up -d
  # Runs PostgreSQL, FastAPI Backend, React Frontend, and Hardware Driver
  ```

### 7.2 Running the Tool-Routing Benchmark
```bash
# Run all 6 router variants against the LangSmith WP2 benchmark:
python backend/test/digital/routers/compare_routers.py

# Run individual router experiments:
python backend/test/digital/routers/models/laya/two_layer_topk.py
python backend/test/digital/routers/models/llm/baseline.py
```

### 7.3 Running Autonomous Cozmo Tests
```bash
# Test Bidirectional A* path planning:
python backend/test/digital/test_bidirectional_astar.py

# Test DINOv3 visual heatmap & webcam extraction:
python backend/test/physical/webcam_dinov3_VS_dinov2.py

# Test autonomous docking simulation:
python backend/test/physical/test_phase5_autonomous_docking.py
```

---

## 8. Invariants & Guidelines for Pair Programming

Whenever we work on this codebase, adhere strictly to these core architectural rules:

1. **Hardware-Free Executability:** All Must-Have and Should-Have features must run cleanly on a laptop without physical robot hardware via `--dry-run` and `--source webcam`.
2. **Never Bypass Layer 1 for Physical Safety:** Physical robot emergency stops, cliff reflexes, and high-frequency movement commands must resolve in Layer 1 FastEmbed reflexes or hardware guards, never blocked behind LLM inference.
3. **Keep Context Windows $O(k)$ Constant:** Do not pass the entire tool registry into generative LLM prompts. Always route through FAISS candidate retrieval ($k=3$ or $k=5$) before passing choices to LAYA or Ollama.
4. **Preserve Dual Memory Boundaries:** Temporary details (weather, clock time, meetings) belong in short-term checkpoints; only permanent biographical facts belong in long-term vector storage.
5. **Zero-Shot Prompt/Schema Engineering Over LAYA Fine-Tuning:** Improve LAYA decision accuracy by refining typed choice criteria descriptions, not by fine-tuning the base weights.
6. **Token Header Validation:** All mutating web endpoints must validate `X-Moka-Token` with localhost automatic development bypass.
7. **Design Aesthetics:** Maintain the cybernetic frosted glass aesthetics, high-contrast dark surfaces, and dynamic theme responsiveness across all frontend components.
