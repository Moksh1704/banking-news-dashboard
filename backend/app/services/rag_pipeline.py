"""
rag_pipeline.py  ·  v2.0
═════════════════════════
Dual-source RAG pipeline — searches both RBI documents and live banking news,
merges the results into a single context, and sends them to Gemini.

What changed from v1 → v2
──────────────────────────
  NEW  Accepts optional NewsRAG instance alongside the existing VectorStore.
  NEW  Dual-source retrieval: rbi_docs + news_docs merged into one context.
  NEW  Context sections clearly labelled [RBI Document] vs [Banking News].
  NEW  Improved system prompt (Banking News Intelligence Assistant).
  NEW  Source list includes "type" field so the frontend can style results.
  NEW  Graceful degradation: if news index is not ready, answers from RBI only.
  KEPT All existing public interface: RAGPipeline(vector_store), answer(query).
  KEPT Auto-ingest for RBI index (unchanged).
  KEPT Fallback response when Gemini quota is exhausted.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

from backend.app.services.llm_service import ask_llm
from backend.app.services.rbi_ingest import prepare_rbi_chunks
from backend.app.services.rbi_scraper import fetch_all_rbi_documents
from backend.app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

_OTHER_INSTITUTION_TITLE_PATTERNS = (
    re.compile(r"\burban\s+co[\s-]*operative\s+banks?\b", re.IGNORECASE),
    re.compile(r"\bco[\s-]*operative\s+banks?\b", re.IGNORECASE),
    re.compile(r"\bpayments?\s+banks?\b", re.IGNORECASE),
    re.compile(r"\bsmall\s+finance\s+banks?\b", re.IGNORECASE),
    re.compile(r"\bregional\s+rural\s+banks?\b", re.IGNORECASE),
    re.compile(r"\bnon[\s-]*banking\s+financial\s+companies\b", re.IGNORECASE),
    re.compile(r"\bnon[\s-]*bank\s+payment\s+system\s+operators\b", re.IGNORECASE),
)
_INSTITUTION_QUERY_PATTERNS = (
    re.compile(r"\bcommercial[\s-]+banks?\b", re.IGNORECASE),
    *_OTHER_INSTITUTION_TITLE_PATTERNS,
)


def _is_broad_digital_payment_security_query(query: str) -> bool:
    normalized_query = unicodedata.normalize("NFKC", query)
    if not re.search(r"\bdigital[\s-]+payments?\b", normalized_query, re.IGNORECASE):
        return False
    if not re.search(r"\bsecurity\b|\bcontrols?\b", normalized_query, re.IGNORECASE):
        return False
    return not any(
        pattern.search(normalized_query)
        for pattern in _INSTITUTION_QUERY_PATTERNS
    )


def _deduplicate_source_documents(
    documents: List[Dict[str, Any]],
    limit: int,
) -> List[Dict[str, Any]]:
    if limit <= 0:
        return []

    unique_documents = []
    seen_urls = set()
    for document in documents:
        metadata = document.get("metadata")
        url = metadata.get("url") if isinstance(metadata, dict) else None
        if isinstance(url, str) and url:
            if url in seen_urls:
                continue
            seen_urls.add(url)

        unique_documents.append(document)
        if len(unique_documents) >= limit:
            break
    return unique_documents


def _uses_institution_scope_filter(query: str) -> bool:
    normalized_query = unicodedata.normalize("NFKC", query)
    return bool(
        re.search(r"\bcommercial[\s-]+banks?\b", normalized_query, re.IGNORECASE)
    )


def _filter_institution_scope(
    query: str,
    documents: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not _uses_institution_scope_filter(query):
        return documents

    filtered_documents = []
    for document in documents:
        metadata = document.get("metadata")
        if not isinstance(metadata, dict):
            filtered_documents.append(document)
            continue

        title = metadata.get("title", "")
        if not isinstance(title, str):
            filtered_documents.append(document)
            continue

        if re.search(r"\bcommercial[\s-]+banks?\b", title, re.IGNORECASE):
            filtered_documents.append(document)
            continue

        if any(pattern.search(title) for pattern in _OTHER_INSTITUTION_TITLE_PATTERNS):
            continue

        filtered_documents.append(document)

    return filtered_documents


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a Banking News Intelligence Assistant.

You have access to two knowledge sources:
1. RBI (Reserve Bank of India) regulations, circulars, and official notifications.
2. Latest Indian banking and financial news from trusted news outlets.

Instructions:
- Answer the user's question using ONLY the context provided below.
- Clearly distinguish between regulatory information (from RBI documents) and
  news-based information (from recent articles) when both are relevant.
- Treat each RBI document as applicable only to the institution type named in
  its title, unless that document's text explicitly states otherwise.
- Never combine requirements from Urban Co-operative Banks (UCBs), Small
  Finance Banks (SFBs), Payments Banks, Commercial Banks, and NBFCs into one
  universal checklist.
- When retrieved RBI documents cover multiple institution types, explain that
  scope and present each institution's requirements separately under its own
  heading. For a broad question, make clear that the retrieved directions cover
  different institution types.
- Describe a control as COMMON only when retrieved passages explicitly support
  it for EVERY institution being discussed. If evidence supports it for only
  some institutions, attribute it only to those institutions.
- Never infer that a requirement applies to another institution because its
  wording is similar.
- If a retrieved passage lacks sufficient detail, identify the institution and
  source document, then state that the passage does not establish the specific
  requirement. Absence from a retrieved chunk does not prove that the full RBI
  direction lacks that requirement.
- Use only facts explicitly supported by retrieved passages. Do not infer
  requirements from regulatory terminology or general knowledge, or claim a
  control applies to an institution unless its retrieved source supports that
  claim. If evidence is insufficient, say so clearly. Do not invent dates,
  deadlines, penalties, controls, or regulatory obligations.
- Start with a short summary, mention the source document title alongside each
  institution's information, and end with a concise takeaway.
- If the context does not contain enough information to answer confidently,
  state: "This information is not available in the current RBI data or news index."
- Keep answers concise: use a short introduction, separate institution
  headings, a few supported key points per institution, and a short takeaway.
- Be accurate and professional.
- Do not speculate beyond the provided context.
"""


