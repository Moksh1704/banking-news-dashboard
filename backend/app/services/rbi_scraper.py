import logging
import re
import unicodedata
from io import BytesIO
from typing import Dict, List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from backend.app.services.rbi_sources import RBI_SOURCES

logger = logging.getLogger(__name__)


def _normalized_title(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


_TITLE_PRIORITY_GROUPS = (
    "digital_payments",
    "digital_lending",
    "mpc_monetary_policy",
    "commercial_bank_directions",
)


def _title_priority_group(title: str) -> str:
    normalized = _normalized_title(title)
    if "digital payment" in normalized:
        return "digital_payments"
    if "digital lending" in normalized:
        return "digital_lending"
    if (
        "monetary policy committee" in normalized
        or re.search(r"\bmpc\b", normalized) is not None
        or "monetary policy" in normalized
    ):
        return "mpc_monetary_policy"
    if "commercial bank" in normalized and "direction" in normalized:
        return "commercial_bank_directions"
    return ""


def _is_priority_title(title: str) -> bool:
    return bool(_title_priority_group(title))


def _select_pdf_items(
    source_pdf_items: List[List[Dict]],
    limit: int,
) -> List[Dict]:
    candidates: List[Dict] = []
    seen_pdfs = set()
    position = 0
    while True:
        found_at_position = False
        for items in source_pdf_items:
            if position >= len(items):
                continue
            found_at_position = True
            item = items[position]
            if item["pdf_url"] in seen_pdfs:
                continue
            seen_pdfs.add(item["pdf_url"])
            candidates.append(item)
        if not found_at_position:
            break
        position += 1

    by_category: Dict[str, List[Dict]] = {}
    for item in candidates:
        by_category.setdefault(item["category"], []).append(item)

    categories = list(by_category.values())
    for items in categories:
        items.sort(
            key=lambda item: (
                _TITLE_PRIORITY_GROUPS.index(group)
                if (group := _title_priority_group(item["title"]))
                else len(_TITLE_PRIORITY_GROUPS)
            )
        )

    selected: List[Dict] = []
    position = 0
    while len(selected) < limit:
        found_at_position = False
        for items in categories:
            if position >= len(items):
                continue
            found_at_position = True
            selected.append(items[position])
            if len(selected) >= limit:
                break
        if not found_at_position:
            break
        position += 1

    return selected


def _title_from_document_text(
    content: str,
    fallback_title: str,
    source_name: str,
) -> str:
    """Use a visible PDF heading when the listing link has only a generic title."""
    if fallback_title and _normalized_title(fallback_title) != _normalized_title(source_name):
        return fallback_title

    for line in content.splitlines()[:12]:
        candidate = " ".join(line.split()).strip(" -–—:")
        candidate = re.sub(
            r"^\w+\s+\d{1,2},\s+\d{4}(?:\s+|$)",
            "",
            candidate,
        ).strip(" -–—:")
        if not candidate or len(candidate) < 12 or len(candidate) > 180:
            continue
        if candidate.casefold().startswith(("rbi/", "www.", "reserve bank of india")):
            continue
        return candidate

    return fallback_title or source_name


def _title_from_listing_row(pdf_link) -> str:
    row = pdf_link.find_parent("tr")
    if row is None:
        return ""

    for link in row.find_all("a", href=True):
        href = str(link["href"]).strip()
        if urlparse(href).path.lower().endswith(".pdf"):
            continue
        title = link.get_text(" ", strip=True)
        if title:
            return title

    return ""


def fetch_rbi_pdf_links(limit: int = 20) -> List[Dict]:
    """
    Collect links to PDF documents from the configured RBI source pages.

    Only PDF links are accepted because the existing extraction pipeline uses
    pypdf and does not reliably parse RBI HTML pages.
    """
    if limit <= 0:
        return []

    source_pdf_items: List[List[Dict]] = []
    seen_sources = set()

    for source in RBI_SOURCES:
        source_url = source["url"]
        if source_url in seen_sources:
            continue
        seen_sources.add(source_url)

        try:
            response = requests.get(source_url, timeout=20)
            response.raise_for_status()
        except requests.RequestException:
            logger.exception("Failed to fetch RBI source page %s", source_url)
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        source_items = []
        for link in soup.find_all("a", href=True):
            pdf_url = urljoin(source_url, str(link["href"]).strip())
            if not urlparse(pdf_url).path.lower().endswith(".pdf"):
                continue

            title = (
                _title_from_listing_row(link)
                or link.get_text(" ", strip=True)
                or source["name"]
            )
            source_items.append(
                {
                    "title": title,
                    "pdf_url": pdf_url,
                    "source_name": source["name"],
                    "category": source.get("category", source["name"]),
                }
            )
        source_pdf_items.append(source_items)

    return _select_pdf_items(source_pdf_items, limit)


def extract_text_from_pdf_url(pdf_url: str) -> str:
    """
    Download PDF and extract full text
    """

    response = requests.get(pdf_url, timeout=30)
    response.raise_for_status()

    pdf_file = BytesIO(response.content)
    reader = PdfReader(pdf_file)

    text = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)

    return "\n".join(text)


def fetch_all_rbi_documents(limit: int = 20) -> List[Dict]:
    """
    Fetch multiple RBI PDFs and extract text
    Returns documents compatible with the /news/rbi endpoint.
    """

    documents = []
    pdfs = fetch_rbi_pdf_links(limit=limit)

    for item in pdfs:
        try:
            content = extract_text_from_pdf_url(item["pdf_url"])

            if len(content.strip()) < 500:
                continue

            documents.append({
                "title": _title_from_document_text(
                    content,
                    item["title"],
                    item.get("source_name", item["category"]),
                ),
                "source": "RBI",
                "url": item["pdf_url"],
                "category": item["category"],
                "content": content
            })

        except Exception:
            logger.exception("RBI PDF extraction failed for %s", item["pdf_url"])

    return documents
