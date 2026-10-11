import os
import sys

# Ensure both workspace root and backend directory are in the Python search path
# so that imports resolve correctly when run directly
MODE_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.dirname(MODE_DIR)
BACKEND_DIR = os.path.dirname(CORE_DIR)
WORKSPACE_DIR = os.path.dirname(BACKEND_DIR)

if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Security, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import uvicorn

# Import request models and unified brain router
from pydantic import BaseModel
from schemas.request_models import ChatRequest
from schemas.chat_history_db import chat_history_db
from core.routing.brain import process_user_intent


async def _background_warmup():
    """
    Non-blocking background task that pre-warms AI/ML models (FastEmbed, Semantic Router,
    Kokoro ONNX) while the web server is already live and responding to health probes.
    """
    try:
        print("[MoKa Warmup] Starting background model pre-warming...")
        loop = asyncio.get_running_loop()
        
        # 1. Warm up shared encoder
        from core.routing.encoder import get_shared_encoder
        await loop.run_in_executor(None, get_shared_encoder)

        # 2. Warm up semantic layer router & tool vector DB index
        from core.routing.layer1.semantic_layer import initialize_router
        await loop.run_in_executor(None, initialize_router)

        # 3. Warm up LAYA Typed Decision Router
        from core.routing.layer2.graph_nodes import get_laya_agent
        await loop.run_in_executor(None, get_laya_agent)

        # 4. Warm up Kokoro ONNX speaker model
        from actions.physical.speak import speaker
        await loop.run_in_executor(None, speaker.warmup)

        print("[MoKa Warmup] All cognitive models pre-warmed & active in RAM!")
    except Exception as e:
        print(f"[MoKa Warmup] Notice during background pre-warming: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Launch background pre-warming without blocking server boot
    asyncio.create_task(_background_warmup())
    
    # Auto-seed history from LangSmith if DB is currently empty
    try:
        existing_sessions = chat_history_db.get_all_sessions()
        if not existing_sessions:
            print("[MoKa Startup] Chat history DB is empty. Syncing past conversations from LangSmith...")
            asyncio.create_task(asyncio.to_thread(chat_history_db.sync_from_langsmith, 50))
    except Exception as e:
        print(f"[MoKa Startup] Notice during history check: {e}")

    yield


app = FastAPI(
    title="MoKa Web API",
    description="Dedicated connection bridge for MoKa's cognitive layer, enabling chat interface access offline.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware configuration allowing traffic from Vite/React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-Moka-Token", auto_error=False)

async def verify_moka_token(request: Request, token: str = Security(api_key_header)):
    # Localhost automatic bypass
    client_ip = request.client.host if request.client else None
    if client_ip in ("127.0.0.1", "::1"):
        return token or os.getenv("MOKA_ADMIN_TOKEN") or "local-bypass"

    expected_token = os.getenv("MOKA_ADMIN_TOKEN")
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: MoKa Admin Token is unconfigured."
        )
    if not token or token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid or missing X-Moka-Token header."
        )
    return token

@app.get("/api/token/local")
async def get_local_token(request: Request):
    """
    Returns the configured MoKa Admin Token if visited from localhost (127.0.0.1 or ::1).
    """
    client_ip = request.client.host if request.client else None
    if client_ip in ("127.0.0.1", "::1"):
        expected_token = os.getenv("MOKA_ADMIN_TOKEN")
        if expected_token:
            return {"token": expected_token}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MoKa Admin Token is unconfigured."
            )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden: Auto-retrieval of token is only allowed from localhost."
    )


@app.get("/api/health")
async def health_endpoint():
    """
    Simple health check endpoint to verify connectivity to the cognitive layer.
    """
    return {"status": "success", "connected": True}

_CURRENT_MODEL_MODE = "local"


class ModelModeRequest(BaseModel):
    provider: str


@app.get("/api/model-mode", dependencies=[Depends(verify_moka_token)])
async def get_model_mode_endpoint():
    return {
        "status": "success",
        "provider": _CURRENT_MODEL_MODE,
        "cloud_model": os.getenv("AZURE_MODEL_NAME", "Phi-4-mini-instruct"),
        "local_chat_model": os.getenv("CHAT_LLM_MODEL", "qwen2.5:3b"),
        "local_agent_model": os.getenv("CALENDAR_LLM_MODEL", "qwen3.5:4b")
    }


@app.post("/api/model-mode", dependencies=[Depends(verify_moka_token)])
async def set_model_mode_endpoint(req: ModelModeRequest):
    global _CURRENT_MODEL_MODE
    clean_provider = req.provider.lower().strip()
    if clean_provider not in ["local", "cloud"]:
        raise HTTPException(status_code=400, detail="Provider must be 'local' or 'cloud'.")
    _CURRENT_MODEL_MODE = clean_provider
    return {
        "status": "success",
        "provider": _CURRENT_MODEL_MODE,
        "message": f"Active model provider updated to {_CURRENT_MODEL_MODE.upper()}"
    }


class RenameSessionRequest(BaseModel):
    title: str


@app.get("/api/history", dependencies=[Depends(verify_moka_token)])
async def get_chat_history_endpoint():
    """
    Returns all saved chat sessions and messages stored in the database.
    """
    sessions = chat_history_db.get_all_sessions()
    return {
        "status": "success",
        "sessions": sessions,
        "storage": "postgres" if chat_history_db.use_postgres else "sqlite"
    }


