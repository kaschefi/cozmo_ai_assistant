# Cozmo AI Assistant

An AI-powered assistant built around the **Anki Cozmo** robot. The system uses a two-layer intelligence pipeline — fast semantic reflexes for instant robot commands, and a LangGraph-powered AI brain for complex tasks like natural conversation, Google Calendar management, and specialized agents (Weather, Web Search) — all accessible via an interactive launcher or a **FastAPI** REST bridge.

---

## Features

| Feature | Description |
|---|---|
| **Interactive Launcher** | Single `main.py` entry point with a menu to choose Terminal Mode or Robot Mode |
| **Voice Input** | Wake-word listener (`"hey buddy"`) captures microphone audio, transcribes via Google Speech Recognition, and routes through the full AI pipeline |
| **Text-to-Speech** | Cozmo speaks responses aloud using Microsoft Edge TTS, with support for **English & Persian (Farsi)** |
| **AI Brain (LangGraph)** | Routes user input through a local LLM (`qwen2.5:1.5b` via Ollama) to specialized nodes: Weather, Calendar, Web Search, or local Chat |
| **Specialized Weather Agent** | A ReAct agent that uses the `wttr.in` tool to provide real-time, conversational weather updates |
| **Web Search** | Delegates general real-time queries (news, sports) to an **n8n** workflow via a dedicated webhook |
| **Layer 1 Semantic Router** | Ultra-fast intent matching for physical robot commands (dock, stop, time, date) using `semantic-router` + FastEmbed |
| **Google Calendar Integration** | Reads, creates, moves, and deletes calendar events via an **n8n** workflow connected to the Gemini API |
| **Autonomous Docking** | Visual ArUco marker navigation — Cozmo finds its charger and docks itself |
| **Face Expressions** | Renders custom text/graphics directly on Cozmo's 128×64 OLED face display |
| **Timer** | Runs async countdown timers with live MM:SS face updates |
| **FastAPI REST Bridge** | All robot capabilities are exposed as HTTP endpoints for easy external integration |

---

## Architecture

```
User Input (Terminal or Voice)
    │
    ▼
┌─────────────────────────────────┐
│         Layer 1 Router          │  ← Fast semantic matching (~50ms)
│  (semantic-router + FastEmbed)  │    Handles: dock, stop, time, date
└────────────────┬────────────────┘
                 │ No match
                 ▼
┌──────────────────────────────────────────────────┐
│              LangGraph AI Brain Node             │  ← Local LLM (Ollama / qwen2.5)
│  ┌────────────┬──────────────┬────────────────┐  │
│  │  Calendar  │   Weather    │      ...       │  │
│  │   Node     │    Node      │   (etc.)       │  │
│  │ (n8n Tool) │ (ReAct Agent)│                │  │
│  └─────┬──────┴──────┬───────┴────────┬───────┘  │
└────────┼─────────────┼────────────────┼──────────┘
         │             │                │
         ▼             ▼                ▼
   n8n /calendarTool  wttr.in API      External APIs
   → Google Cal       (Weather Tool)   (Search, etc.)
```

**Two-layer processing:**
1. **Layer 1 (Semantic Router):** Embedding-based intent detection for latency-critical physical actions. Bypasses the LLM entirely.
2. **Layer 2 (LangGraph):** A stateful agent graph that classifies queries into `calendar`, `weather`, `web_search`, or `none` (local chat), and routes to the appropriate worker node.

---

## Project Structure

```
cozmo_ai_assistant/
│
├── main.py                   # Interactive launcher (Terminal / Robot mode menu)
│
├── core/
│   ├── connection.py         # Singleton Cozmo robot connection manager
│   ├── cozmo_mode.py         # FastAPI app & REST endpoints (Robot Mode)
│   ├── router.py             # LangGraph agent graph & node definitions
│   ├── semantic_layer.py     # Layer 1 fast semantic router & reflex registry
│   └── terminal_mode.py      # Interactive terminal REPL (no robot required)
│
├── actions/
│   ├── physical/             # Physical robot interactions
│   │   ├── charger.py        # Autonomous docking via ArUco marker vision
│   │   ├── face.py           # Cozmo OLED face expression rendering
│   │   ├── listen.py         # Wake-word mic listener → Layer 1 → n8n pipeline
│   │   ├── speak.py          # Edge TTS → audio conversion → Cozmo playback
│   │   └── timer.py          # Async countdown timer with face display
│   └── digital/              # Cloud/API/Agent integrations
│       ├── langchain_agents.py # ReAct agents (Weather Agent + tools)
│       └── n8n_agents.py       # n8n webhook clients (Calendar & Web Search)
│
├── schemas/
│   └── request_models.py     # Pydantic models & LangGraph AgentState
│
└── utils/
    └── logger.py             # Shared logging utilities
```

---

## Prerequisites

### Hardware
- **Anki Cozmo** robot + USB cable + Cozmo app (required only for Robot Mode)

### Software
- Python **3.10+**
- [**Ollama**](https://ollama.com/) running locally with the `qwen2.5:1.5b` model
- [**n8n**](https://n8n.io/) (auto-started by the terminal launcher, or run manually)
- **FFmpeg** (required by `pydub` for audio conversion in Robot Mode)

### Python Dependencies

Install with `pip`:
```bash
pip install pycozmo fastapi uvicorn langchain-ollama langgraph semantic-router fastembed edge-tts pydub deep-translator opencv-python Pillow requests speechrecognition
```

Or using `uv`:
```bash
uv sync
```

---

## Getting Started

### 1. Pull the Ollama model

```bash
ollama pull qwen2.5:1.5b
```

### 2. Run the launcher

```bash
python main.py
```

Choose **Option 1** for the terminal brain or **Option 2** to connect to the physical robot.

### 3. Start the voice listener (optional)

Run alongside `main.py` to enable wake-word voice input:

```bash
python actions/physical/listen.py
```

Say **"hey buddy"** followed by your command.

---

## Configuration

| Component | Default | Where to Change |
|---|---|---|
| Ollama model | `qwen2.5:1.5b` | `core/router.py` |
| Ollama base URL | `http://localhost:11434` | `core/router.py` |
| Calendar webhook URL | `http://localhost:5678/webhook/calendarTool` | `actions/digital/n8n_agents.py` |
| Web search webhook URL | `http://localhost:5678/webhook/websearchTool` | `actions/digital/n8n_agents.py` |
| Weather tool API | `wttr.in` | `actions/digital/langchain_agents.py` |
| FastAPI host/port | `localhost:8000` | `main.py` |
| Wake word | `"hey buddy"` | `actions/physical/listen.py` |

---

## Roadmap

- [x] Voice input
- [x] Web search via n8n
- [x] Specialized Weather Agent (ReAct)
- [x] Single unified launcher (`main.py`)
- [ ] Telegram bot integration
- [ ] YOLO model for charger detection
- [ ] Memory / conversation history in LangGraph

---

## License

This project is for educational and research purposes.