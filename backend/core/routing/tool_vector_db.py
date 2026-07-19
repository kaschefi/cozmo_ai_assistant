from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from semantic_router.encoders import FastEmbedEncoder
import numpy as np


class LangChainFastEmbedBridge:
    """Bridges Layer 1 encoder to LangChain's vector store interface."""

    def __init__(self):
        self.encoder = FastEmbedEncoder(name="BAAI/bge-small-en-v1.5")

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

    def search_relevant_tools(self, user_query: str, k: int = 3, distance_threshold: float = 0.86) -> list[dict]:
        """Retrieves the top K tools closest to the user's intent, filtered by distance score."""
        if not self.db:
            return []
        
        # similarity_search_with_score returns a list of (Document, score) tuples
        # Under BAAI/bge-small-en-v1.5 and FAISS, a lower L2 distance means a closer match
        results = self.db.similarity_search_with_score(user_query, k=k)
        
        filtered_tools = []
        seen_names = set()
        for doc, score in results:
            if score <= distance_threshold:
                name = doc.metadata["tool_name"]
                if name not in seen_names:
                    seen_names.add(name)
                    filtered_tools.append({
                        "name": name,
                        "description": doc.page_content
                    })
        
        return filtered_tools


# Global singleton for tool indexing
tool_rag_registry = ToolVectorRegistry()