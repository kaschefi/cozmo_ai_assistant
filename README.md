# Cozmo AI Assistant

An AI-powered assistant built around the **Anki Cozmo** robot. The system uses a state-of-the-art two-layer intelligence pipeline: **Layer 1** fast semantic reflexes (50ms latency) for instant physical and laptop commands, and **Layer 2** a dynamic **LangGraph-powered AI brain** that uses local LLMs (`qwen2.5:3b` via Ollama) and a **Vector RAG Tool Retrieval Index** for complex natural conversation, Google Calendar management, and advanced search agents (Weather, Tavily MCP, Web Search). All features are exposed via an interactive console launcher, voice control, or a **FastAPI** REST bridge.

---

## Features

| Feature | Description |
|---|---|
| **Interactive Launcher** | Unified `main.py` console with a menu to run Terminal Mode (repl with brain) or Cozmo Mode (robot + API server) |
| **Voice Input** | Wake-word listener (`"hey buddy"`) captures mic audio, transcribes via Google Speech Recognition, and routes to Layer 1 reflexes or LangGraph |
| **Text-to-Speech** | Speeds responses using Microsoft Edge TTS, supporting both **English & Persian (Farsi)** with high-fidelity neural voices |
| **Layer 1 Semantic Router** | Instant intent matching (~50ms) using `semantic-router` + `FastEmbed` for latency-critical commands (bypasses LLM) |
| **Dynamic Layer 2 Tool RAG** | Rather than bloating LLM prompts with static definitions, tools are indexed in an in-memory vector database (**FAISS** + `BAAI/bge-small-en-v1.5` embeddings) and dynamically injected into the router's context based on relevance |
| **Tavily MCP Integration** | Executes highly optimized, real-time web searches using the official Tavily **Model Context Protocol (MCP)** server spawned via standard `npx` stdio client pipes |
| **Local Laptop Automation Setups** | Instant laptop routines for **Gaming Mode** (launches Steam, CS2, Discord), **Study Mode** (opens Moodle, Gemini, NotebookLM), and **Coding Mode** (opens PyCharm, GitHub, Gemini) |
| **Specialized Weather Agent** | A ReAct agent that queries the `wttr.in` API to provide real-time, conversational weather updates |
| **Google Calendar Integration** | Multi-step calendar manager that queries, creates, moves, or deletes appointments using an **n8n** webhook connected to Gemini API |
| **Autonomous Docking** | Visual color-based navigation — Cozmo activates his camera, scans for the charger's yellow-green marker (RGB 204, 255, 51) using HSV color filtering, steers toward it, and backs onto the charging pins |
| **Face Expressions** | Dynamic rendering of graphics, countdown timers, and weather info directly onto Cozmo's 128×64 OLED face display |
| **Timer** | Runs asynchronous countdown timers with real-time MM:SS face updates |
| **FastAPI REST Bridge** | Exposes all physical actions (docking, speak, timer, face expressions) as HTTP endpoints for external triggers |
| **Short-Term Memory** | PostgreSQL-backed persistent session state tracker (`PostgresSaver`) paired with rolling context summarization and automatic history trimming to keep context windows tiny |
| **Long-Term Memory** | Permanent biographical store using native PostgreSQL float arrays (`REAL[]`), local `FastEmbed` embeddings, NumPy cosine similarity, dynamic entity resolution categories ($O(1)$ updates), and async background extraction threads |

---

## Architecture

```
                       User Input (Terminal / Voice)
                                     │
                                     ▼
                ┌──────────────────────────────────────────┐
                │         Layer 1 Semantic Router          │  ← Fast Embeddings (~50ms)
                │      (reflex_registry + FastEmbed)       │    Bypasses LLM entirely.
                └────────────────────┬─────────────────────┘
                                     │ No reflex match
                                     ▼
                ┌──────────────────────────────────────────┐
                │        Layer 2: LangGraph Brain          │
                │                                          │
                │  ┌────────────────────────────────────┐  │
                │  │    Tool Retrieval Node (FAISS)     │  │  ← Dynamic Tool RAG Selection
                │  └─────────────────┬──────────────────┘  │
                │                    │ top 2 matched tools
                │                    ▼
                │  ┌────────────────────────────────────┐  │
                │  │       Router Supervisor (LLM)      │  │  ← Structured classifier
                │  └────────┬────────┬────────┬─────────┘  │
                └───────────┼────────┼────────┼────────────┘
                            │        │        │
                            ▼        ▼        ▼
                      Calendar    Weather  Web Search / Casual Chat
                       (n8n)     (ReAct)   (Tavily MCP / Ollama)
```

### 1. Layer 1 Semantic Router (Fast Reflexes)
Embedding-based semantic lookup. Utterances are mapped to a local registry of python operations (`core/registry.py`) enabling instantaneous response for:
*   Physical actions: Autonomous charger docking.
*   System operations: Date, time, and laptop configurations (Gaming/Coding/Study setups).

