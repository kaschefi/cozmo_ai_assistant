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

from fastapi import FastAPI, HTTPException, Security, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import uvicorn

# Import request models and unified brain router
from schemas.request_models import ChatRequest
from core.routing.brain import process_user_intent

app = FastAPI(
    title="MoKa Web API",
    description="Dedicated connection bridge for MoKa's cognitive layer, enabling chat interface access offline.",
    version="1.0.0"
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

async def verify_moka_token(token: str = Security(api_key_header)):
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
        response_text = await process_user_intent(req.message, session_id=req.session_id)
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

if __name__ == "__main__":
    print("Launching MoKa Web API server on http://127.0.0.1:5000...")
    uvicorn.run(app, host="127.0.0.1", port=5000)
