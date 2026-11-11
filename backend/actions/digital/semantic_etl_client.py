# backend/actions/digital/semantic_etl_client.py
"""
Client for the Semantic ETL Pipeline & Grounded Knowledge Base Microservice.
Connects MoKa AI Assistant directly to the Semantic ETL Pipeline service
running at SEMANTIC_ETL_URL (defaults to http://localhost:8001).
Provides document upload, health checking, and context retrieval.
"""

import os
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

SEMANTIC_ETL_URL = os.getenv("SEMANTIC_ETL_URL", "http://localhost:8001").rstrip("/")
SEMANTIC_ETL_RETRIEVE_PATH = os.getenv("SEMANTIC_ETL_RETRIEVE_PATH", "/agent/query").strip()
if not SEMANTIC_ETL_RETRIEVE_PATH.startswith("/"):
    SEMANTIC_ETL_RETRIEVE_PATH = "/" + SEMANTIC_ETL_RETRIEVE_PATH


class SemanticETLError(Exception):
    """Raised when the Semantic ETL microservice returns an HTTP error or is unreachable."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _extract_error_detail(response: httpx.Response) -> str:
    """Extracts a concise upstream error message from JSON or raw response text."""
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return str(payload.get("detail") or payload.get("message") or response.text)
    except Exception:
        pass
    return response.text or f"HTTP {response.status_code}"


def _map_http_status_error(exc: httpx.HTTPStatusError, context: str) -> SemanticETLError:
    code = exc.response.status_code
    upstream_detail = _extract_error_detail(exc.response)
    mapped_code = code if 400 <= code < 500 else 502
    return SemanticETLError(mapped_code, f"{context} ({code}): {upstream_detail}")


def _map_request_error(exc: Exception) -> SemanticETLError:
    return SemanticETLError(
        503,
        f"Semantic ETL service is unreachable at {SEMANTIC_ETL_URL}: {exc}",
    )


def _build_upload_payload(
    file_bytes: bytes,
    filename: Optional[str],
    namespace: str,
    content_type: Optional[str] = None,
) -> tuple[str, Dict[str, Any], Dict[str, str]]:
    url = f"{SEMANTIC_ETL_URL}/pipeline/jobs/upload"
    safe_filename = filename or "document"
    safe_content_type = content_type or "application/octet-stream"
    files = {"file": (safe_filename, file_bytes, safe_content_type)}
    data = {"namespace": namespace or "documents"}
    return url, files, data


def is_semantic_etl_healthy() -> bool:
    """Checks whether the Semantic ETL Pipeline service is operational."""
    try:
        with httpx.Client(timeout=1.5) as client:
            resp = client.get(f"{SEMANTIC_ETL_URL}/health")
            return resp.status_code == 200 and resp.json().get("status") == "healthy"
    except Exception:
        return False


def get_health_status() -> Dict[str, Any]:
    """Retrieves detailed infrastructure health from the Semantic ETL service."""
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{SEMANTIC_ETL_URL}/health")
            if resp.status_code == 200:
                return resp.json()
            return {"status": "unhealthy", "code": resp.status_code, "detail": resp.text}
    except Exception as e:
        return {"status": "offline", "error": str(e), "target_url": SEMANTIC_ETL_URL}


async def async_get_health_status() -> Dict[str, Any]:
    """Non-blocking infrastructure health check for FastAPI async endpoints."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{SEMANTIC_ETL_URL}/health")
            if resp.status_code == 200:
                return resp.json()
            return {"status": "unhealthy", "code": resp.status_code, "detail": resp.text}
    except Exception as e:
        return {"status": "offline", "error": str(e), "target_url": SEMANTIC_ETL_URL}


def upload_document_bytes(
    file_bytes: bytes,
    filename: str,
    namespace: str = "documents",
    content_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submits a document file to the Semantic ETL background job queue.
    Returns HTTP 202 job tracking details (job_id, status, progress).
    Raises SemanticETLError on upstream HTTP or connection failures.
    """
    url, files, data = _build_upload_payload(file_bytes, filename, namespace, content_type)

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, files=files, data=data)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise _map_http_status_error(e, "Document upload failed") from e
    except Exception as e:
        raise _map_request_error(e) from e


async def async_upload_document_bytes(
    file_bytes: bytes,
    filename: str,
    namespace: str = "documents",
    content_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Non-blocking document upload submission for FastAPI async endpoints."""
    url, files, data = _build_upload_payload(file_bytes, filename, namespace, content_type)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, files=files, data=data)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise _map_http_status_error(e, "Document upload failed") from e
    except Exception as e:
        raise _map_request_error(e) from e


def get_job_status(job_id: str) -> Dict[str, Any]:
    """Queries the real-time background processing state for a job_id."""
    url = f"{SEMANTIC_ETL_URL}/pipeline/jobs/{job_id}"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise _map_http_status_error(e, "Job status query failed") from e
    except Exception as e:
        raise _map_request_error(e) from e


async def async_get_job_status(job_id: str) -> Dict[str, Any]:
    """Non-blocking job status query for FastAPI async endpoints."""
    url = f"{SEMANTIC_ETL_URL}/pipeline/jobs/{job_id}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise _map_http_status_error(e, "Job status query failed") from e
    except Exception as e:
        raise _map_request_error(e) from e


def retrieve_document_context(
    query: str,
    namespace: str = "documents",
    category_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieves grounded context blocks and structured sources from the
    Semantic Knowledge Base for a user query.
    Returns:
        dict: {"answer": str, "sources": list[dict], "has_context": bool}
    """
    res = query_semantic_rag(query, namespace=namespace, category_filter=category_filter)
    sources = res.get("sources", [])
    has_context = bool(sources and len(sources) > 0)
    return {
        "answer": res.get("answer", ""),
        "sources": sources,
        "has_context": has_context
    }


def query_semantic_rag(
    question: str,
    namespace: str = "documents",
    category_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends a query to the Semantic ETL retrieval/RAG endpoint (configurable via SEMANTIC_ETL_RETRIEVE_PATH).
    Returns retrieved sources (and synthesized answer if using /agent/query).
    """
    url = f"{SEMANTIC_ETL_URL}{SEMANTIC_ETL_RETRIEVE_PATH}"
    payload = {
        "question": question,
        "namespace": namespace,
        "category_filter": category_filter
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        return {
            "answer": f"Error from Semantic RAG service: {e.response.status_code} - {e.response.text}",
            "sources": []
        }
    except Exception as e:
        return {
            "answer": f"Could not reach Semantic RAG service at {SEMANTIC_ETL_URL}. Please ensure the microservice is running: {e}",
            "sources": []
        }