### 2. Layer 2 LangGraph Brain (Dynamic Tool RAG)
For complex inputs, the system triggers a stateful graph:
1.  **Tool Retrieval Node**: Uses `FAISS` to run similarity search on the user's query against registered tool schemas, fetching only the top 2 candidates.
2.  **Route Query**: Constructs a system prompt with only the retrieved candidate tools and uses local LLM (`qwen2.5:3b`) to yield a structured `RouteDecision`.
3.  **Specialized Workers**: Routes to n8n (Google Calendar, Web Search), ReAct agent (Weather), or falls back to casual conversational chat (`chat_node`).

### 3. Layer 2 Memory Architecture (Short & Long-Term)
The assistant features a sophisticated, persistent two-tiered memory architecture designed to run efficiently on local systems without heavy cloud or complex database dependencies:

#### A. Short-Term Memory (Stateful Session Checkpointing)
*   **PostgreSQL Session Checkpointer**: Driven by LangGraph's `PostgresSaver`, conversational sessions are stored statefully using connection pooling and database thread trackers (`thread_id="cozmo_default_session"`).
*   **Automatic Database Migrations**: Self-heals and sets up all required system schemas and state tables natively on application initialization (`checkpointer.setup()`), gracefully falling back to local memory if PostgreSQL is offline.
*   **Rolling Summarization Node**: To prevent local LLM context window bloating and maintain fast inference speeds:
    *   If a session accumulates **more than 6 messages**, the graph triggers `summarize_conversation_node`.
    *   It condenses historical context into a concise running `summary` attribute inside the state.
    *   It emits a sequence of `RemoveMessage` commands to prune active messages older than the last 4 exchanges (2 full turns), freeing up significant CPU resources while maintaining context.

#### B. Long-Term Memory (Permanent Semantic Profile Core)
*   **Native PostgreSQL Vector Storage (`REAL[]`)**: Bypasses OS-level compiled binaries or dependencies on `pgvector` (highly beneficial for Windows support) by utilizing native float array storage mapping (`REAL[]`) to persist high-dimensional fact embeddings.
*   **Local Fast Embedding Generation**: Generates 384-dimensional dense vectors locally using `LangChainFastEmbedBridge` powered by the optimized `FastEmbed` library (`BAAI/bge-small-en-v1.5`), ensuring instant query/fact processing.
*   **Entity Resolution & Dynamic Category Overwriting ($O(1)$ updates)**:
    *   Supports key biological and user attribute categories: `user_name`, `user_occupation`, `favorite_sports_team`, `favorite_programming_language`, and `user_location`.
    *   When Cozmo extracts a fact in these unique categories, it bypasses complex semantic logic and performs $O(1)$ entity resolution—directly replacing or updating the database row to prevent key duplicates (e.g. no redundant name facts).
*   **NumPy Cosine Similarity & Deduplication**:
    *   For general preferences or hobbies, Cozmo evaluates the semantic overlap mathematically via local NumPy array operations:
        $$\text{Similarity} = \frac{A \cdot B}{\|A\| \|B\|}$$
    *   A strict similarity threshold of **`0.82`** prevents duplicate biographical facts; if a new fact is semantically similar to an existing fact, the system updates the original rather than adding a new entry.
*   **Asynchronous Fact Extraction & Noise Filtering**:
    *   Memory extraction executes on a non-blocking background thread (`threading.Thread(daemon=False)`) at the end of each response, keeping physical text-to-speech (TTS) and voice response cycles entirely lag-free.
    *   Runs a low-temperature (0.0) deterministic LLM extractor (`router_llm`) on the last 3 messages to parse out explicit user biographical facts while strictly filtering out temporary items (weather, calendar times, dates) and assistant suggestions.
*   **Dual-Mode Retrieval Pipeline**:
    *   **Vector Semantic Search**: Matches current query embeddings against stored facts to fetch up to 3 highly relevant personal details per turn, feeding them silently to Cozmo's system context.
    *   **Meta-Query Fallback**: Intercepts broad questions like *"what do you know about me"* or *"tell me all the facts you know"* (which have 0% semantic overlap with vector embeddings of actual facts) and returns the last 15 raw database records directly.

---

## Project Structure

The project has a highly modular architecture separating physical controls, digital integrations, state schemas, and core routing logic:

