"""
Sparse Lexical BM25 Retriever for AgentEcom.
Provides fast keyword, exact SKU, and entity matching with tokenization.
"""

import re
from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi

def tokenize(text: str) -> List[str]:
    """Tokenize text preserving SKU dashes and alphanumeric codes."""
    if not text:
        return []
    # Lowercase and split on whitespace and punctuation except hyphens/underscores
    tokens = re.findall(r'[a-zA-Z0-9_\-]+', text.lower())
    return tokens

class BM25Retriever:
    def __init__(self):
        self.corpus_docs: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: BM25Okapi = None

    def build_index(self, products: List[Dict[str, Any]]) -> None:
        """
        Build BM25 index over catalog documents.
        Enriches text with SKU repetition to boost exact SKU matches.
        """
        self.corpus_docs = products
        self.tokenized_corpus = []

        for p in products:
            sku = p.get("sku", "")
            name = p.get("name", "")
            desc = p.get("description", "")
            cat = p.get("category", "")
            attrs = p.get("attributes_json", "")
            
            # Enrich document text with weight on SKU and Title
            doc_text = f"{sku} {sku} {name} {name} {cat} {desc} {attrs}"
            self.tokenized_corpus.append(tokenize(doc_text))

        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = None

    def search(self, query: str, top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """Search BM25 index returning ranked (product, score) pairs."""
        if not self.bm25 or not self.corpus_docs:
            return []

        try:
            top_k = int(top_k) if top_k is not None else 10
        except (ValueError, TypeError):
            top_k = 10

        if top_k <= 0:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        doc_scores = self.bm25.get_scores(query_tokens)
        
        # Rank by score descending
        ranked_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)
        
        results = []
        for idx in ranked_indices[:top_k]:
            score = float(doc_scores[idx])
            if score > 0.0:  # Only return positive matches
                results.append((self.corpus_docs[idx], score))
        return results
