# schemas/memory_db.py
import uuid
import os
from psycopg import connect
from core.routing.tool_vector_db import LangChainFastEmbedBridge
import numpy as np

DB_URI = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/cozmo_db")


class LongTermMemoryManager:
    def __init__(self):
        self.embedder = LangChainFastEmbedBridge()
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Creates a pure-text table. No pgvector extension required!"""
        with connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                            CREATE TABLE IF NOT EXISTS user_profile_memories
                            (
                                id
                                VARCHAR
                            (
                                36
                            ) PRIMARY KEY,
                                fact TEXT NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                );
                            """)

    def save_memory(self, fact: str):
        """Saves a unique personal fact to the database."""
        # Check if the fact or a conflicting one already exists before saving
        existing_facts = self._get_all_facts()

        if existing_facts:
            # Check semantic distance in Python
            new_embedding = np.array(self.embedder.embed_query(fact))

            for db_id, db_fact in existing_facts:
                db_embedding = np.array(self.embedder.embed_query(db_fact))

                # Calculate cosine similarity manually: (A . B) / (||A|| * ||B||)
                similarity = np.dot(new_embedding, db_embedding) / (
                            np.linalg.norm(new_embedding) * np.linalg.norm(db_embedding))

                # If similarity is very high (e.g., > 0.82), update/overwrite the old entry
                if similarity > 0.82:
                    with connect(DB_URI) as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE user_profile_memories SET fact = %s WHERE id = %s;",
                                (fact, db_id)
                            )
                    return

        # If it's completely new, insert it
        with connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO user_profile_memories (id, fact) VALUES (%s, %s);",
                    (str(uuid.uuid4()), fact)
                )

    def _get_all_facts(self):
        """Helper to safely grab raw facts for python-side distance computing."""
        with connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, fact FROM user_profile_memories;")
                return cur.fetchall()

    def retrieve_relevant_memories(self, user_query: str, limit: int = 3) -> list[str]:
        """Calculates relevance scoring inside Python using your FastEmbed model."""
        all_rows = self._get_all_facts()
        if not all_rows:
            return []

        query_embedding = np.array(self.embedder.embed_query(user_query))
        scored_memories = []

        for _, fact in all_rows:
            fact_embedding = np.array(self.embedder.embed_query(fact))
            similarity = np.dot(query_embedding, fact_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(fact_embedding))
            scored_memories.append((fact, similarity))

        # Sort by highest similarity score
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        return [mem[0] for mem in scored_memories[:limit]]


long_term_memory = LongTermMemoryManager()