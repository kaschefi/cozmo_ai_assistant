# backend/core/services/semantic_etl_launcher.py
"""
Lifecycle manager for the local Semantic ETL Pipeline microservice.

When MoKa starts locally with SEMANTIC_ETL_URL targeting localhost/127.0.0.1
and the Semantic-ETL-Pipeline repository present alongside the workspace,
this launcher ensures the microservice is booted and cleaned up on exit.
"""

import atexit
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx
from dotenv import dotenv_values, load_dotenv

_SERVICES_DIR = os.path.dirname(os.path.abspath(__file__))
_CORE_DIR = os.path.dirname(_SERVICES_DIR)
_BACKEND_DIR = os.path.dirname(_CORE_DIR)
_WORKSPACE_DIR = os.path.dirname(_BACKEND_DIR)

_DEFAULT_ETL_DIR = os.path.abspath(os.path.join(_WORKSPACE_DIR, "..", "Semantic-ETL-Pipeline"))
_LOG_PATH = os.path.join(_BACKEND_DIR, "data", "semantic_etl.log")
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}

_lock = threading.Lock()
_managed_process: Optional[subprocess.Popen] = None
_managed_log_handle = None


def _is_autostart_enabled() -> bool:
    """Returns True unless Semantic ETL auto-start is explicitly disabled via env vars."""
    load_dotenv(os.path.join(_WORKSPACE_DIR, ".env"))
    if os.getenv("DISABLE_SEMANTIC_ETL_AUTOSTART", "").strip().lower() in ("1", "true", "yes"):
        return False
    return os.getenv("SEMANTIC_ETL_AUTOSTART", "true").strip().lower() not in ("0", "false", "no", "off")


def _resolve_local_target() -> Optional[Tuple[str, int, str]]:
    """Parses SEMANTIC_ETL_URL and returns (probe_host, port, base_url) only for local targets."""
    raw_url = os.getenv("SEMANTIC_ETL_URL", "http://localhost:8001").strip().rstrip("/")
    parsed = urlparse(raw_url)
    hostname = (parsed.hostname or "").lower()
    if hostname not in _LOCAL_HOSTS:
        return None
    port = parsed.port or (443 if parsed.scheme == "https" else 8001)
    probe_host = "127.0.0.1" if hostname == "0.0.0.0" else hostname
    return probe_host, port, raw_url


def _resolve_etl_project() -> Optional[Tuple[str, str]]:
    """Locates the sibling Semantic-ETL-Pipeline repo and its virtual environment Python."""
    etl_dir = os.path.abspath(os.getenv("SEMANTIC_ETL_DIR", _DEFAULT_ETL_DIR))
    if not os.path.isfile(os.path.join(etl_dir, "src", "main.py")):
        return None

    venv_candidates = [
        os.path.join(etl_dir, ".venv", "Scripts", "python.exe"),
        os.path.join(etl_dir, ".venv", "bin", "python"),
    ]
    python_exe = next((p for p in venv_candidates if os.path.isfile(p)), sys.executable)
    return etl_dir, python_exe


def _build_child_env() -> Dict[str, str]:
    """Builds a clean subprocess environment without MoKa .env or PYTHONPATH overrides."""
    child_env = os.environ.copy()
    for key in ("PYTHONPATH", "VIRTUAL_ENV", "PYTHONHOME", "PORT", "HOST"):
        child_env.pop(key, None)

    moka_env_file = os.path.join(_WORKSPACE_DIR, ".env")
    if os.path.isfile(moka_env_file):
        # Strip MoKa project keys so Semantic ETL's Pydantic BaseSettings reads its own .env.
        for key in dotenv_values(moka_env_file):
            child_env.pop(key, None)
    return child_env


