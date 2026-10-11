# schemas/chat_history_db.py
import os
import time
import sqlite3
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_DB_PATH = os.path.join(BACKEND_DIR, "data", "chat_history.db")

def _get_postgres_uri() -> str:
    raw_uri = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/cozmo_db")
    if raw_uri.endswith("/"):
        db_name = os.getenv("POSTGRES_DB") or "cozmo_db"
        return raw_uri + db_name
    return raw_uri


class ChatHistoryDatabase:
    """
    Manages persistent chat session and message storage across system reboots.
    Uses PostgreSQL (cozmo_db) as primary storage, with automatic fallback
    to local SQLite (backend/data/chat_history.db) if PostgreSQL is unavailable.
    Also supports automatic or manual syncing from LangSmith traces.
    """

    def __init__(self):
        self.use_postgres = False
        self.pg_uri = _get_postgres_uri()
        self.retention_days = int(os.getenv("CHAT_HISTORY_RETENTION_DAYS", "30"))
        self._init_db()

    def prune_expired_sessions(self, max_days: Optional[int] = None) -> int:
        """
        Automatically deletes conversations and associated messages older than max_days (default: 30 days).
        Ensures conversations older than a month are removed from persistent storage.
        """
        days = max_days if max_days is not None else self.retention_days
        cutoff_ms = int((time.time() - (days * 86400)) * 1000)
        deleted_count = 0

        if self.use_postgres:
            try:
                from psycopg import connect
                with connect(self.pg_uri, connect_timeout=2) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT id FROM chat_sessions WHERE updated_at < %s;", (cutoff_ms,))
                        expired_ids = [r[0] for r in cur.fetchall()]
                        if expired_ids:
                            deleted_count = len(expired_ids)
                            cur.execute("DELETE FROM chat_messages WHERE session_id = ANY(%s);", (expired_ids,))
                            cur.execute("DELETE FROM chat_sessions WHERE id = ANY(%s);", (expired_ids,))
                            print(f"[ChatHistoryDB] Auto-pruned {deleted_count} conversation(s) older than {days} days from PostgreSQL.")
                return deleted_count
            except Exception as e:
                print(f"[ChatHistoryDB Error] PostgreSQL prune_expired_sessions failed: {e}")

        try:
            with sqlite3.connect(SQLITE_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM chat_sessions WHERE updated_at < ?;", (cutoff_ms,))
                expired_ids = [r[0] for r in cur.fetchall()]
                if expired_ids:
                    deleted_count = len(expired_ids)
                    cur.executemany("DELETE FROM chat_messages WHERE session_id = ?;", [(i,) for i in expired_ids])
                    cur.executemany("DELETE FROM chat_sessions WHERE id = ?;", [(i,) for i in expired_ids])
                    conn.commit()
                    print(f"[ChatHistoryDB] Auto-pruned {deleted_count} conversation(s) older than {days} days from SQLite.")
            return deleted_count
        except Exception as sql_e:
            print(f"[ChatHistoryDB Error] SQLite prune_expired_sessions failed: {sql_e}")
            return 0

    def _init_db(self):
        """Initializes database schema in PostgreSQL or fallback SQLite and cleans expired sessions."""
        # 1. Try PostgreSQL
        try:
            from psycopg import connect
            with connect(self.pg_uri, connect_timeout=2) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS chat_sessions (
                            id VARCHAR(64) PRIMARY KEY,
                            title VARCHAR(255) NOT NULL,
                            model_mode VARCHAR(32) DEFAULT 'local',
                            created_at BIGINT NOT NULL,
                            updated_at BIGINT NOT NULL
                        );
                    """)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS chat_messages (
                            id VARCHAR(64) PRIMARY KEY,
                            session_id VARCHAR(64) NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                            sender VARCHAR(16) NOT NULL,
                            text TEXT NOT NULL,
                            timestamp VARCHAR(32) NOT NULL,
                            created_at BIGINT NOT NULL
                        );
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_chat_messages_session 
                        ON chat_messages(session_id, created_at);
                    """)
            self.use_postgres = True
            print(f"[ChatHistoryDB] Connected to PostgreSQL at {self.pg_uri}. Chat history is persistently stored in DB.")
            self.prune_expired_sessions()
            return
        except Exception as e:
            print(f"[ChatHistoryDB] PostgreSQL unavailable ({e}). Falling back to persistent local SQLite storage.")

        # 2. Fallback to SQLite
        os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
        try:
            with sqlite3.connect(SQLITE_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        model_mode TEXT DEFAULT 'local',
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        sender TEXT NOT NULL,
                        text TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
                    );
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_messages_session 
                    ON chat_messages(session_id, created_at);
                """)
                conn.commit()
            print(f"[ChatHistoryDB] Initialized persistent SQLite storage at {SQLITE_DB_PATH}.")
            self.prune_expired_sessions()
        except Exception as sql_e:
            print(f"[ChatHistoryDB Error] Failed to initialize SQLite database: {sql_e}")

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Returns all chat sessions with their messages, sorted by updatedAt descending, pruning any older than 30 days."""
        self.prune_expired_sessions()
        if self.use_postgres:
            try:
                from psycopg import connect
                with connect(self.pg_uri, connect_timeout=2) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT id, title, model_mode, created_at, updated_at 
                            FROM chat_sessions 
                            ORDER BY updated_at DESC;
                        """)
                        session_rows = cur.fetchall()

                        sessions = []
                        for s_id, title, model_mode, created_at, updated_at in session_rows:
                            cur.execute("""
                                SELECT id, sender, text, timestamp 
                                FROM chat_messages 
                                WHERE session_id = %s 
                                ORDER BY created_at ASC;
                            """, (s_id,))
                            msg_rows = cur.fetchall()
                            messages = [
                                {
                                    "id": m[0],
                                    "sender": m[1],
                                    "text": m[2],
                                    "timestamp": m[3]
                                }
                                for m in msg_rows
                            ]
                            sessions.append({
                                "id": s_id,
                                "title": title,
                                "modelMode": model_mode,
                                "createdAt": int(created_at),
                                "updatedAt": int(updated_at),
                                "messages": messages
                            })
                        return sessions
            except Exception as e:
                print(f"[ChatHistoryDB Error] PostgreSQL get_all_sessions failed ({e}), checking SQLite fallback.")

        # SQLite fallback
        try:
            with sqlite3.connect(SQLITE_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, title, model_mode, created_at, updated_at 
                    FROM chat_sessions 
                    ORDER BY updated_at DESC;
                """)
                session_rows = cur.fetchall()

                sessions = []
                for s_id, title, model_mode, created_at, updated_at in session_rows:
                    cur.execute("""
                        SELECT id, sender, text, timestamp 
                        FROM chat_messages 
                        WHERE session_id = ? 
                        ORDER BY created_at ASC;
                    """, (s_id,))
                    msg_rows = cur.fetchall()
                    messages = [
                        {
                            "id": m[0],
                            "sender": m[1],
                            "text": m[2],
                            "timestamp": m[3]
                        }
                        for m in msg_rows
                    ]
                    sessions.append({
                        "id": s_id,
                        "title": title,
                        "modelMode": model_mode,
                        "createdAt": int(created_at),
                        "updatedAt": int(updated_at),
                        "messages": messages
                    })
                return sessions
        except Exception as sql_e:
            print(f"[ChatHistoryDB Error] SQLite get_all_sessions failed: {sql_e}")
            return []

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Returns a single session with all its messages."""
        if self.use_postgres:
            try:
                from psycopg import connect
                with connect(self.pg_uri, connect_timeout=2) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT id, title, model_mode, created_at, updated_at 
                            FROM chat_sessions 
                            WHERE id = %s;
                        """, (session_id,))
                        s_row = cur.fetchone()
                        if not s_row:
                            return None

                        cur.execute("""
                            SELECT id, sender, text, timestamp 
                            FROM chat_messages 
                            WHERE session_id = %s 
                            ORDER BY created_at ASC;
                        """, (session_id,))
                        msg_rows = cur.fetchall()
                        return {
                            "id": s_row[0],
                            "title": s_row[1],
                            "modelMode": s_row[2],
                            "createdAt": int(s_row[3]),
                            "updatedAt": int(s_row[4]),
                            "messages": [
                                {
                                    "id": m[0],
                                    "sender": m[1],
                                    "text": m[2],
                                    "timestamp": m[3]
                                }
                                for m in msg_rows
                            ]
                        }
            except Exception as e:
                print(f"[ChatHistoryDB Error] PostgreSQL get_session failed ({e}), checking SQLite.")

        # SQLite fallback
        try:
            with sqlite3.connect(SQLITE_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, title, model_mode, created_at, updated_at 
                    FROM chat_sessions 
                    WHERE id = ?;
                """, (session_id,))
                s_row = cur.fetchone()
                if not s_row:
                    return None

                cur.execute("""
                    SELECT id, sender, text, timestamp 
                    FROM chat_messages 
                    WHERE session_id = ? 
                    ORDER BY created_at ASC;
                """, (session_id,))
                msg_rows = cur.fetchall()
                return {
                    "id": s_row[0],
                    "title": s_row[1],
                    "modelMode": s_row[2],
                    "createdAt": int(s_row[3]),
                    "updatedAt": int(s_row[4]),
                    "messages": [
                        {
                            "id": m[0],
                            "sender": m[1],
                            "text": m[2],
                            "timestamp": m[3]
                        }
                        for m in msg_rows
                    ]
                }
        except Exception as sql_e:
            print(f"[ChatHistoryDB Error] SQLite get_session failed: {sql_e}")
            return None

    def upsert_session(self, session: Dict[str, Any]) -> bool:
        """Upserts a full session and synchronizes all its messages."""
        session_id = session.get("id")
        title = session.get("title", "New Conversation")
        model_mode = session.get("modelMode", "local")
        created_at = session.get("createdAt", int(time.time() * 1000))
        updated_at = session.get("updatedAt", int(time.time() * 1000))
        messages = session.get("messages", [])

        if not session_id:
            return False

        if self.use_postgres:
            try:
                from psycopg import connect
                with connect(self.pg_uri, connect_timeout=2) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO chat_sessions (id, title, model_mode, created_at, updated_at) 
                            VALUES (%s, %s, %s, %s, %s) 
                            ON CONFLICT (id) DO UPDATE SET 
                                title = EXCLUDED.title,
                                model_mode = EXCLUDED.model_mode,
                                updated_at = EXCLUDED.updated_at;
                        """, (session_id, title, model_mode, created_at, updated_at))

                        # Upsert messages
                        now_ms = int(time.time() * 1000)
                        for idx, m in enumerate(messages):
                            m_id = m.get("id") or f"{session_id}_{idx}"
                            sender = m.get("sender", "user")
                            text = m.get("text", "")
                            ts = m.get("timestamp") or datetime.now().strftime("%I:%M %p")
                            m_created_at = created_at + idx if idx > 0 else created_at

                            cur.execute("""
                                INSERT INTO chat_messages (id, session_id, sender, text, timestamp, created_at) 
                                VALUES (%s, %s, %s, %s, %s, %s) 
                                ON CONFLICT (id) DO UPDATE SET 
                                    text = EXCLUDED.text,
                                    timestamp = EXCLUDED.timestamp;
                            """, (m_id, session_id, sender, text, ts, m_created_at))
                return True
            except Exception as e:
                print(f"[ChatHistoryDB Error] PostgreSQL upsert_session failed ({e}), falling back to SQLite.")

        # SQLite fallback
        try:
            with sqlite3.connect(SQLITE_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO chat_sessions (id, title, model_mode, created_at, updated_at) 
                    VALUES (?, ?, ?, ?, ?) 
                    ON CONFLICT(id) DO UPDATE SET 
                        title = excluded.title,
                        model_mode = excluded.model_mode,
                        updated_at = excluded.updated_at;
                """, (session_id, title, model_mode, created_at, updated_at))

                for idx, m in enumerate(messages):
                    m_id = m.get("id") or f"{session_id}_{idx}"
                    sender = m.get("sender", "user")
                    text = m.get("text", "")
                    ts = m.get("timestamp") or datetime.now().strftime("%I:%M %p")
                    m_created_at = created_at + idx if idx > 0 else created_at

                    cur.execute("""
                        INSERT INTO chat_messages (id, session_id, sender, text, timestamp, created_at) 
                        VALUES (?, ?, ?, ?, ?, ?) 
                        ON CONFLICT(id) DO UPDATE SET 
                            text = excluded.text,
                            timestamp = excluded.timestamp;
                    """, (m_id, session_id, sender, text, ts, m_created_at))
                conn.commit()
            return True
        except Exception as sql_e:
            print(f"[ChatHistoryDB Error] SQLite upsert_session failed: {sql_e}")
            return False

    def add_message(
        self,
        session_id: str,
        sender: str,
        text: str,
        timestamp: Optional[str] = None,
        message_id: Optional[str] = None,
        model_mode: str = "local",
        title: Optional[str] = None
    ) -> bool:
        """Appends a single message to a session and updates the session's timestamp and title."""
        now_ms = int(time.time() * 1000)
        m_id = message_id or str(uuid.uuid4())
        ts = timestamp or datetime.now().strftime("%I:%M %p")

        # Auto-generate title if session does not exist
        clean_text = text.strip()
        auto_title = title or (clean_text[:36] + "..." if len(clean_text) > 36 else clean_text or "New Conversation")

        if self.use_postgres:
            try:
                from psycopg import connect
                with connect(self.pg_uri, connect_timeout=2) as conn:
                    with conn.cursor() as cur:
                        # Ensure session exists or create it
                        cur.execute("""
                            INSERT INTO chat_sessions (id, title, model_mode, created_at, updated_at) 
                            VALUES (%s, %s, %s, %s, %s) 
                            ON CONFLICT (id) DO UPDATE SET 
                                updated_at = EXCLUDED.updated_at;
                        """, (session_id, auto_title, model_mode, now_ms, now_ms))

                        # Insert message
                        cur.execute("""
                            INSERT INTO chat_messages (id, session_id, sender, text, timestamp, created_at) 
                            VALUES (%s, %s, %s, %s, %s, %s) 
                            ON CONFLICT (id) DO UPDATE SET 
                                text = EXCLUDED.text,
                                timestamp = EXCLUDED.timestamp;
                        """, (m_id, session_id, sender, text, ts, now_ms))
                return True
            except Exception as e:
                print(f"[ChatHistoryDB Error] PostgreSQL add_message failed ({e}), checking SQLite.")

        # SQLite fallback
        try:
            with sqlite3.connect(SQLITE_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO chat_sessions (id, title, model_mode, created_at, updated_at) 
                    VALUES (?, ?, ?, ?, ?) 
                    ON CONFLICT(id) DO UPDATE SET 
                        updated_at = excluded.updated_at;
                """, (session_id, auto_title, model_mode, now_ms, now_ms))

                cur.execute("""
                    INSERT INTO chat_messages (id, session_id, sender, text, timestamp, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?) 
                    ON CONFLICT(id) DO UPDATE SET 
                        text = excluded.text,
                        timestamp = excluded.timestamp;
                """, (m_id, session_id, sender, text, ts, now_ms))
                conn.commit()
            return True
        except Exception as sql_e:
            print(f"[ChatHistoryDB Error] SQLite add_message failed: {sql_e}")
            return False

    def rename_session(self, session_id: str, new_title: str) -> bool:
        """Renames an existing session."""
        now_ms = int(time.time() * 1000)
        if self.use_postgres:
            try:
                from psycopg import connect
                with connect(self.pg_uri, connect_timeout=2) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE chat_sessions 
                            SET title = %s, updated_at = %s 
                            WHERE id = %s;
                        """, (new_title, now_ms, session_id))
                return True
            except Exception as e:
                print(f"[ChatHistoryDB Error] PostgreSQL rename_session failed: {e}")

        try:
            with sqlite3.connect(SQLITE_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE chat_sessions 
                    SET title = ?, updated_at = ? 
                    WHERE id = ?;
                """, (new_title, now_ms, session_id))
                conn.commit()
            return True
        except Exception as sql_e:
            print(f"[ChatHistoryDB Error] SQLite rename_session failed: {sql_e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session and its messages."""
        if self.use_postgres:
            try:
                from psycopg import connect
                with connect(self.pg_uri, connect_timeout=2) as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM chat_messages WHERE session_id = %s;", (session_id,))
                        cur.execute("DELETE FROM chat_sessions WHERE id = %s;", (session_id,))
                return True
            except Exception as e:
                print(f"[ChatHistoryDB Error] PostgreSQL delete_session failed: {e}")

        try:
            with sqlite3.connect(SQLITE_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM chat_messages WHERE session_id = ?;", (session_id,))
                cur.execute("DELETE FROM chat_sessions WHERE id = ?;", (session_id,))
                conn.commit()
            return True
        except Exception as sql_e:
            print(f"[ChatHistoryDB Error] SQLite delete_session failed: {sql_e}")
            return False

    def clear_all_sessions(self) -> bool:
        """Deletes all sessions and messages."""
        if self.use_postgres:
            try:
                from psycopg import connect
                with connect(self.pg_uri, connect_timeout=2) as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM chat_messages;")
                        cur.execute("DELETE FROM chat_sessions;")
                return True
            except Exception as e:
                print(f"[ChatHistoryDB Error] PostgreSQL clear_all_sessions failed: {e}")

        try:
            with sqlite3.connect(SQLITE_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM chat_messages;")
                cur.execute("DELETE FROM chat_sessions;")
                conn.commit()
            return True
        except Exception as sql_e:
            print(f"[ChatHistoryDB Error] SQLite clear_all_sessions failed: {sql_e}")
            return False

    def sync_from_langsmith(self, limit: int = 50) -> int:
        """
        Extracts historical conversation runs logged to LangSmith and
        restores them into the persistent database.
        Returns the count of synced sessions.
        """
        api_key = os.getenv("LANGCHAIN_API_KEY")
        project_name = os.getenv("LANGCHAIN_PROJECT", "Moka-AI-Assistant")

        if not api_key:
            print("[LangSmith Sync] Skipped: LANGCHAIN_API_KEY is not configured.")
            return 0

        try:
            from langsmith import Client
            client = Client()
            print(f"[LangSmith Sync] Querying runs for project '{project_name}' (limit={limit})...")
            
            runs = list(client.list_runs(project_name=project_name, is_root=True, limit=limit))
            imported_count = 0

            for run in runs:
                meta = getattr(run, "extra", {}).get("metadata", {}) if getattr(run, "extra", None) else {}
                sess_id = meta.get("session_id") or meta.get("thread_id")
                
                # Check output messages in LangGraph run
                outputs = getattr(run, "outputs", {}) or {}
                raw_messages = outputs.get("messages", [])

                if sess_id and raw_messages:
                    messages = []
                    first_user_text = ""

                    for idx, msg in enumerate(raw_messages):
                        if isinstance(msg, dict):
                            m_type = msg.get("type")
                            content = msg.get("content", "")
                        else:
                            m_type = getattr(msg, "type", "human")
                            content = getattr(msg, "content", "")

                        if not content:
                            continue

                        sender = "user" if m_type in ("human", "user") else "moka"
                        if sender == "user" and not first_user_text:
                            first_user_text = content

                        m_id = f"{sess_id}_ls_{idx}"
                        ts = datetime.now().strftime("%I:%M %p")
                        messages.append({
                            "id": m_id,
                            "sender": sender,
                            "text": content,
                            "timestamp": ts
                        })

                    if messages:
                        title = first_user_text[:36] + "..." if len(first_user_text) > 36 else (first_user_text or "LangSmith Session")
                        created_at = int(run.start_time.timestamp() * 1000) if getattr(run, "start_time", None) else int(time.time() * 1000)
                        updated_at = int(run.end_time.timestamp() * 1000) if getattr(run, "end_time", None) else created_at

                        # Enforce 30-day retention cutoff on synced runs
                        cutoff_ms = int((time.time() - (self.retention_days * 86400)) * 1000)
                        if updated_at < cutoff_ms:
                            continue

                        session_dict = {
                            "id": sess_id,
                            "title": title,
                            "modelMode": meta.get("provider", "local"),
                            "createdAt": created_at,
                            "updatedAt": updated_at,
                            "messages": messages
                        }
                        if self.upsert_session(session_dict):
                            imported_count += 1

            print(f"[LangSmith Sync] Successfully synced {imported_count} conversation sessions from LangSmith into database!")
            return imported_count
        except Exception as e:
            print(f"[LangSmith Sync Error] Failed to sync from LangSmith: {e}")
            return 0


# Global singleton instance
chat_history_db = ChatHistoryDatabase()
