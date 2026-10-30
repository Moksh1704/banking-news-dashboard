import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import faiss

from backend.app.services.rbi_ingest import prepare_rbi_chunks
from backend.app.services.rbi_scraper import fetch_all_rbi_documents
from backend.app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


def _validate_staged_index(index_path: Path, metadata_path: Path) -> int:
    if not index_path.is_file() or not metadata_path.is_file():
        raise RuntimeError("The staged index pair is incomplete.")

    index = faiss.read_index(str(index_path))
    with metadata_path.open("r", encoding="utf-8") as metadata_file:
        documents = json.load(metadata_file)

    if not isinstance(documents, list) or not documents:
        raise RuntimeError("The staged metadata must contain documents.")
    if index.ntotal != len(documents):
        raise RuntimeError(
            "The staged FAISS index and metadata counts do not match."
        )
    if any(
        not isinstance(document, dict)
        or not document.get("text")
        or not isinstance(document.get("metadata"), dict)
        for document in documents
    ):
        raise RuntimeError("The staged metadata contains an invalid document.")

    return len(documents)


def build_staged_rbi_index(
    limit: int = 20,
    staging_root: Optional[Path] = None,
    document_fetcher: Optional[Callable[..., List[Dict[str, Any]]]] = None,
    vector_store_factory: Optional[Callable[..., Any]] = None,
) -> Tuple[Path, int]:
    """
    Build and validate an RBI index pair in a unique staging directory.

    This function never replaces or writes to the active index files.
    """
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    fetch_documents = document_fetcher or fetch_all_rbi_documents
    make_vector_store = vector_store_factory or VectorStore

    documents = fetch_documents(limit=limit)
    chunks = prepare_rbi_chunks(documents)
    if not chunks:
        raise RuntimeError("No RBI document chunks were produced.")

    if staging_root is None:
        data_dir = Path(__file__).resolve().parent.parent / "data"
        staging_root = data_dir / "staging"
    staging_root = Path(staging_root)
    staging_root.mkdir(parents=True, exist_ok=True)

    stage_dir = Path(
        tempfile.mkdtemp(prefix="rbi-index-", dir=str(staging_root))
    )
    index_path = stage_dir / "rbi.index"
    metadata_path = stage_dir / "rbi_docs.json"

    try:
        vector_store = make_vector_store(
            index_path=str(index_path),
            metadata_path=str(metadata_path),
        )
        vector_store.add_documents(chunks)
        if not vector_store.save():
            raise RuntimeError("The vector store failed to save the staged index.")

        document_count = _validate_staged_index(index_path, metadata_path)
        logger.info(
            "Validated staged RBI index: directory=%s documents=%d",
            stage_dir,
            document_count,
        )
        return stage_dir, document_count
    except Exception:
        logger.exception("Failed to build staged RBI index.")
        for path in (index_path, metadata_path):
            if path.exists():
                path.unlink()
        try:
            stage_dir.rmdir()
        except OSError:
            logger.warning("Staging directory remains for inspection: %s", stage_dir)
        raise