def _is_port_listening(host: str, port: int, timeout: float = 0.4) -> bool:
    """Checks whether a TCP port is accepting local connections."""
    candidates = ["127.0.0.1"] if host in ("localhost", "127.0.0.1", "0.0.0.0") else [host]
    if host == "localhost":
        candidates.append("localhost")
    for candidate in candidates:
        try:
            with socket.create_connection((candidate, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def _close_log_handle_locked() -> None:
    global _managed_log_handle
    if _managed_log_handle is not None:
        try:
            _managed_log_handle.close()
        except Exception:
            pass
        _managed_log_handle = None


def _read_log_tail(max_lines: int = 8) -> str:
    try:
        with open(_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        return "\n".join(lines[-max_lines:]).strip()
    except Exception:
        return ""


def _wait_for_service_ready(
    probe_host: str,
    port: int,
    base_url: str,
    timeout_s: float,
    proc: subprocess.Popen,
) -> bool:
    """Polls until Semantic ETL responds healthy on /health or exits/times out."""
    deadline = time.monotonic() + timeout_s
    health_url = f"http://{probe_host}:{port}/health"
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            tail = _read_log_tail()
            detail = f"\n{tail}" if tail else ""
            print(f"[Semantic ETL Warning] Service exited early (code {proc.returncode}).{detail}")
            return False
        if _is_port_listening(probe_host, port, timeout=0.4):
            try:
                resp = httpx.get(health_url, timeout=1.5)
                if resp.status_code == 200:
                    print(f"[Semantic ETL] Microservice online & healthy at {base_url}")
                    return True
            except Exception:
                pass
        time.sleep(0.5)

    print(f"[Semantic ETL Warning] Timed out waiting for {base_url}/health after {timeout_s:.0f}s (log: {_LOG_PATH}).")
    return False


def ensure_semantic_etl_started(wait_ready: bool = False, timeout_s: float = 20.0) -> bool:
    """
    Ensures the local Semantic ETL Pipeline service is running and listening.

    Returns True when the service is already running or was successfully launched.
    If wait_ready is True, blocks up to timeout_s until /health returns HTTP 200.
    """
    global _managed_process, _managed_log_handle

    if not _is_autostart_enabled():
        return False

    target = _resolve_local_target()
    if target is None:
        return False
    probe_host, port, base_url = target

    proc_to_watch: Optional[subprocess.Popen] = None
    with _lock:
        if _managed_process is not None and _managed_process.poll() is None:
            proc_to_watch = _managed_process
        else:
            _close_log_handle_locked()
            _managed_process = None

            if _is_port_listening(probe_host, port):
                print(f"[Semantic ETL] Already listening at {base_url}. Reusing existing service.")
                return True

            project = _resolve_etl_project()
            if project is None:
                expected_dir = os.path.abspath(os.getenv("SEMANTIC_ETL_DIR", _DEFAULT_ETL_DIR))
                print(f"[Semantic ETL] Local repo not found at '{expected_dir}'; skipping auto-start.")
                return False

            etl_dir, python_exe = project
            os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
            log_handle = open(_LOG_PATH, "w", encoding="utf-8", errors="replace", buffering=1)

            cmd = [
                python_exe,
                "-m",
                "uvicorn",
                "src.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(port),
            ]
            popen_kwargs: Dict[str, Any] = {
                "cwd": etl_dir,
                "env": _build_child_env(),
                "stdin": subprocess.DEVNULL,
                "stdout": log_handle,
                "stderr": subprocess.STDOUT,
            }
            if os.name == "nt":
                popen_kwargs["creationflags"] = (
                    subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
            else:
                popen_kwargs["start_new_session"] = True

            try:
                _managed_process = subprocess.Popen(cmd, **popen_kwargs)
                _managed_log_handle = log_handle
                proc_to_watch = _managed_process
                print(f"[Semantic ETL] Starting microservice on {base_url} (PID {_managed_process.pid})...")
            except Exception as exc:
                log_handle.close()
                print(f"[Semantic ETL Warning] Failed to start microservice: {exc}")
                return False

    if proc_to_watch is None:
        return False

    if wait_ready:
        return _wait_for_service_ready(probe_host, port, base_url, timeout_s, proc_to_watch)

    threading.Thread(
        target=_wait_for_service_ready,
        args=(probe_host, port, base_url, timeout_s, proc_to_watch),
        daemon=True,
    ).start()
    return True


def start_semantic_etl_background() -> None:
    """Starts the Semantic ETL launcher check without blocking caller boot."""
    threading.Thread(
        target=ensure_semantic_etl_started,
        kwargs={"wait_ready": False},
        daemon=True,
    ).start()


def _terminate_process_tree(proc: subprocess.Popen) -> None:
    """Terminates a spawned process and any child processes (such as Windows venv shims)."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            pass
        if proc.poll() is None:
            proc.terminate()
        return

    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=4.0)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=2.0)
    except ProcessLookupError:
        pass


def stop_semantic_etl() -> None:
    """Terminates the Semantic ETL subprocess if this process spawned it."""
    global _managed_process
    with _lock:
        proc = _managed_process
        _managed_process = None
        if proc is not None and proc.poll() is None:
            print(f"[Semantic ETL] Stopping managed microservice (PID {proc.pid})...")
            try:
                _terminate_process_tree(proc)
            except Exception:
                pass
        _close_log_handle_locked()


atexit.register(stop_semantic_etl)
