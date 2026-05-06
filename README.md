# Cozmo AI Assistant

An AI-powered assistant built around the **Anki Cozmo** robot. The system uses a two-layer intelligence pipeline — fast semantic reflexes for instant robot commands, and a LangGraph-powered AI brain for complex tasks like natural conversation, Google Calendar management, and real-time web search — all accessible via an interactive launcher or a **FastAPI** REST bridge.

---

## Features

| Feature | Description |
|---|---|
| **Interactive Launcher** | Single `main.py` entry point with a menu to choose Terminal Mode or Robot Mode |
| **Voice Input** | Wake-word listener (`"hey buddy"`) captures microphone audio, transcribes via Google Speech Recognition, and routes through the full AI pipeline |
| **Text-to-Speech** | Cozmo speaks responses aloud using Microsoft Edge TTS, with support for **English & Persian (Farsi)** |
| **AI Brain (LangGraph)** | Routes user input through a local LLM (`qwen2.5:1.5b` via Ollama) to one of three nodes: Calendar, Web Search, or local Chat |
| **Web Search** | Delegates real-time queries (news, weather, sports) to an **n8n** workflow via a dedicated webhook |
| **Layer 1 Semantic Router** | Ultra-fast embedding-based intent matching for physical robot commands (dock, stop, time, date) — bypasses the LLM entirely |
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
┌──────────────────────────────────────┐
│         LangGraph AI Brain           │  ← Local LLM (Ollama / qwen2.5)
│  ┌────────────┬──────────┬────────┐  │
│  │  Calendar  │   Web    │  Chat  │  │
│  │   Node     │  Search  │  Node  │  │
│  └─────┬──────┴────┬─────┴────────┘  │
└────────┼───────────┼─────────────────┘
         │           │
         ▼           ▼
   n8n /calendarTool  n8n /websearchTool
   → Gemini / ollama       → Web Search API
   → Google Calendar
```

**Two-layer processing:**
1. **Layer 1 (Semantic Router):** Embedding-based intent detection for latency-critical physical actions. Bypasses the LLM entirely.
2. **Layer 2 (LangGraph):** A stateful agent graph that classifies queries into `calendar`, `web_search`, or `none` (local chat), and routes accordingly.

---

## Project Structure

```
cozmo_ai_assistant/
│
├── main.py                   # Interactive launcher (Terminal / Robot mode menu)
│
├── core/
│   ├── connection.py         # Singleton Cozmo robot connection manager (pycozmo)
│   ├── cozmo_mode.py         # FastAPI app & REST endpoints (Robot Mode)
│   ├── router.py             # LangGraph agent graph (calendar / web_search / chat)
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
│   └── digital/              # Cloud/API integrations
│       └── n8n_tools.py      # n8n webhook clients (calendar & web search)
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

You'll see a menu:

```
=======================================
           COZMO AI ASSISTANT
=======================================
1. Start in Terminal (No Robot Required)
2. Start Cozmo (Physical Robot)
3. Exit
```

- **Option 1** — Launches the terminal REPL. Auto-starts n8n in the background. No robot needed.
- **Option 2** — Connects to the physical Cozmo and starts the FastAPI server on `http://localhost:8000`. Interactive API docs available at `http://localhost:8000/docs`.

### 3. Start the voice listener (optional)

Run alongside `main.py` to enable wake-word voice input:

```bash
python actions/physical/listen.py
```

Say **"hey buddy"** followed by your command. It routes through the same Layer 1 → n8n pipeline as the terminal.

---

## API Endpoints

> Only available in **Robot Mode** (option 2).

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/actions/speak` | Make Cozmo speak a given text |
| `POST` | `/actions/dock` | Trigger autonomous charger docking |
| `POST` | `/actions/face` | Update Cozmo's face display |
| `POST` | `/actions/timer` | Start a countdown timer |

### Example: Make Cozmo Speak

```bash
curl -X POST http://localhost:8000/actions/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world!", "play_animation": true, "language": "en"}'
```

### Example: Face Expression

```bash
curl -X POST http://localhost:8000/actions/face \
  -H "Content-Type: application/json" \
  -d '{"act": "thinking"}'
```

Available face acts: `timer`, `weather`, `thinking`, `reset`

---

## Configuration

| Component | Default | Where to Change |
|---|---|---|
| Ollama model | `qwen2.5:1.5b` | `core/router.py` |
| Ollama base URL | `http://localhost:11434` | `core/router.py` |
| Calendar webhook URL | `http://localhost:5678/webhook/calendarTool` | `actions/digital/n8n_tools.py` |
| Web search webhook URL | `http://localhost:5678/webhook/websearchTool` | `actions/digital/n8n_tools.py` |
| FastAPI host/port | `localhost:8000` | `main.py` |
| TTS voice (EN) | `en-US-ChristopherNeural` | `actions/physical/speak.py` |
| TTS voice (FA) | `fa-IR-FaridNeural` | `actions/physical/speak.py` |
| Wake word | `"hey buddy"` | `actions/physical/listen.py` |
| ArUco target marker ID | `0` | `actions/physical/charger.py` |

---

## Roadmap

- [x] Voice input (microphone → wake-word → speech-to-text → pipeline)
- [x] Web search via n8n workflow
- [x] Single unified launcher (`main.py`) with mode selection
- [ ] Telegram bot as a third communication channel
- [ ] YOLO model for charger detection (replacing ArUco)
- [ ] Memory / conversation history in LangGraph
- [ ] Weather display on Cozmo's face via live API

---

## License

This project is for educational and research purposes.