@app.get("/api/history/{session_id}", dependencies=[Depends(verify_moka_token)])
async def get_session_history_endpoint(session_id: str):
    session = chat_history_db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"status": "success", "session": session}


@app.post("/api/history", dependencies=[Depends(verify_moka_token)])
async def upsert_chat_history_endpoint(session: dict):
    success = chat_history_db.upsert_session(session)
    return {"status": "success" if success else "failed"}


@app.patch("/api/history/{session_id}", dependencies=[Depends(verify_moka_token)])
async def rename_session_history_endpoint(session_id: str, req: RenameSessionRequest):
    success = chat_history_db.rename_session(session_id, req.title)
    return {"status": "success" if success else "failed"}


@app.delete("/api/history/{session_id}", dependencies=[Depends(verify_moka_token)])
async def delete_session_history_endpoint(session_id: str):
    success = chat_history_db.delete_session(session_id)
    return {"status": "success" if success else "failed"}


@app.delete("/api/history", dependencies=[Depends(verify_moka_token)])
async def clear_all_history_endpoint():
    success = chat_history_db.clear_all_sessions()
    return {"status": "success" if success else "failed"}


@app.post("/api/history/sync-langsmith", dependencies=[Depends(verify_moka_token)])
async def sync_langsmith_history_endpoint():
    """
    Fetches historical conversation runs logged to LangSmith and stores them in the database.
    """
    count = chat_history_db.sync_from_langsmith(limit=50)
    sessions = chat_history_db.get_all_sessions()
    return {
        "status": "success",
        "synced_count": count,
        "sessions": sessions
    }


@app.post("/api/chat", dependencies=[Depends(verify_moka_token)])
async def chat_endpoint(req: ChatRequest):
    """
    Direct endpoint mapping user chat prompts to the cognitive layer.
    Automatically persists conversations to PostgreSQL / SQLite.
    """
    try:
        active_provider = (req.provider or _CURRENT_MODEL_MODE).lower().strip()
        
        # 1. Immediately persist user message to database
        chat_history_db.add_message(
            session_id=req.session_id,
            sender="user",
            text=req.message,
            model_mode=active_provider
        )

        # 2. Process cognitive response
        response_text = await process_user_intent(
            req.message,
            session_id=req.session_id,
            mute=True,
            provider=active_provider
        )

        # 3. Persist AI response to database
        if response_text:
            chat_history_db.add_message(
                session_id=req.session_id,
                sender="moka",
                text=response_text,
                model_mode=active_provider
            )

        if not req.mute and response_text:
            from actions.physical.speak import respond
            asyncio.create_task(respond(response_text, mute=False))

        return {
            "status": "success",
            "response": response_text,
            "provider": active_provider
        }
    except Exception as e:
        print(f"[Web API Error] Failed to process message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred in the cognitive layer: {str(e)}"
        )

from fastapi.responses import StreamingResponse
import json

@app.post("/api/chat/stream", dependencies=[Depends(verify_moka_token)])
async def chat_stream_endpoint(req: ChatRequest):
    """
    Direct SSE streaming endpoint pushing tokens token-by-token in real time.
    Automatically saves full stream to the database.
    """
    from core.routing.brain import stream_user_intent
    active_provider = (req.provider or _CURRENT_MODEL_MODE).lower().strip()

    # 1. Persist user message to database
    chat_history_db.add_message(
        session_id=req.session_id,
        sender="user",
        text=req.message,
        model_mode=active_provider
    )

    async def stream_and_record():
        accumulated_chunks = []
        async for chunk in stream_user_intent(
            req.message,
            session_id=req.session_id,
            mute=req.mute,
            provider=active_provider
        ):
            if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                try:
                    payload = json.loads(chunk[6:].strip())
                    if "token" in payload:
                        accumulated_chunks.append(payload["token"])
                except Exception:
                    pass
            yield chunk

        # 2. Persist complete streamed AI response to database
        full_reply = "".join(accumulated_chunks).strip()
        if full_reply:
            chat_history_db.add_message(
                session_id=req.session_id,
                sender="moka",
                text=full_reply,
                model_mode=active_provider
            )

    return StreamingResponse(
        stream_and_record(),
        media_type="text/event-stream"
    )

@app.post("/api/mute", dependencies=[Depends(verify_moka_token)])
async def mute_endpoint():
    """
    Instantly halts any ongoing speech playback on the speaker.
    """
    try:
        from actions.physical.speak import speaker
        speaker.interrupt()
        return {"status": "success", "message": "Speech interrupted successfully."}
    except Exception as e:
        print(f"[Web API Error] Failed to interrupt speech: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while interrupting speech: {str(e)}"
        )

# Mount Cozmo Autonomous Vision & Mission Control API
try:
    from core.modes.cozmo_api import cozmo_router, cozmo_ws_router
    app.include_router(cozmo_router)
    app.include_router(cozmo_ws_router)
    print("[Web API] Mounted Cozmo Autonomous Vision & Telemetry endpoints (/api/cozmo & /ws/cozmo).")
except Exception as e:
    print(f"[Web API Warning] Could not mount Cozmo endpoints: {e}")

if __name__ == "__main__":
    print("Launching MoKa Web API server on http://0.0.0.0:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)


