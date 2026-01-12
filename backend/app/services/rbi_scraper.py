import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from pypdf import PdfReader
from io import BytesIO


RBI_PRESS_RELEASES_URL = (
    "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
)


def fetch_rbi_pdf_links(limit: int = 20) -> List[Dict]:
    """
    Scrape RBI press release page and collect PDF links.
    Returns list of {title, pdf_url}
    """

    response = requests.get(RBI_PRESS_RELEASES_URL, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    pdf_items = []

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if ".pdf" not in href.lower():
            continue

        title = link.get_text(strip=True)
        if not title:
            title = "RBI Press Release"

        # Handle relative URLs
        if href.startswith("/"):
            href = "https://www.rbi.org.in" + href

        pdf_items.append({
            "title": title,
            "pdf_url": href
        })

        if len(pdf_items) >= limit:
            break

    return pdf_items


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
    Returns list of documents for RAG
    """

    documents = []
    pdfs = fetch_rbi_pdf_links(limit=limit)

    for item in pdfs:
        try:
            content = extract_text_from_pdf_url(item["pdf_url"])

            if len(content.strip()) < 500:
                continue

            documents.append({
                "title": item["title"],
                "source": "RBI",
                "url": item["pdf_url"],
                "content": content
            })

        except Exception as e:
            print("⚠️ RBI PDF failed:", item["pdf_url"], e)

    return documents
