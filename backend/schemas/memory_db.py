# schemas/memory_db.py
import uuid
import os
from dotenv import load_dotenv
from psycopg import connect
from core.routing.tool_vector_db import LangChainFastEmbedBridge
import numpy as np

load_dotenv()

DB_URI = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/cozmo_db")


class LongTermMemoryManager:
    UNIQUE_CATEGORIES = {
        "user_name",
        "user_occupation",
        "favorite_sports_team",
        "favorite_programming_language",
        "user_location"
    }

    def __init__(self):
        self.embedder = LangChainFastEmbedBridge()
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Creates the user_profile_memories table with category support and runs safe DDL migrations and a self-healing sweeper."""
        with connect(DB_URI) as conn:
            with connect(DB_URI) as conn:
                with conn.cursor() as cur:
                    # 1. Create table if not exists with correct schema
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS user_profile_memories (
                            id VARCHAR(36) PRIMARY KEY,
                            user_id VARCHAR(50) NOT NULL DEFAULT 'cozmo_owner',
                            fact TEXT NOT NULL,
                            embedding REAL[] NOT NULL,
                            category VARCHAR(50),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # 2. Schema migration: check and add user_id column
                    cur.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='user_profile_memories' AND column_name='user_id';
                    """)
                    if not cur.fetchone():
                        print("Migrating database user_profile_memories: adding user_id column...")
                        cur.execute("ALTER TABLE user_profile_memories ADD COLUMN user_id VARCHAR(50) NOT NULL DEFAULT 'cozmo_owner';")
                    
                    # 3. Schema migration: check and add updated_at column
                    cur.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='user_profile_memories' AND column_name='updated_at';
                    """)
                    if not cur.fetchone():
                        cur.execute("ALTER TABLE user_profile_memories ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
                    
                    # 4. Schema migration: check and add category column
                    cur.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='user_profile_memories' AND column_name='category';
                    """)
                    if not cur.fetchone():
                        print("Migrating database user_profile_memories: adding category VARCHAR(50) column...")
                        cur.execute("ALTER TABLE user_profile_memories ADD COLUMN category VARCHAR(50);")
                    
                    # 5. Schema migration: check and add embedding column
                    cur.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='user_profile_memories' AND column_name='embedding';
                    """)
                    if not cur.fetchone():
                        print("Migrating database user_profile_memories: adding embedding REAL[] column...")
                        cur.execute("ALTER TABLE user_profile_memories ADD COLUMN embedding REAL[];")
                        
                        # Generate embeddings for legacy text-only rows on the fly
                        cur.execute("SELECT id, fact FROM user_profile_memories WHERE embedding IS NULL;")
                        legacy_rows = cur.fetchall()
                        if legacy_rows:
                            print(f"Retroactively embedding {len(legacy_rows)} legacy personal facts...")
                            for db_id, fact in legacy_rows:
                                embedding_vector = self.embedder.embed_query(fact)
                                cur.execute(
                                    "UPDATE user_profile_memories SET embedding = %s WHERE id = %s;",
                                    (embedding_vector, db_id)
                               )
                        
                        # Apply NOT NULL constraint after migration completes
                        cur.execute("ALTER TABLE user_profile_memories ALTER COLUMN embedding SET NOT NULL;")

                    # 6. Database Cleanup & Tagging Sweep (Self-Healing Repair)
                    # Classify any untagged rows based on text matching
                    cur.execute("SELECT id, fact FROM user_profile_memories WHERE category IS NULL;")
                    untagged_rows = cur.fetchall()
                    if untagged_rows:
                        print("Classifying legacy database facts to repair entities...")
                        for db_id, fact in untagged_rows:
                            fact_lower = fact.lower()
                            category = None
                            if "name is" in fact_lower or "shares their name" in fact_lower or "provided their name" in fact_lower or "name openly" in fact_lower:
                                category = "user_name"
                            elif "favorite sports team" in fact_lower or "favorite team" in fact_lower:
                                category = "favorite_sports_team"
                            elif "favorite programming language" in fact_lower:
                                category = "favorite_programming_language"
                            elif "is a student" in fact_lower or "studying" in fact_lower:
                                category = "user_occupation"
                            elif "is from" in fact_lower or "comes from" in fact_lower:
                                category = "user_location"
                            
                            if category:
                                cur.execute(
                                    "UPDATE user_profile_memories SET category = %s WHERE id = %s;",
                                    (category, db_id)
                                )
                    
                    # Dedup sweep: For each unique single-value category, keep only the latest one and delete the rest!
                    for cat in self.UNIQUE_CATEGORIES:
                        cur.execute(
                            """
                            SELECT id, fact FROM user_profile_memories 
                            WHERE category = %s 
                            ORDER BY created_at DESC, updated_at DESC;
                            """,
                            (cat,)
                        )
                        cat_rows = cur.fetchall()
                        if len(cat_rows) > 1:
                            # Keep the first (latest), delete the rest
                            ids_to_delete = [r[0] for r in cat_rows[1:]]
                            print(f"Self-Healing: Cleaning up {len(ids_to_delete)} duplicate database entries for category '{cat}'...")
                            for r in cat_rows[1:]:
                                print(f"   Deleting duplicate: '{r[1]}'")
                            cur.execute(
                                "DELETE FROM user_profile_memories WHERE id = ANY(%s);",
                                (ids_to_delete,)
                            )

    def save_memory(self, fact: str, category: str = None, user_id: str = "cozmo_owner"):
        """Saves a unique personal fact to the database. Overwrites semantically conflicting or matching category facts."""
        new_embedding = np.array(self.embedder.embed_query(fact))

        # 1. Entity Resolution: Overwrite directly if it belongs to a single-value unique category
        if category and category in self.UNIQUE_CATEGORIES:
            with connect(DB_URI) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM user_profile_memories WHERE user_id = %s AND category = %s;",
                        (user_id, category)
                    )
                    row = cur.fetchone()
                    if row:
                        db_id = row[0]
                        cur.execute(
                            """
                            UPDATE user_profile_memories 
                            SET fact = %s, embedding = %s, updated_at = CURRENT_TIMESTAMP 
                            WHERE id = %s;
                            """,
                            (fact, new_embedding.tolist(), db_id)
                        )
                        return

        # 2. Vector Cosine Similarity checking for general or fallback memories
        existing_memories = self._get_all_memories_for_user(user_id)

        if existing_memories:
            for db_id, db_fact, db_embedding_list, db_category in existing_memories:
                # If they belong to different unique categories, they are not semantic duplicates
                if category and db_category and category != db_category:
                    continue

                db_embedding = np.array(db_embedding_list)

                # Vectorized Cosine Similarity: (A . B) / (||A|| * ||B||)
                dot_prod = np.dot(new_embedding, db_embedding)
                norm_new = np.linalg.norm(new_embedding)
                norm_db = np.linalg.norm(db_embedding)

                similarity = dot_prod / (norm_new * norm_db) if (norm_new > 0 and norm_db > 0) else 0.0

                # If similarity is very high (e.g. > 0.82), update/overwrite the old entry
                if similarity > 0.82:
                    with connect(DB_URI) as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                UPDATE user_profile_memories 
                                SET fact = %s, embedding = %s, category = %s, updated_at = CURRENT_TIMESTAMP 
                                WHERE id = %s;
                                """,
                                (fact, new_embedding.tolist(), category, db_id)
                            )
                    return

        # If it's a completely new fact, insert it
        with connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_profile_memories (id, user_id, fact, embedding, category) 
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (str(uuid.uuid4()), user_id, fact, new_embedding.tolist(), category)
                )

    def _get_all_memories_for_user(self, user_id: str):
        """Helper to retrieve all raw facts, precomputed vectors, and categories for a user."""
        with connect(DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, fact, embedding, category FROM user_profile_memories WHERE user_id = %s;", (user_id,))
                return cur.fetchall()

    def retrieve_relevant_memories(self, user_query: str, user_id: str = "cozmo_owner", limit: int = 3) -> list[str]:
        """Calculates relevance scoring inside Python using precomputed Postgres vectors and NumPy.
        Always retrieves core profile memories (UNIQUE_CATEGORIES) directly to guarantee consistency,
        while using semantic similarity search for general preferences.
        """
        all_rows = self._get_all_memories_for_user(user_id)
        if not all_rows:
            return []

        core_memories = []
        general_memories_rows = []
        for _, fact, db_embedding_list, category in all_rows:
            if category in self.UNIQUE_CATEGORIES:
                core_memories.append(fact)
            else:
                general_memories_rows.append((fact, db_embedding_list))

        scored_general = []
        if general_memories_rows:
            query_embedding = np.array(self.embedder.embed_query(user_query))
            norm_query = np.linalg.norm(query_embedding)
            if norm_query > 0:
                for fact, db_embedding_list in general_memories_rows:
                    db_embedding = np.array(db_embedding_list)
                    norm_db = np.linalg.norm(db_embedding)
                    if norm_db == 0:
                        continue
                    similarity = np.dot(query_embedding, db_embedding) / (norm_query * norm_db)
                    scored_general.append((fact, similarity))
                
                # Sort by highest similarity score
                scored_general.sort(key=lambda x: x[1], reverse=True)

        top_general = [mem[0] for mem in scored_general[:limit]]

        # Combine core profile memories and relevant general memories, deduplicating them
        combined = []
        seen = set()
        for m in (core_memories + top_general):
            if m not in seen:
                combined.append(m)
                seen.add(m)
        return combined


long_term_memory = LongTermMemoryManager()