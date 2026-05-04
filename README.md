# Cozmo AI Assistant

An AI-powered assistant built around the **Anki Cozmo** robot. The system uses a two-layer intelligence pipeline — fast semantic reflexes for instant robot commands, and a LangGraph-powered AI brain for complex tasks like natural conversation and Google Calendar management — all exposed via a **FastAPI** REST bridge.

---

## Features

| Feature | Description |
|---|---|
| **Voice Input** | Wake-word listener (`"hey buddy"`) captures microphone audio, transcribes via Google Speech Recognition, and routes through the full AI pipeline |
| **Text-to-Speech** | Cozmo speaks responses aloud using Microsoft Edge TTS, with support for **English & Persian (Farsi)** |
| **AI Brain (LangGraph)** | Routes user input through a local LLM (`qwen2.5:1.5b` via Ollama) to either general chat or a calendar tool |
| **Layer 1 Semantic Router** | Ultra-fast intent matching for physical robot commands (dock, stop, time) using `semantic-router` + FastEmbed |
| **Google Calendar Integration** | Delegates calendar reads/writes to an **n8n** workflow connected to the Gemini API |
| **Autonomous Docking** | Visual ArUco marker navigation — Cozmo finds its charger and docks itself |
| **Face Expressions** | Renders custom text/graphics directly on Cozmo's 128×64 OLED face display |
| **Timer** | Runs async countdown timers with live face updates |
| **FastAPI REST Bridge** | All capabilities are exposed as HTTP endpoints for easy integration with external systems |
| **Terminal Mode** | A rich terminal REPL (`terminal_brain.py`) for direct text-based interaction without a robot |

---

## Architecture

```
User Input
    │
    ▼
┌─────────────────────────────────┐
│         Layer 1 Router          │  ← Fast semantic matching (50ms)
│  (semantic-router + FastEmbed)  │    Handles: dock, stop, time, date
└────────────────┬────────────────┘
                 │ No match
                 ▼
┌─────────────────────────────────┐
│      LangGraph AI Brain         │  ← Local LLM (Ollama / qwen2.5)
│  ┌────────────┬──────────────┐  │
│  │ Calendar   │  Chat Node   │  │
│  │   Node     │  (Fallback)  │  │
│  └─────┬──────┴──────────────┘  │
└────────┼────────────────────────┘
         │ calendar route
         ▼
   n8n Webhook → Gemini API → Google Calendar
```

**Two-layer processing:**
1. **Layer 1 (Semantic Router):** Embedding-based intent detection for latency-critical physical actions. Bypasses the LLM entirely.
2. **Layer 2 (LangGraph):** A stateful agent graph that routes complex queries to either a local chat LLM or external tools (n8n/calendar).

---

## Project Structure

```
cozmo_ai_assistant/
│
├── main.py                  # FastAPI app entry point & REST endpoints
│
├── core/
│   ├── connection.py        # Cozmo robot connection manager (pycozmo)
│   ├── router.py            # LangGraph agent graph (LLM routing logic)
│   ├── semantic_layer.py    # Layer 1 fast semantic router & reflex registry
│   └── terminal_brain.py   # Interactive terminal REPL (no robot required)
│
├── actions/
│   ├── physical/            # Physical robot interactions
│   │   ├── charger.py       # Autonomous docking via ArUco marker vision
│   │   ├── face.py          # Cozmo OLED face expression rendering
│   │   ├── listen.py        # Wake-word mic listener → Layer 1 → n8n pipeline
│   │   ├── speak.py         # Edge TTS → audio conversion → Cozmo playback
│   │   └── timer.py         # Async countdown timer logic
│   └── digital/             # Cloud/API integrations
│       └── n8n_tools.py     # n8n webhook client for Google Calendar
│
├── schemas/
│   └── request_models.py    # Pydantic models & LangGraph AgentState
│
└── utils/
    └── logger.py            # Shared logging utilities
```

---

## Prerequisites

### Hardware
- **Anki Cozmo** robot + USB cable + Cozmo app

### Software
- Python **3.10+**
- [**Ollama**](https://ollama.com/) running locally with the `qwen2.5:1.5b` model
- [**n8n**](https://n8n.io/) (auto-started by the terminal brain, or run manually)
- **FFmpeg** (required by `pydub` for audio conversion)

### Python Dependencies

Install with `pip` or `uv`:

```bash
pip install pycozmo fastapi uvicorn langchain-ollama langgraph semantic-router fastembed edge-tts pydub deep-translator opencv-python Pillow requests
```

Or if using `uv`:
```bash
uv sync
```

---

## Getting Started

### 1. Pull the Ollama model

```bash
ollama pull qwen2.5:1.5b
```

### 2. Start the FastAPI bridge (with physical robot)

Connect Cozmo via USB, then:

```bash
python main.py
```

The server starts on `http://localhost:8000`. Interactive API docs are available at `http://localhost:8000/docs`.

### 3. Use Terminal Mode (no robot needed)

```bash
python core/terminal_brain.py
```

This launches a colorized REPL that auto-starts n8n and routes your typed commands through the full AI pipeline.

---

## API Endpoints

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
| n8n webhook URL | `http://localhost:5678/webhook/calendarTool` | `actions/digital/n8n_tools.py` |
| FastAPI host/port | `localhost:8000` | `main.py` |
| TTS voice (EN) | `en-US-ChristopherNeural` | `actions/physical/speak.py` |
| TTS voice (FA) | `fa-IR-FaridNeural` | `actions/physical/speak.py` |
| ArUco target marker ID | `0` | `actions/physical/charger.py` |


---

## License

This project is for educational and research purposes.