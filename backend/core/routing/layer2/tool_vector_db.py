# core/routing/layer2/tool_vector_db.py
import os
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import json
import threading
from typing import List, Dict, Any, Optional, Literal
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from core.routing.encoder import get_shared_encoder
import numpy as np

ToolSourceType = Literal["native", "mcp_dormant", "mcp_active"]


class LangChainFastEmbedBridge:
    """Bridges Layer 1 encoder to LangChain's vector store interface."""

    @property
    def encoder(self):
        return get_shared_encoder()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.encoder(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.encoder([text])[0]

    def __call__(self, text: str) -> list[float]:
        """Makes the instance callable, routing directly to embed_query."""
        return self.embed_query(text)


class ToolVectorRegistry:
    def __init__(self):
        self.embeddings = LangChainFastEmbedBridge()
        self.db: Optional[FAISS] = None
        self._lock = threading.RLock()
        self._tools_source: List[Document] = []
        self._tools_embeddings: List[List[float]] = []

    def register_tool_schema(
        self,
        name: str,
        description: str,
        source_type: ToolSourceType = "native",
        server_pack_id: Optional[str] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        is_mutating: bool = False
    ):
        """Adds a tool definition to the raw index source."""
        with self._lock:
            doc = Document(
                page_content=description,
                metadata={
                    "tool_name": name,
                    "source_type": source_type,
                    "server_pack_id": server_pack_id,
                    "input_schema": input_schema or {},
                    "is_mutating": is_mutating
                }
            )
            self._tools_source.append(doc)
            # Embeddings will be computed/synced during build_index()

    def load_dormant_catalog(self, catalog_path: Optional[str] = None):
        """
        Loads dormant MCP server stubs from mcp_catalog.json and registers them into the registry.
        """
        self._dormant_catalog_loaded = True
        if catalog_path is None:
            # Resolve relative to backend/data/mcp_catalog.json
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            catalog_path = os.path.join(backend_dir, "data", "mcp_catalog.json")

        if not os.path.exists(catalog_path):
            print(f"[ToolVectorRegistry] MCP catalog not found at: {catalog_path}")
            return

        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            servers = data.get("servers", {})
            existing_names = {doc.metadata.get("tool_name") for doc in self._tools_source}
            loaded_count = 0
            for pack_id, cfg in servers.items():
                if pack_id in existing_names:
                    continue
                self.register_tool_schema(
                    name=pack_id,
                    description=cfg.get("description", ""),
                    source_type="mcp_dormant",
                    server_pack_id=pack_id,
                    input_schema={},
                    is_mutating=False
                )
                loaded_count += 1
            if loaded_count > 0:
                print(f"[ToolVectorRegistry] Loaded {loaded_count} dormant MCP stubs from catalog.")
        except Exception as e:
            print(f"[ToolVectorRegistry Warning] Failed to load MCP catalog: {e}")

    def build_index(self):
        """Compiles or updates the tool definitions into an in-memory vector index."""
        with self._lock:
            # Automatically load dormant catalog stubs on initial build if not yet loaded
            if not getattr(self, "_dormant_catalog_loaded", False):
                self._dormant_catalog_loaded = True
                self.load_dormant_catalog()

            if not self._tools_source:
                self.db = None
                return

            # Compute embeddings for any documents that have not been embedded yet
            start_idx = len(self._tools_embeddings)
            if start_idx < len(self._tools_source):
                new_texts = [doc.page_content for doc in self._tools_source[start_idx:]]
                new_embeddings = self.embeddings.embed_documents(new_texts)
                self._tools_embeddings.extend(new_embeddings)

            # Fast in-memory construction from pre-cached embeddings (<0.5 ms)
            text_embeddings = [
                (doc.page_content, emb)
                for doc, emb in zip(self._tools_source, self._tools_embeddings)
            ]
            metadatas = [doc.metadata for doc in self._tools_source]

            self.db = FAISS.from_embeddings(
                text_embeddings=text_embeddings,
                embedding=self.embeddings,
                metadatas=metadatas
            )

    def register_mcp_tools_runtime(self, pack_id: str, mcp_tools: List[Dict[str, Any]]):
        """
        Thread-safe hot-reloading:
        1. Retires the 'mcp_dormant' stub for pack_id.
        2. Adds new granular 'mcp_active' tools into the index.
        3. Fast-rebuilds the index in <1ms without full re-computation of existing embeddings.
        """
        with self._lock:
            # 1. Filter out existing dormant stub for this pack_id
            filtered_sources = []
            filtered_embeddings = []
            for doc, emb in zip(self._tools_source, self._tools_embeddings):
                if doc.metadata.get("tool_name") == pack_id or (
                    doc.metadata.get("server_pack_id") == pack_id
                    and doc.metadata.get("source_type") == "mcp_dormant"
                ):
                    continue
                filtered_sources.append(doc)
                filtered_embeddings.append(emb)

            self._tools_source = filtered_sources
            self._tools_embeddings = filtered_embeddings

            # 2. Prepare new granular active tools
            new_docs = []
            for tool in mcp_tools:
                tool_name = tool.get("name", "")
                description = tool.get("description", "") or f"Tool {tool_name} from {pack_id}"
                is_mutating = tool.get("is_mutating", False)
                input_schema = tool.get("inputSchema", {})

                doc = Document(
                    page_content=description,
                    metadata={
                        "tool_name": tool_name,
                        "source_type": "mcp_active",
                        "server_pack_id": pack_id,
                        "input_schema": input_schema,
                        "is_mutating": is_mutating
                    }
                )
                new_docs.append(doc)

            if new_docs:
                self._tools_source.extend(new_docs)

            # Rebuild index
            self.build_index()
            print(f"[ToolVectorRegistry] Successfully activated {len(new_docs)} MCP tools for pack '{pack_id}'. Index size: {len(self._tools_source)}")

    def remove_mcp_tools_runtime(self, pack_id: str, reinstate_dormant: bool = True):
        """
        Removes active tools of pack_id and optionally re-instates the dormant stub.
        """
        with self._lock:
            filtered_sources = []
            filtered_embeddings = []
            for doc, emb in zip(self._tools_source, self._tools_embeddings):
                if doc.metadata.get("server_pack_id") == pack_id and doc.metadata.get("source_type") == "mcp_active":
                    continue
                filtered_sources.append(doc)
                filtered_embeddings.append(emb)

            self._tools_source = filtered_sources
            self._tools_embeddings = filtered_embeddings

            if reinstate_dormant:
                self.load_dormant_catalog()

            # Fast rebuild
            self.build_index()
            print(f"[ToolVectorRegistry] Removed MCP tools for pack '{pack_id}'. Index size: {len(self._tools_source)}")

    def search_relevant_tools(self, user_query: str, k: int = 5, distance_threshold: float = 1.22) -> list[dict]:
        """Retrieves the top K tools closest to the user's intent, filtered by distance score."""
        with self._lock:
            if not self.db:
                return []

            # Oversample to account for multi-document tool representations
            fetch_k = min(len(self._tools_source), max(k * 3, 15))
            results = self.db.similarity_search_with_score(user_query, k=fetch_k)

            filtered_tools = []
            seen_names = set()
            for doc, score in results:
                if score <= distance_threshold:
                    name = doc.metadata["tool_name"]
                    if name not in seen_names:
                        seen_names.add(name)
                        filtered_tools.append({
                            "name": name,
                            "description": doc.page_content,
                            "score": float(score),
                            "source_type": doc.metadata.get("source_type", "native"),
                            "server_pack_id": doc.metadata.get("server_pack_id"),
                            "input_schema": doc.metadata.get("input_schema", {}),
                            "is_mutating": doc.metadata.get("is_mutating", False)
                        })
                        if len(filtered_tools) >= k:
                            break

            return filtered_tools


# Global singleton for tool indexing
tool_rag_registry = ToolVectorRegistry()
