// src/data/mokaPagesData.ts
// Comprehensive, production-grade architectural specifications and data models for the MoKa AI Assistant portfolio book.

export interface MokaPageContent {
  pageNumber: string;
  pageLabel: string;
  title: string;
  subtitle: string;
  discipline?: string;
  thesis?: string;
  overview?: string;
  description?: string;     // Extended, comprehensive deep dive for the right-hand panel
  codeSnippet?: string;     // Production code excerpt with explanatory comments
  keyMetrics?: Array<{ label: string; value: string }>;
  highlights?: string[];
  image?: string;
  imageCaption?: string;
}

export const mokaPagesData: MokaPageContent[] = [
  // =========================================================================================
  // PAGE 01: GENESIS & SYSTEM OVERVIEW
  // =========================================================================================
  {
    pageNumber: "01",
    pageLabel: "GENESIS // DUAL-PLANE ARCHITECTURE",
    title: "Hybrid Dual-Plane Cognitive Architecture",
    subtitle: "Local-First Neural Inference & Embodied Cybernetic Control",
    discipline: "Distributed Systems Architecture & Edge Robotics",
    thesis: "Overcoming the Latency-Versatility Dilemma via Decoupled Spinal Reflexes and Graph-Orchestrated Local SLMs",
    overview:
      "MoKa is a local-first, embodied robotic AI assistant engineered on top of the Anki Cozmo hardware platform. It eliminates cloud dependencies by pairing an ultra-low-latency semantic reflex arc (~45ms P50) with an asynchronous, graph-compiled cognitive deliberator powered by Ollama Small Language Models (SLMs) and on-device neural synthesis.",
    description:
      "Embodied conversational agents face a fundamental architectural dichotomy: physical hardware demands instantaneous, deterministic reaction times (<50ms) to ensure stability and user responsiveness, whereas open-domain linguistic reasoning and dynamic tool execution traditionally impose massive computational latency (1,000ms - 3,000ms) and cloud API coupling.\n\n" +
      "MoKa resolves this latency-versatility dilemma through a dual-plane hybrid cognitive architecture:\n\n" +
      "1. The Spinal Reflex Plane (Tier 1): Implemented in pure on-device C++ and Python bindings via FastEmbed (BAAI/bge-small-en-v1.5 384D embeddings) and the semantic-router framework. Utterances matching physical actuation, safety stops, or local OS workstation setups are resolved in ~45ms without allocating a single LLM token.\n\n" +
      "2. The Cognitive Cortical Plane (Tier 2): Complex natural language queries, multi-step tool calls, and stateful memory reasoning route into a compiled LangGraph state machine. This plane runs entirely on local quantization substrates (Ollama qwen2.5:3b for routing/synthesis, ornith:9b for isolated code sandboxing, and Kokoro-v1.0 ONNX for zero-disk streaming TTS).\n\n" +
      "3. Hardware-Software Decoupling: The cognitive substrate interfaces with physical actuators via a 33Hz low-level PyCozmo packet loop, safeguarded by asynchronous monkey-patched motor interrupters that guarantee physical stability even during heavy GPU/CPU tensor loads.",
    keyMetrics: [
      { label: "Reflex P50 Latency", value: "~45 ms" },
      { label: "Cognitive P50 Latency", value: "~1.28 s" },
      { label: "Cloud API Footprint", value: "0 Calls (Core)" },
      { label: "Hardware Sync Loop", value: "33.3 Hz (30ms)" },
    ],
    highlights: [
      "Zero-cloud dependency: All embeddings, language generation, and speech synthesis execute locally on edge workstation hardware.",
      "Dual-plane decoupling guarantees 45ms physical reflex responses while preserving multi-step LangGraph reasoning capabilities.",
      "Ollama quantization (Q4_K_M) enables sub-2GB RAM footprints for the primary 3B router/chat deliberator.",
      "Integrated FastAPI REST gateway and terminal REPL expose identical high-level state representations to external consumers."
    ],
    codeSnippet:
`# High-Level System Initialization Pipeline (main.py / cozmo_mode.py)
import asyncio
from core.routing.layer1.semantic_layer import initialize_router, check_layer_1, execute_reflex
from core.routing.layer2.router import run_cozmo_agent
from actions.physical.speak import voice_speaker

async def process_user_utterance(user_input: str, thread_id: str = "cozmo_default_session") -> str:
    """
    Dual-Plane Hybrid Dispatch: Evaluates Tier 1 reflex arc before allocating
    computational cycles to the compiled LangGraph Tier 2 brain.
    """
    # 1. Tier 1: Sub-50ms embedding similarity reflex check (bypasses LLM)
    reflex_route = check_layer_1(user_input)
    if reflex_route:
        success, response_text = await execute_reflex(reflex_route)
        if success:
            return response_text

    # 2. Tier 2: Asynchronous LangGraph state machine invocation
    # Evaluates Tool RAG, PostgreSQL vector state, and local Ollama models
    return await asyncio.to_thread(run_cozmo_agent, user_input, thread_id)`
  },

  // =========================================================================================
  // PAGE 02: THE TWO-TIER ROUTER
  // =========================================================================================
  {
    pageNumber: "02",
    pageLabel: "ROUTING SUBSYSTEM // TWO-TIER HIERARCHY",
    title: "Two-Tier Sub-50ms Semantic Fallback & Tool RAG",
    subtitle: "Spinal Reflex Layer & FAISS-Indexed Tool Vector Space",
    discipline: "Information Retrieval & Directed Acyclic Graph (DAG) Routing",
    thesis: "Eliminating Tool Crowding and Prompt Confusion via Vector Subspace Filtering and Unified Node Execution",
    overview:
      "A hierarchical dispatch pipeline that marries zero-LLM semantic embeddings with an in-memory FAISS tool vector store. Layer 1 executes hardware actions in ~45ms; Layer 2 dynamically retrieves top-k tool schemas, slashing prompt tokens by 83% and boosting routing accuracy to 93.0%.",
    description:
      "Monolithic agent architectures suffer from prompt bloat: feeding 15+ tool definitions into a compact local SLM (such as qwen2.5:3b) dilutes attention heads, leading to severe tool hallucination, catastrophic routing latency (>1,300ms), and 59,000+ token context expenditures.\n\n" +
      "MoKa eliminates this failure mode using a Two-Tier Fallback Hierarchy:\n\n" +
      "• Tier 1 (Spinal Reflex Arc): Utilizes FastEmbed (384-dimensional dense vectors via ONNX Runtime) to compute maximum cosine similarity against pre-compiled phrase centroids. If the utterance exceeds a tuned threshold (0.80 - 0.85), execution dispatches synchronously in ~45ms, completely bypassing tokenizer overhead.\n\n" +
      "• Tier 2 (Dynamic Tool RAG & Graph Router): When Tier 1 yields no match, the query enters LangGraph's tool_retrieval_node. Here, an in-memory FAISS index computes L2 distance over registered tool docstrings, filtering out irrelevant schemas and pruning candidates to the top 2-3 tools (distance threshold d <= 1.15).\n\n" +
      "• Structured Supervisor & Unified Node: A zero-temperature LLM receives only the pruned candidates and generates a validated Pydantic RouteDecision. Instead of maintaining N discrete tool nodes with branching conditional edges, the graph routes into a single execute_tool_node that dispatches dynamically against a Python function registry.\n\n" +
      "In a 57-case LangSmith benchmark, this two-tier paradigm achieved 93.0% accuracy (vs 89.5% monolithic baseline), lowered P50 latency from 1,340ms to 45ms (~30x acceleration), and cut prompt token consumption from 59,200 to 10,150 tokens (-82.9%).",
    keyMetrics: [
      { label: "Routing Accuracy", value: "93.0% (53/57 Cases)" },
      { label: "P50 Latency (Tier 1)", value: "45 ms (30x Speedup)" },
      { label: "Token Reduction", value: "-82.9% (10.1k vs 59.2k)" },
      { label: "Candidate Fan-Out", value: "Top 2-3 of 20+ Tools" },
    ],
    highlights: [
      "Eliminates prompt crowding by dynamically injecting only FAISS-filtered tool definitions into the LLM context window.",
      "Spinal reflex arc guarantees instantaneous ~45ms reaction for safety stops, battery docking, and local workspace presets.",
      "Unified Tool Executor node scales linearly to 100+ tools without expanding graph compilation complexity or edge boilerplate.",
      "LangSmith verified: 93.0% routing accuracy with an 83% reduction in active context token consumption."
    ],
    codeSnippet:
`# Dynamic Tool Vector Indexing & Subspace Filtering (tool_vector_db.py)
from langchain_community.vectorstores import FAISS
from core.routing.encoder import get_shared_encoder

class ToolVectorRegistry:
    def __init__(self):
        self.embeddings = LangChainFastEmbedBridge()
        self.db = None
        self._tools_source = []

    def register_tool_schema(self, name: str, description: str):
        self._tools_source.append(Document(page_content=description, metadata={"tool_name": name}))

    def search_relevant_tools(self, user_query: str, k: int = 3, distance_threshold: float = 1.15) -> list[dict]:
        """Performs vector similarity search, pruning distant tool schemas (L2 distance <= 1.15)."""
        if not self.db:
            return []
        results = self.db.similarity_search_with_score(user_query, k=k)
        return [{"name": doc.metadata["tool_name"], "description": doc.page_content} 
                for doc, score in results if score <= distance_threshold]`
  },

  // =========================================================================================
  // PAGE 03: HARDWARE SAFETY GUARDS & AUTONOMOUS REFLEXES
  // =========================================================================================
  {
    pageNumber: "03",
    pageLabel: "HARDWARE CORE // REAL-TIME REFLEX SAFETY",
    title: "Deterministic Hardware Safety & Multi-Modal Evasion",
    subtitle: "33Hz Low-Level Packet Monkey-Patching & IMU/Vision Fusion",
    discipline: "Embedded Robotics & Real-Time Cyber-Physical Control",
    thesis: "Zero-Latency Hardware Interception via SDK Monkey-Patching, Deceleration Shock Filters, and Visual Stasis Sliding Windows",
    overview:
      "A multi-modal safety supervisor operating at PyCozmo's 33Hz packet frequency. It monkey-patches motor controls to intercept dangerous host commands, fusing cliff IR, IMU pitch tilt (>0.35 rad), impact shock deceleration, and OpenCV visual stasis (cv2.absdiff < 3.5) into autonomous evasion routines.",
    description:
      "In physical robotics, safety routines cannot rely on asynchronous application threads or model inference queues. A delayed halt of 200ms when approaching a desk ledge causes catastrophic physical drops.\n\n" +
      "MoKa's ReflexSafetyGuard operates directly within the PyCozmo SDK 33.3Hz packet thread context (~30ms cycle time) and enforces protection through three synchronized layers:\n\n" +
      "1. Sub-Packet Method Interception: On initialization, ReflexSafetyGuard monkey-patches the PyCozmo client's drive_wheels, drive_straight, turn_in_place, and stop_all_motors methods. When safety is tripped, all external movement invocations are discarded at zero latency unless originated by the isolated evasion thread.\n\n" +
      "2. Multi-Modal Collision & Tilt Detection:\n" +
      "   • IMU Pitch Tilt: Detects climbing or tipping when absolute pitch exceeds 0.35 rad (~20°).\n" +
      "   • Impact Deceleration Filter: Compensates raw X-axis accelerometer data for gravity tilt: a_true = a_x - g * sin(theta). Deceleration spikes relative to an adaptive resting baseline (delta <= -2,200 mm/s²) trigger instant impact detection.\n" +
      "   • Visual Motion Stasis Window: Downsamples 30fps camera feed to 80x60 grayscale with 5x5 Gaussian blur. If wheels are commanded forward for >1.0s but frame differencing yields mean(absdiff) < 3.5, visual stall is declared (preventing motor burnout against transparent or soft obstacles).\n" +
      "   • Pose Stasis: A 0.8s sliding window verifies linear displacement (hypot(dx, dy) < 10.0mm).\n\n" +
      "3. Autonomous Non-Blocking Evasion: When a tripwire fires, an isolated daemon worker thread halts motors, pulses reverse thrust (-80 mm/s for 1.2s), and executes a 180° rotation away from danger before clearing the lock.",
    keyMetrics: [
      { label: "Packet Loop Frequency", value: "33.3 Hz (30ms)" },
      { label: "Cliff Tripwire Latency", value: "< 12 ms" },
      { label: "Visual Stasis Matrix", value: "80x60 Gaussian (5x5)" },
      { label: "Evasive Maneuver", value: "1.2s Rev + 180° Spin" },
    ],
    highlights: [
      "Direct PyCozmo SDK monkey-patching prevents host commands from overriding emergency halt states.",
      "Gravity-compensated accelerometer filtering isolates true kinetic impacts from gravitational pitch shifts.",
      "OpenCV frame differencing detects wheel slip and invisible barriers without tactile bumper switches.",
      "Non-blocking threaded evasion autonomously reverses and rotates 180° away from table edges."
    ],
    codeSnippet:
`# Real-Time Deceleration & Visual Stasis Detection (backend/core/hardware/safety.py)
def _on_robot_state(self, cli, state=None):
    # Gravity-compensated linear acceleration impact shock
    pitch_rad = float(getattr(state, "pose_pitch_rad", 0.0))
    gravity_x = math.sin(pitch_rad) * 9800.0  # mm/s^2
    true_accel_x = float(getattr(state, "accel_x", 0.0)) - gravity_x
    accel_shock = true_accel_x - self.baseline_accel_x

    # Tripwire: Severe forward deceleration shock below resting baseline
    if self.is_forward_driving and accel_shock <= self.ACCEL_SHOCK_DELTA_THRESHOLD:
        self._trigger_evasive_reflex("BUMP_DETECTED")

def update_camera_frame(self, bgr_image) -> bool:
    """Evaluates 1.0s sliding window frame difference (cv2.absdiff) for visual stasis."""
    small = cv2.resize(bgr_image, (80, 60))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    diff = float(cv2.absdiff(blurred, self.visual_window_ref_frame).mean())
    if diff < self.STALL_DIFF_THRESHOLD and self.is_forward_driving:
        self._trigger_evasive_reflex("BUMP_DETECTED")`
  },

  // =========================================================================================
  // PAGE 04: DUAL-TIER MEMORY & ZERO-DISK VOICE PIPELINE
  // =========================================================================================
  {
    pageNumber: "04",
    pageLabel: "STATE & AUDIO // PERSISTENT MEMORY & STREAMING TTS",
    title: "Dual-Tier Memory Architecture & Zero-Disk Voice Substrate",
    subtitle: "PostgreSQL REAL[] Vector Store & 20ms Ring-Buffered Kokoro TTS",
    discipline: "State Management, Vector Mathematics & Audio Signal Processing",
    thesis: "Decoupling State Durability from Cloud Footprints via In-Engine Vector Math and Asynchronous Pipeline Streaming",
    overview:
      "A production state and speech engine combining LangGraph session checkpoints with a PostgreSQL native REAL[] biographical vector store (NumPy 0.82 cosine deduplication). Paired with Kokoro-ONNX zero-disk TTS streaming 20ms float32 PCM frames into PortAudio ring buffers.",
    description:
      "Personalized companionship requires lifelong biographical recall, yet deploying specialized vector databases (like Milvus or pgvector compiled extensions) introduces severe deployment friction on edge environments like Windows.\n\n" +
      "MoKa implements a dual-tier state and acoustic synthesis architecture:\n\n" +
      "1. Short-Term Context Management (LangGraph + PostgresSaver):\n" +
      "   • Every interaction is committed to a local PostgreSQL checkpointer under session thread identifiers.\n" +
      "   • Rolling Context Summarizer: When turn depth exceeds 6 messages, summarize_conversation_node compiles older history into an incremental state summary and issues RemoveMessage primitives to prune all but the 4 most recent turns, maintaining constant-time inference.\n\n" +
      "2. Long-Term Biographical Memory (schemas/memory_db.py):\n" +
      "   • Native PostgreSQL REAL[] Array Storage: Bypasses C-extension vector plugins by storing raw 384D float arrays in standard relational schemas.\n" +
      "   • O(1) Unique Entity Resolution: Core slots (user_name, user_occupation, favorite_sports_team, favorite_programming_language, user_location) are updated via deterministic key overwrites.\n" +
      "   • NumPy Vector Cosine Deduplication: General facts compute similarity S = (A · B) / (||A|| ||B||). If S > 0.82, the record is updated in place rather than duplicated.\n" +
      "   • Asynchronous Fact Extraction: Non-daemon background threads extract user facts via temperature-0 LLMs, filtering out transient data (weather/calendar).\n\n" +
      "3. Zero-Disk Streaming Voice Substrate (actions/physical/speak.py):\n" +
      "   • Kokoro-ONNX generates 24kHz float32 audio tensors directly in memory.\n" +
      "   • Streams 20ms chunks (480 samples @ 24,000Hz) into a PortAudio C-level callback queue, enabling near-zero latency playback and instantaneous barge-in interruption.",
    keyMetrics: [
      { label: "TTS Chunk Buffer", value: "20 ms (480 Float32 Samples)" },
      { label: "Deduplication Threshold", value: "0.82 Cosine Similarity" },
      { label: "Vector Extension Cost", value: "0 MB (Native REAL[])" },
      { label: "Context Window Cap", value: "Rolling 4 Turns + Summary" },
    ],
    highlights: [
      "Native PostgreSQL REAL[] array storage eliminates complex pgvector compilation requirements on Windows.",
      "NumPy-driven 0.82 cosine similarity threshold prevents memory duplication and resolves updated user preferences.",
      "Asynchronous non-daemon memory extraction processes biographical data without introducing conversational latency.",
      "Kokoro-ONNX streams 24kHz float32 audio chunks directly to sound hardware with zero disk I/O bottlenecks."
    ],
    codeSnippet:
`# Vector Cosine Deduplication & Ring Buffer Stream (memory_db.py & speak.py)
# 1. NumPy Vectorized Cosine Similarity (schemas/memory_db.py)
dot_prod = np.dot(new_embedding, db_embedding)
norm_new, norm_db = np.linalg.norm(new_embedding), np.linalg.norm(db_embedding)
similarity = dot_prod / (norm_new * norm_db) if (norm_new > 0 and norm_db > 0) else 0.0

if similarity > 0.82:  # Update existing fact in place
    cur.execute("UPDATE user_profile_memories SET fact = %s, embedding = %s WHERE id = %s;",
                (fact, new_embedding.tolist(), db_id))

# 2. PortAudio 20ms Zero-Disk Streaming Callback (actions/physical/speak.py)
def _audio_callback(self, outdata, frames, time, status):
    needed, filled = frames, 0
    while needed > 0 and not self._audio_queue.empty():
        chunk = self._audio_queue.get_nowait()
        take = min(needed, len(chunk))
        outdata[filled:filled + take, 0] = chunk[:take]
        needed -= take
        filled += take
    if needed > 0:
        outdata[filled:, 0] = 0.0  # Zero-fill remaining buffer`
  },

  // =========================================================================================
  // PAGE 05: TOOL ECOSYSTEM & DETERMINISTIC EXECUTION ENGINES
  // =========================================================================================
  {
    pageNumber: "05",
    pageLabel: "EXECUTION ENGINES // UNIFIED TOOL ECOSYSTEM",
    title: "Unified Tool Ecosystem & Deterministic Sandboxing",
    subtitle: "From Isolated Subprocess Python to Open MCPs, OS Automation & Vision",
    discipline: "Tool-Augmented LLMs, Protocol Engineering & Cyber-Physical Actuation",
    thesis: "Empowering Local Embodied Agents via Strict Sandbox Isolation, Open Protocol Standards, and Multi-Domain Tool Specialization",
    overview:
      "A comprehensive, multi-domain tool ecosystem spanning deterministic Python sandboxing, Model Context Protocol (MCP) web retrieval, n8n Google Calendar pipelines, OS workstation routines, OpenCV visual docking, and real-time OLED face rendering.",
    description:
      "Small local language models excel at natural dialogue and intent routing, but fail catastrophically when attempting mental arithmetic, real-time web extraction, OS automation, and physical spatial navigation. MoKa resolves these limitations by backing the agent with a diverse, specialized tool ecosystem unified under the LangGraph TOOL_REGISTRY:\n\n" +
      "1. Deterministic Python Code Sandbox (actions/digital/langchain/code_executor.py):\n" +
      "   • Driven by local ornith:9b with a strict 'tool-first, answer-second' system prompt.\n" +
      "   • Spawns an isolated Python subprocess (subprocess.run with 8.0s hard timeout) capturing stdout/stderr with guaranteed temp file cleanup.\n" +
      "   • What it does: Multi-step arithmetic, statistical calculations, unit conversions, date/time offsets, matrix/vector math, tabular/CSV/JSON data transformations, and deterministic algorithm verification.\n\n" +
      "2. Real-Time Web Intelligence & Open Protocols (actions/digital/MCPs.py):\n" +
      "   • Model Context Protocol (MCP): Spawns npx -y tavily-mcp@latest over standard asynchronous stdio pipes using JSON-RPC 2.0 (ClientSession).\n" +
      "   • What it does: Performs live multi-source web searches, extracts deep content payloads, and feeds real-time world knowledge back to the LLM.\n\n" +
      "3. Productivity & Cloud Agents (actions/digital/):\n" +
      "   • Google Calendar Agent (n8n_agents.py): Calls n8n webhook workflows connected to Gemini to query, schedule, reschedule, and cancel calendar events.\n" +
      "   • Todo List Manager (langgraph/todolist_agent.py): Stateful task tracker for creating, prioritizing, and completing user action items.\n" +
      "   • Meteorological Agent (weather_agent.py): Queries wttr.in, formats natural speech, and renders dynamic weather graphics on Cozmo's OLED face.\n\n" +
      "4. Local OS Workstation Setups (actions/digital/setups.py):\n" +
      "   • Gaming Mode: Launches Steam (steam://rungameid/730 for Counter-Strike 2) and Discord.\n" +
      "   • Study Mode: Opens browser tabs for Moodle, Gemini, NotebookLM, and YouTube.\n" +
      "   • Coding Mode: Launches PyCharm IDE, GitHub, and AI developer tools.\n\n" +
      "5. Cyber-Physical Actuation & Perception (actions/physical/):\n" +
      "   • Autonomous Charger Docking (charger.py): OpenCV HSV segmentation (RGB 204,255,51 -> HSV [15..60]), 360° radar sweep, contour centroid tracking (Cx = M10/M00), and reverse alignment onto charging pads.\n" +
      "   • Locomotion & Spatial Scanning (movement.py): Calibrated millimeter drive (move_forward/backward), precise angle turns, and arc_sweep environmental surveys.\n" +
      "   • OLED Face Expressions & Timers (face.py, timer.py): 128x64 bitmap rendering of animated emotional eyes, countdown timers (MM:SS), weather icons, and thinking indicators.\n" +
      "   • System Hardware Telemetry (system_tools.py): Real-time system clock and date queries synchronized with the host OS.",
    keyMetrics: [
      { label: "Active Tool Domains", value: "5 Distinct Categories" },
      { label: "Sandbox Hard Timeout", value: "8.0s Subprocess Isolation" },
      { label: "Protocol Standard", value: "MCP (JSON-RPC 2.0 / stdio)" },
      { label: "Autonomous Docking", value: "HSV Radar + Centroid Tracking" },
    ],
    highlights: [
      "Deterministic Python sandbox offloads math, data parsing, and logic to an isolated subprocess with 8.0s timeout.",
      "Model Context Protocol (MCP) and n8n webhooks bridge live web intelligence and Google Calendar automation.",
      "Workstation presets trigger multi-app OS routines for Gaming (CS2/Discord), Study (Moodle/NotebookLM), and Coding (PyCharm/GitHub).",
      "Full physical tool suite handles autonomous HSV charger docking, OLED face expressions, countdown timers, and calibrated locomotion."
    ],
    codeSnippet:
`# Unified Tool Dispatch & Multi-Domain Handlers (worker_nodes.py, code_executor.py, setups.py)
# 1. Unified Dynamic Tool Registry (core/routing/layer2/worker_nodes.py)
TOOL_REGISTRY = {
    # Computational & Web Intelligence
    "code_executor_node": code_executor_node,   # ornith:9b Python sandbox (8.0s isolation)
    "web_search_node": web_search_node,         # Tavily MCP (JSON-RPC 2.0 stdio client)
    "weather_node": weather_node,               # wttr.in real-time meteorological agent
    "calendar_node": calendar_node,             # n8n webhook Google Calendar manager
    "todolist_node": todolist_node,             # Interactive stateful task tracker
    # Physical Actuation & Vision
    "dock_with_charger": dock_with_charger_node,# OpenCV HSV color segmentation docking
    "move_forward": move_forward_node,          # Calibrated 100mm differential locomotion
    "arc_sweep": arc_sweep_node,                # 360° radar environmental survey
    # OS Workstation Automation
    "setup_gaming": setup_gaming_node,          # Native Steam (CS2) & Discord launcher
    "setup_study": setup_study_node,            # Browser multi-tab study workspace
    "setup_coding": setup_coding_node,          # PyCharm IDE & GitHub launcher
    "tell_time": tell_time_node,                # Real-time system clock synchronization
}

def execute_tool_node(state: AgentState):
    """Dynamically dispatches any retrieved tool from a single generic LangGraph node."""
    route = state.get("next_route", "none")
    handler = TOOL_REGISTRY.get(route)
    return handler(state) if handler else {"messages": [AIMessage(content="Tool not found.")]}`
  }
];