```
cozmo_ai_assistant/
│
├── main.py                     # Entry point launcher (Terminal Mode / Cozmo Mode menu)
├── Launch_Cozmo.bat            # Windows startup script to execute Terminal Mode
├── roadmap.md                  # Project milestones and task backlog
├── README.md                   # Full system documentation
│
├── core/
│   ├── __init__.py
│   │
│   ├── hardware/               # Physical hardware connections and robot managers
│   │   ├── __init__.py
│   │   └── connection.py       # Singleton Cozmo hardware connection manager
│   │
│   ├── routing/                # AI Intelligence, Layer 1 & 2 routers, reflex registries, and tool RAG
│   │   ├── __init__.py
│   │   ├── registry.py         # Decorator class for low-latency Layer 1 reflex registration
│   │   ├── router.py           # LangGraph state machine flow, supervisor, and node workers
│   │   ├── semantic_layer.py   # Layer 1 semantic matching router & package-wide action loader
│   │   └── tool_vector_db.py   # FAISS vector store bridge for dynamic tool registration & retrieval
│   │
│   └── modes/                  # Interface modes and runtime application shells
│       ├── __init__.py
│       ├── cozmo_mode.py       # FastAPI application server and REST endpoint routing
│       └── terminal_mode.py    # Terminal REPL chat client with n8n/Ollama auto-initialization
│
├── actions/
│   ├── physical/               # Robot hardware controls
│   │   ├── __init__.py
│   │   ├── charger.py          # Vision-guided docking using OpenCV HSV color filtering (Yellow-Green, RGB 204, 255, 51)
│   │   ├── face.py             # OLED canvas draw actions (Timer MM:SS, weather details, thinking indicator)
│   │   ├── listen.py           # Speech recognition wake-word parser ("hey buddy") and FastAPI/n8n forwarder
│   │   ├── speak.py            # edge-tts engine + Persian Gemma translator + 22kHz wav converter
│   │   └── timer.py            # Asynchronous countdown clock controller
│   │
│   └── digital/                # Digital APIs & Agent integrations
│       ├── __init__.py
│       ├── langchain_agents.py # Weather ReAct agent utilizing wttr.in tool & prompt engineering
│       ├── MCPs.py             # Tavily search powered by standard Model Context Protocol client via npx
│       ├── n8n_agents.py       # n8n webhook connectors for Google Calendar and web searching
│       ├── setups.py           # OS-level workstation launchers (Gaming, Study, Coding routines)
│       └── system_tools.py     # System action registry (Date and Time responses)
│
├── schemas/
│   ├── __init__.py
│   └── request_models.py       # Pydantic models for REST API requests and LangGraph TypedDict state
│
└── utils/
    ├── __init__.py
    └── logger.py               # Centralized logging configurations
```

---

## Prerequisites

### Hardware
*   **Anki Cozmo** robot + USB charger base + Android/iOS device running Cozmo app in SDK mode (required for physical Cozmo Mode).

### Software
*   Python **3.10+** (Python 3.11 recommended).
*   [**Ollama**](https://ollama.com/) running locally.
*   [**n8n**](https://n8n.io/) installed globally (`npm install -g n8n`) or running in your environment (auto-started by launcher).
*   **FFmpeg** (added to your system PATH; required by `pydub` for streaming speech audio to Cozmo).

### Node Packages
*   `tavily-mcp` (run automatically via `npx` during search).

### Python Libraries
Install the requirements using standard pip:
```bash
pip install pycozmo fastapi uvicorn langchain-ollama langchain-community langgraph semantic-router fastembed edge-tts pydub deep-translator opencv-python Pillow requests speechrecognition mcp python-dotenv faiss-cpu
```

Or sync with the project's **uv** configurations:
```bash
uv sync
```

---

## Getting Started

### 1. Environment Configuration

Create a `.env` file in the project root:
```env
TAVILY_API_KEY=your_tavily_api_key_here
```

### 2. Fetch the Local AI Models

Pull the required Ollama models:
```bash
ollama pull qwen2.5:3b
```

### 3. Launch the Assistant

Run the unified launcher:
```bash
python main.py
```

*   **Option 1 (Terminal Mode)**: Launches the terminal chat interface. This will automatically scan ports, boot up n8n in the background, check Ollama's availability, compile the tool registry index, and open the command prompt.
*   **Option 2 (Cozmo Mode)**: Connects to the physical robot and opens a FastAPI REST bridge on port `8000`.

### 4. Enable Voice Wake-Word Activation (Optional)

Start the listener in a separate terminal:
```bash
python actions/physical/listen.py
```
Simply speak **"hey buddy"** followed by any command (e.g. *"hey buddy, set it for coding"* or *"hey buddy, what's today's date"*).

---

## Technical Highlights

### 1. Dynamic Tool RAG Retrieval
Instead of feeding all available tool instructions into the LLM system prompt—which decreases latency and accuracy—this application utilizes a FAISS-backed Vector Database registry:
```python
# actions/digital/n8n_agents.py
tool_rag_registry.register_tool_schema(
    name="calendar_node",
    description="Manages Google Calendar. Use this if the user wants to check, create, move, change, or delete meetings, events, appointments, or schedules."
)
```
Upon a user query, the `tool_retrieval_node` matches the query vector with the tool embeddings and passes the select matched tools to the Router LLM.

### 2. Standard Model Context Protocol (MCP) Client
Using standard `mcp` stdio client parameters, the Tavily search tool operates dynamically:
```python
server_params = StdioServerParameters(
    command="npx",
    args=["-y", "tavily-mcp@latest"],
    env=os.environ.copy(),
    extra_spawn_args={"shell": True}
)
```
This spawns the standard Tavily MCP package, executes a query, and handles communication perfectly, bypassing bulky client frameworks.

### 3. Low-Latency Local Automation Reflexes
Workstation presets are tied to local shell utilities:
*   **Gaming**: Executes custom URI protocols (`steam://`) and queries paths to boot update launchers before executing Discord update commands.
*   **Coding & Study**: Performs multi-tab browser dispatch routines (`webbrowser.open`) and searches registry folders dynamically using glob matching to execute JetBrains IDEs.

---

## License

This project is for educational, research, and hobby purposes.