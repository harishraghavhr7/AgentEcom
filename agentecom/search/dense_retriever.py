"""
Dense Vector Retriever for AgentEcom.
Provides semantic and natural-language similarity search using dense vector embeddings.
"""

import json
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from agentecom.config import settings

class DenseRetriever:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._model = None
        self.corpus_docs: List[Dict[str, Any]] = []
        self.doc_embeddings: Optional[np.ndarray] = None  # shape (N, D)

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode_text(self, text: str) -> np.ndarray:
        """Encode a single query or text asynchronously / synchronously."""
        model = self._get_model()
        vec = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return vec

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Batch encode list of texts."""
        model = self._get_model()
        vecs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return vecs

    def build_index(self, products: List[Dict[str, Any]], precomputed_embeddings: Optional[List[List[float]]] = None) -> None:
        """
        Build dense vector index from catalog documents and precomputed embeddings.
        If precomputed embeddings are missing, compute in batch.
        """
        self.corpus_docs = products
        if not products:
            self.doc_embeddings = None
            return

        if precomputed_embeddings and len(precomputed_embeddings) == len(products):
            self.doc_embeddings = np.array(precomputed_embeddings, dtype=np.float32)
            # Ensure normalized for cosine similarity via dot product
            norms = np.linalg.norm(self.doc_embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self.doc_embeddings = self.doc_embeddings / norms
        else:
            texts = [
                f"{p.get('name', '')}. Category: {p.get('category', '')}. Description: {p.get('description', '')}. Attributes: {p.get('attributes_json', '')}"
                for p in products
            ]
            self.doc_embeddings = self.encode_batch(texts)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """Dense cosine similarity search."""
        if self.doc_embeddings is None or not self.corpus_docs:
            return []

        try:
            top_k = int(top_k) if top_k is not None else 10
        except (ValueError, TypeError):
            top_k = 10

        if top_k <= 0:
            return []

        query_vec = self.encode_text(query)
        # Cosine similarity is dot product of normalized vectors
        scores = np.dot(self.doc_embeddings, query_vec)

        ranked_indices = np.argsort(scores)[::-1]
        results = []
        for idx in ranked_indices[:top_k]:
            results.append((self.corpus_docs[idx], float(scores[idx])))
        return results
