# core/routing/layer2/tool_vector_db.py
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from core.routing.encoder import get_shared_encoder
import numpy as np


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
        self.db = None
        self._tools_source = []

    def register_tool_schema(self, name: str, description: str):
        """Adds a tool definition to the raw index source."""
        self._tools_source.append(Document(
            page_content=description,
            metadata={"tool_name": name}
        ))

    def build_index(self):
        """Compiles the tool definitions into an in-memory vector index."""
        if self._tools_source:
            self.db = FAISS.from_documents(self._tools_source, self.embeddings)

    def search_relevant_tools(self, user_query: str, k: int = 5, distance_threshold: float = 1.22) -> list[dict]:
        """Retrieves the top K tools closest to the user's intent, filtered by distance score."""
        if not self.db:
            return []
        
        # When tools have multiple dimensional sub-documents (e.g. code_executor, web_search),
        # oversample raw chunks so deduplication by tool_name returns exactly k distinct tool candidates.
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
                        "score": float(score)
                    })
                    if len(filtered_tools) >= k:
                        break
        
        return filtered_tools


# Global singleton for tool indexing
tool_rag_registry = ToolVectorRegistry()
