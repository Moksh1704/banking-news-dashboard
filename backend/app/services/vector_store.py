import json
import logging
import os
from typing import Any, Dict, Iterable, List, Optional, Union

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        index_path: Optional[str] = None,
        metadata_path: Optional[str] = None,
    ):
        # Embedding model (small, fast, free)
        self.model = SentenceTransformer(model_name)
        self.index: Optional[faiss.Index] = None
        self.documents: List[Dict[str, Any]] = []

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "data")
        self.index_path = index_path or os.path.join(data_dir, "rbi.index")
        self.metadata_path = metadata_path or os.path.join(data_dir, "rbi_docs.json")

    def is_ready(self) -> bool:
        return self.index is not None and len(self.documents) > 0

    def add_documents(self, docs: Iterable[Union[str, Dict[str, Any]]]):
        normalized_docs: List[Dict[str, Any]] = []
        texts: List[str] = []

        for doc in docs:
            if isinstance(doc, str):
                text = doc.strip()
                metadata: Dict[str, Any] = {}
            else:
                text = str(doc.get("text", "")).strip()
                metadata = dict(doc.get("metadata", {}))
                for key in ("title", "url", "source", "page"):
                    if key in doc:
                        metadata.setdefault(key, doc[key])

            if not text:
                continue

            normalized_docs.append({"text": text, "metadata": metadata})
            texts.append(text)

        if not texts:
            return

        embeddings = self.model.encode(texts)
        embeddings = np.array(embeddings).astype("float32")

        if self.index is None:
            self.index = faiss.IndexFlatL2(embeddings.shape[1])

        self.index.add(embeddings)
        self.documents.extend(normalized_docs)

    def search(self, query: str, top_k: int = 3, k: Optional[int] = None):
        if k is not None:
            top_k = k

        if not self.is_ready():
            logger.warning("Vector store is not ready. No index/documents loaded.")
            return []

        query_embedding = self.model.encode([query])
        query_embedding = np.array(query_embedding).astype("float32")

        search_k = min(top_k, len(self.documents))
        distances, indices = self.index.search(query_embedding, search_k)

        results = []
        for rank, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self.documents):
                continue

            doc = self.documents[idx]
            results.append(
                {
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {}),
                    "score": float(distances[0][rank]),
                }
            )

        return results

    def save(self) -> bool:
        if self.index is None:
            logger.warning("No FAISS index to save.")
            return False

        data_dir = os.path.dirname(self.index_path)
        os.makedirs(data_dir, exist_ok=True)

        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=True, indent=2)

        logger.info("Saved FAISS index to %s", self.index_path)
        return True

    def load(self) -> bool:
        if not (os.path.exists(self.index_path) and os.path.exists(self.metadata_path)):
            return False

        try:
            self.index = faiss.read_index(self.index_path)
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self.documents = json.load(f)
            logger.info("Loaded FAISS index from %s", self.index_path)
            return True
        except Exception:
            logger.exception("Failed to load FAISS index or metadata.")
            return False
