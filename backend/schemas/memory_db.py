# schemas/memory_db.py
import os
import sys
import json
import re
import threading
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM0_DIR = os.path.join(BACKEND_DIR, "data", ".mem0")
os.environ["MEM0_DIR"] = MEM0_DIR
os.environ["MEM0_TELEMETRY"] = "false"
os.makedirs(MEM0_DIR, exist_ok=True)

from mem0 import Memory
from langchain_core.messages import SystemMessage, HumanMessage


def _clean_json_response(raw_text: str) -> Optional[dict]:
    """Robustly extracts and parses a JSON object from LLM response text."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return None


class LongTermMemoryManager:
    """
    Production-grade Long-Term Memory Manager for Moka Assistant powered by Mem0 & pgvector.
    Features:
      - PostgreSQL pgvector storage on Neon (concurrent multi-process safe, no Windows file locking).
      - 100% local ONNX embedding generation (FastEmbed BAAI/bge-small-en-v1.5).
      - Automated contradiction detection, smart updates, and explicit deletions.
      - Seamless Local Ollama / Azure Cloud toggle support.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._client: Optional[Memory] = None

    @property
    def client(self) -> Memory:
        if self._client is None:
            with self._lock:
                if self._client is None:
                    config = self._build_config()
                    self._client = Memory.from_config(config)
        return self._client

    def _build_config(self) -> dict:
        selected_provider = os.getenv("LLM_PROVIDER", "OLLAMA").upper().strip()
        db_uri = os.getenv("DATABASE_URL")

        if db_uri:
            # Production: Concurrent-safe Neon PostgreSQL pgvector
            vector_store_config = {
                "provider": "pgvector",
                "config": {
                    "connection_string": db_uri,
                    "collection_name": "moka_user_memories",
                    "embedding_model_dims": 384
                }
            }
        else:
            # Fallback to local Qdrant if DATABASE_URL is not set
            vector_store_path = os.path.join(BACKEND_DIR, "data", "mem0_qdrant")
            os.makedirs(vector_store_path, exist_ok=True)
            vector_store_config = {
                "provider": "qdrant",
                "config": {
                    "path": vector_store_path,
                    "embedding_model_dims": 384
                }
            }

        embedder_config = {
            "provider": "fastembed",
            "config": {
                "model": "BAAI/bge-small-en-v1.5",
                "embedding_dims": 384
            }
        }

        if selected_provider in ["CLOUD", "AZURE"]:
            deployment_name = (
                os.getenv("AZURE_ROUTER_DEPLOYMENT")
                or os.getenv("AZURE_MODEL_NAME")
                or os.getenv("AZURE_DEPLOYMENT_NAME")
                or "Phi-4-mini-instruct"
            )
            endpoint = (
                os.getenv("AZURE_SERVICES_ENDPOINT")
                or os.getenv("AZURE_OPENAI_ENDPOINT")
                or "https://moka101.services.ai.azure.com/openai/v1"
            )
            api_key = os.getenv("AZURE_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
            llm_config = {
                "provider": "azure_openai",
                "config": {
                    "model": deployment_name,
                    "azure_deployment": deployment_name,
                    "azure_endpoint": endpoint,
                    "api_key": api_key,
                    "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
                }
            }
        else:
            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            ollama_model = os.getenv("MEMORY_LLM_MODEL", os.getenv("ROUTER_LLM_MODEL", "qwen2.5:3b"))
            llm_config = {
                "provider": "ollama",
                "config": {
                    "model": ollama_model,
                    "ollama_base_url": ollama_url
                }
            }

        custom_instructions = (
            "Extract permanent personal facts about the user from the conversation, including:\n"
            "1. Identity & Name (e.g. user's name, nicknames).\n"
            "2. Profession, occupation, student status, major, or field of study.\n"
            "3. Persistent preferences, tools, coding languages, hobbies, sports teams, or interests.\n"
            "4. Location, background, and persistent relationships.\n"
            "Ignore temporary details like current weather, current time, and appointment times.\n"
            "Always formulate extracted memories as clear, factual statements starting with 'User'."
        )

        return {
            "vector_store": vector_store_config,
            "embedder": embedder_config,
            "llm": llm_config,
            "custom_instructions": custom_instructions,
            "version": "v1.1"
        }

    def retrieve_relevant_memories(self, user_query: str, user_id: str = "cozmo_owner", limit: int = 3) -> List[str]:
        """Hybrid search for facts relevant to the user query."""
        try:
            results = self.client.search(user_query, filters={"user_id": user_id}, limit=limit)
            return [r["memory"] for r in results.get("results", [])]
        except Exception as e:
            print(f"[LongTermMemoryManager] Error during retrieve_relevant_memories: {e}")
            return []

    def get_all_memories(self, user_id: str = "cozmo_owner") -> List[str]:
        """Retrieves all permanent profile facts known about the user."""
        try:
            all_mems = self.client.get_all(filters={"user_id": user_id})
            return [m["memory"] for m in all_mems.get("results", [])]
        except Exception as e:
            print(f"[LongTermMemoryManager] Error during get_all_memories: {e}")
            return []

    def get_all_memories_with_details(self, user_id: str = "cozmo_owner") -> List[Dict[str, Any]]:
        """Retrieves memory records including their unique IDs for reconciliation."""
        try:
            all_mems = self.client.get_all(filters={"user_id": user_id})
            return all_mems.get("results", [])
        except Exception as e:
            print(f"[LongTermMemoryManager] Error during get_all_memories_with_details: {e}")
            return []

    def _get_all_memories_for_user(self, user_id: str = "cozmo_owner") -> list:
        """Legacy helper compatibility returning tuple rows (id, fact, embedding, category)."""
        mems = self.get_all_memories(user_id=user_id)
        return [(f"mem_{i}", fact, [], "general") for i, fact in enumerate(mems)]

    def _reconcile_dialogue(self, dialogue_text: str, user_id: str = "cozmo_owner") -> bool:
        """
        Compares recent dialogue against existing memories.
        Detects contradictions/corrections (UPDATE), explicit forget requests (DELETE),
        and new traits (ADD). Executes them against Mem0.
        Returns True if operations were performed, False if dialogue was ignored/unrelated.
        """
        existing_records = self.get_all_memories_with_details(user_id=user_id)
        if not existing_records:
            return False

        existing_clean = [{"id": r["id"], "text": r["memory"]} for r in existing_records]

        system_prompt = f"""You are a Memory Reconciliation Engine. Your job is to update, delete, or add long-term memory facts based on conversation.

### SCHEMA:
- "UPDATE": When an existing memory is contradicted, replaced, or corrected with a new value. Requires "id" and "text" (starting with "User").
- "DELETE": When the user asks to forget or remove a memory without a new replacement. Requires "id".
- "ADD": When the user reveals a NEW personal trait/preference not covered by existing memories. Requires "text" (starting with "User").
- If existing memories are NOT mentioned, leave them alone. Do NOT include them in operations.
- If conversation contains no personal facts (e.g. weather, greetings), output empty operations [].

### EXAMPLES:
Existing: [{{"id": "m1", "text": "User's name is Bob"}}]
Conversation:
User: My name is not Bob, forget that, my name is Mohammad!
Output:
{{"operations": [{{"op": "UPDATE", "id": "m1", "text": "User's name is Mohammad"}}]}}

Existing: [{{"id": "m1", "text": "User lives in Paris"}}]
Conversation:
User: I moved to London last week.
Output:
{{"operations": [{{"op": "UPDATE", "id": "m1", "text": "User lives in London"}}]}}

Existing: [{{"id": "m1", "text": "User likes coffee"}}]
Conversation:
User: Please forget that I like coffee, I quit it.
Output:
{{"operations": [{{"op": "DELETE", "id": "m1"}}]}}

Existing: [{{"id": "m1", "text": "User's name is Alice"}}]
Conversation:
User: I also have a dog named Max.
Output:
{{"operations": [{{"op": "ADD", "text": "User has a dog named Max"}}]}}

Existing: [{{"id": "m1", "text": "User's name is Alice"}}]
Conversation:
User: What time is it?
Output:
{{"operations": []}}

### CURRENT TASK:
Existing Memories:
{json.dumps(existing_clean, indent=2)}

Recent Conversation:
{dialogue_text}

Output JSON:"""

        try:
            from core.routing.llm_factory import get_llm
            reconciliation_llm = get_llm("MEMORY_LLM_MODEL", "qwen2.5:3b", temperature=0.0)

            resp = reconciliation_llm.invoke([
                SystemMessage(content="You are a precise JSON memory engine. Respond ONLY with valid JSON matching the schema."),
                HumanMessage(content=system_prompt)
            ])

            parsed = _clean_json_response(resp.content)
            if not parsed or "operations" not in parsed:
                return False

            operations = parsed.get("operations", [])
            if not operations:
                return False

            for op in operations:
                action = op.get("op", "").upper()
                mem_id = op.get("id")
                text = op.get("text", "")

                if action == "UPDATE" and mem_id and text:
                    print(f"[LongTermMemoryManager] Updating memory {mem_id} -> '{text}'")
                    self.client.update(memory_id=mem_id, text=text)
                elif action == "DELETE" and mem_id:
                    print(f"[LongTermMemoryManager] Deleting memory {mem_id}")
                    self.client.delete(memory_id=mem_id)
                elif action == "ADD" and text:
                    print(f"[LongTermMemoryManager] Adding memory -> '{text}'")
                    self.client.add(text, user_id=user_id, infer=False)

            return True

        except Exception as e:
            print(f"[LongTermMemoryManager] Error during reconciliation: {e}")
            return False

    def add_dialogue(self, messages: Any, user_id: str = "cozmo_owner") -> Any:
        """
        Extracts permanent profile traits and reconciles memory conflicts from conversational turns.
        Automatically updates contradictions, forgets deleted facts, and inserts new traits.
        """
        try:
            # 1. Format dialogue text for reconciliation
            if isinstance(messages, str):
                dialogue_text = messages
                payload_messages = [{"role": "user", "content": messages}]
            elif isinstance(messages, list):
                dialogue_lines = []
                payload_messages = []
                for m in messages:
                    if isinstance(m, dict):
                        role = m.get("role", "user")
                        content = m.get("content", "")
                    else:
                        role = "user" if getattr(m, "type", "") == "human" or getattr(m, "__class__", "").__name__ == "HumanMessage" else "assistant"
                        content = getattr(m, "content", str(m))
                    dialogue_lines.append(f"{role.capitalize()}: {content}")
                    payload_messages.append({"role": role, "content": content})
                dialogue_text = "\n".join(dialogue_lines)
            else:
                dialogue_text = str(messages)
                payload_messages = [{"role": "user", "content": dialogue_text}]

            # 2. Run reconciliation if user already has saved memories
            reconciled = self._reconcile_dialogue(dialogue_text, user_id=user_id)

            # 3. If no existing memories were present, run standard initial extraction
            if not reconciled:
                existing = self.get_all_memories(user_id=user_id)
                if not existing:
                    return self.client.add(payload_messages, user_id=user_id)

            return True

        except Exception as e:
            print(f"[LongTermMemoryManager] Error during add_dialogue: {e}")
            return None

    def save_memory(self, fact: str, category: str = None, user_id: str = "cozmo_owner") -> Any:
        """Directly inserts a single verified fact into long-term memory."""
        try:
            return self.client.add(fact, user_id=user_id, infer=False)
        except Exception as e:
            print(f"[LongTermMemoryManager] Error during save_memory: {e}")
            return None

    def update_memory(self, memory_id: str, new_text: str) -> bool:
        """Updates a specific memory entry by id."""
        try:
            self.client.update(memory_id=memory_id, text=new_text)
            return True
        except Exception as e:
            print(f"[LongTermMemoryManager] Error during update_memory: {e}")
            return False

    def delete_memory(self, memory_id: str) -> bool:
        """Deletes a specific memory entry by id."""
        try:
            self.client.delete(memory_id)
            return True
        except Exception as e:
            print(f"[LongTermMemoryManager] Error during delete_memory: {e}")
            return False

    def reset_user_memory(self, user_id: str = "cozmo_owner") -> bool:
        """Removes all stored memories for a user."""
        try:
            self.client.delete_all(user_id=user_id)
            return True
        except Exception as e:
            print(f"[LongTermMemoryManager] Error during reset_user_memory: {e}")
            return False


long_term_memory = LongTermMemoryManager()