class RAGPipeline:
    """
    Dual-source RAG pipeline combining RBI documents and banking news.

    Parameters
    ----------
    vector_store : VectorStore
        The RBI FAISS vector store (index_name="rbi").
    news_rag : NewsRAG | None
        Optional news retrieval component.  When provided, news results are
        merged with RBI results before building the prompt context.
        When None the pipeline behaves exactly like v1 (RBI-only).
    top_k : int
        Number of chunks to retrieve from each source.
    auto_ingest : bool
        Auto-build the RBI index if not found (behaviour from v1).
    ingest_limit : int
        Max RBI documents to ingest during auto-ingest.
    fallback_char_limit : int
        Character limit for the fallback excerpt when Gemini is unavailable.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        news_rag=None,                  # NewsRAG | None — avoid circular import
        top_k: int = 5,
        auto_ingest: bool = True,
        ingest_limit: int = 10,
        fallback_char_limit: int = 800,
    ):
        self.vector_store = vector_store
        self.news_rag = news_rag
        self.top_k = top_k
        self.auto_ingest = auto_ingest
        self.ingest_limit = ingest_limit
        self._ingestion_attempted = False
        self.fallback_char_limit = fallback_char_limit

    # ── RBI index management (unchanged from v1) ──────────────────────────────

    def _ensure_rbi_index(self) -> bool:
        """Ensure the RBI vector store is ready, building it if necessary."""
        if self.vector_store.is_ready():
            return True

        if self.vector_store.load():
            return True

        if not self.auto_ingest or self._ingestion_attempted:
            return False

        self._ingestion_attempted = True
        logger.info("No existing RBI index found. Building embeddings...")

        try:
            documents = fetch_all_rbi_documents(limit=self.ingest_limit)
            all_chunks = prepare_rbi_chunks(documents)

            if not all_chunks:
                logger.warning("No chunks generated from RBI documents.")
                return False

            self.vector_store.add_documents(all_chunks)
            self.vector_store.save()
            return self.vector_store.is_ready()

        except Exception:
            logger.exception("Failed to build RBI embeddings.")
            return False

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def _retrieve_rbi(self, query: str) -> List[Dict[str, Any]]:
        """Search the RBI vector store."""
        try:
            if _is_broad_digital_payment_security_query(query):
                candidates = self.vector_store.search(query, top_k=12)
                return _deduplicate_source_documents(candidates, self.top_k)
            if _uses_institution_scope_filter(query):
                candidates = self.vector_store.search(query, top_k=12)
                relevant_documents = _filter_institution_scope(query, candidates)
                return relevant_documents[: self.top_k]
            return self.vector_store.search(query, top_k=self.top_k)
        except Exception:
            logger.exception("RBI search failed.")
            return []

    def _retrieve_news(self, query: str) -> List[Dict[str, Any]]:
        """Search the news vector store (if available)."""
        if self.news_rag is None:
            return []
        if not self.news_rag.is_ready():
            logger.info("News index not ready — skipping news retrieval.")
            return []
        try:
            return self.news_rag.search_news(query, top_k=self.top_k)
        except Exception:
            logger.exception("News search failed.")
            return []

    # ── Context building ──────────────────────────────────────────────────────

    def _build_context(
        self,
        rbi_docs: List[Dict[str, Any]],
        news_docs: List[Dict[str, Any]],
    ) -> str:
        """
        Merge RBI and news results into a single labelled context string.

        Format:
            === RBI Regulatory Documents ===
            [RBI Document 1]
            <text>

            === Latest Banking News ===
            [News Article 1]
            <text>
        """
        sections: List[str] = []

        if rbi_docs:
            rbi_blocks = ["=== RBI Regulatory Documents ==="]
            for i, doc in enumerate(rbi_docs, 1):
                meta = doc.get("metadata", {})
                header = f"[RBI Document {i}]"
                if meta.get("title"):
                    header += f"  {meta['title']}"
                rbi_blocks.append(f"{header}\n{doc['text']}")
            sections.append("\n\n".join(rbi_blocks))

        if news_docs:
            news_blocks = ["=== Latest Banking News ==="]
            for i, doc in enumerate(news_docs, 1):
                meta = doc.get("metadata", {})
                header = f"[News Article {i}]"
                if meta.get("title"):
                    header += f"  {meta['title']}"
                if meta.get("source"):
                    header += f"  ({meta['source']})"
                if meta.get("published"):
                    # Show date only (first 10 chars of ISO string)
                    header += f"  — {meta['published'][:10]}"
                news_blocks.append(f"{header}\n{doc['text']}")
            sections.append("\n\n".join(news_blocks))

        return "\n\n" + "\n\n".join(sections)

    def _build_sources(
        self,
        rbi_docs: List[Dict[str, Any]],
        news_docs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build the sources list for the API response."""
        sources = []

        for doc in rbi_docs:
            meta = doc.get("metadata", {})
            sources.append(
                {
                    "title": meta.get("title"),
                    "url": meta.get("url"),
                    "source": meta.get("source", "RBI"),
                    "page": meta.get("page"),
                    "type": "rbi",
                    "score": doc.get("score"),
                }
            )

        for doc in news_docs:
            meta = doc.get("metadata", {})
            sources.append(
                {
                    "title": meta.get("title"),
                    "url": meta.get("url"),
                    "source": meta.get("source", "Google News"),
                    "published": meta.get("published"),
                    "type": "news",
                    "score": doc.get("score"),
                }
            )

        return sources

    # ── Main entry point ──────────────────────────────────────────────────────

    def answer(self, query: str) -> Dict[str, Any]:
        """
        Answer a user question using RBI documents + banking news.

        Parameters
        ----------
        query : str
            The user's question.

        Returns
        -------
        dict
            { "answer": str, "sources": list[dict] }
        """
        try:
            if not query.strip():
                return {"answer": "Please enter a valid question.", "sources": []}

            # ── 1. Ensure RBI index ──────────────────────────────────────────
            rbi_ready = self._ensure_rbi_index()
            if not rbi_ready:
                return {
                    "answer": (
                        "The RBI knowledge index is not ready yet. "
                        "Please try again in a moment."
                    ),
                    "sources": [],
                }

            # ── 2. Dual-source retrieval ─────────────────────────────────────
            retrieved_rbi_docs = self._retrieve_rbi(query)
            retrieved_news_docs = self._retrieve_news(query)
            rbi_docs = _filter_institution_scope(query, retrieved_rbi_docs)
            news_docs = _filter_institution_scope(query, retrieved_news_docs)

            logger.info(
                "answer: query=%r  rbi_docs=%d  news_docs=%d",
                query[:60],
                len(rbi_docs),
                len(news_docs),
            )

            if (
                (
                    (retrieved_rbi_docs or retrieved_news_docs)
                    or _uses_institution_scope_filter(query)
                )
                and not rbi_docs
                and not news_docs
            ):
                return {
                    "answer": (
                        "The retrieved sources cover other institution types, "
                        "so there is not enough relevant information to answer "
                        "this commercial-bank question."
                    ),
                    "sources": [],
                }

            if not rbi_docs and not news_docs:
                return {
                    "answer": (
                        "No relevant information found in the RBI documents "
                        "or the news index for this query."
                    ),
                    "sources": [],
                }

            # ── 3. Build combined context ────────────────────────────────────
            context = self._build_context(rbi_docs, news_docs)

            # ── DEBUG ────────────────────────────────────────────────────────
            docs = rbi_docs + news_docs
            print("RBI Docs:", len(rbi_docs))
            print("News Docs:", len(news_docs))
            print("Combined Docs:", len(docs))
            print("Retrieved document titles:")
            for doc in docs:
                print(" •", doc.get("metadata", {}).get("title"))
            print("Context Preview:")
            print(context[:500])
            # ── END DEBUG ────────────────────────────────────────────────────

            # ── 4. Build prompt ──────────────────────────────────────────────
            prompt = (
                f"{SYSTEM_PROMPT}\n\n"
                f"Context:\n{context}\n\n"
                f"Question:\n{query}\n\n"
                f"Answer:"
            )

            # ── 5. Call Gemini ───────────────────────────────────────────────
            response = ask_llm(prompt)

            sources = self._build_sources(rbi_docs, news_docs)

            if not response:
                # Fallback: return best excerpt when Gemini is unavailable
                best = rbi_docs[0] if rbi_docs else news_docs[0]
                fallback_text = best["text"][: self.fallback_char_limit]
                source_label = (
                    "RBI excerpt" if rbi_docs else "news article excerpt"
                )
                return {
                    "answer": (
                        f"AI quota is currently unavailable. "
                        f"Here is the most relevant {source_label}:\n\n"
                        f"{fallback_text}"
                    ),
                    "sources": sources[:1],
                }

            return {"answer": response, "sources": sources}

        except Exception:
            logger.exception("RAGPipeline.answer failed.")
            return {
                "answer": "Sorry, the chatbot service is currently unavailable.",
                "sources": [],
            }