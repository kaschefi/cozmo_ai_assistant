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
from schemas.request_models import ChatRequest
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

        # 3. Warm up Kokoro ONNX speaker model
        from actions.physical.speak import speaker
        await loop.run_in_executor(None, speaker.warmup)

        print("[MoKa Warmup] All cognitive models pre-warmed & active in RAM!")
    except Exception as e:
        print(f"[MoKa Warmup] Notice during background pre-warming: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Launch background pre-warming without blocking server boot
    asyncio.create_task(_background_warmup())
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

@app.post("/api/chat", dependencies=[Depends(verify_moka_token)])
async def chat_endpoint(req: ChatRequest):
    """
    Direct endpoint mapping user chat prompts to the cognitive layer.
    """
    try:
        response_text = await process_user_intent(req.message, session_id=req.session_id, mute=req.mute)
        return {
            "status": "success",
            "response": response_text
        }
    except Exception as e:
        print(f"[Web API Error] Failed to process message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred in the cognitive layer: {str(e)}"
        )

from fastapi.responses import StreamingResponse

@app.post("/api/chat/stream", dependencies=[Depends(verify_moka_token)])
async def chat_stream_endpoint(req: ChatRequest):
    """
    Direct SSE streaming endpoint pushing tokens token-by-token in real time.
    """
    from core.routing.brain import stream_user_intent
    return StreamingResponse(
        stream_user_intent(req.message, session_id=req.session_id, mute=req.mute),
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

if __name__ == "__main__":
    print("Launching MoKa Web API server on http://127.0.0.1:8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
