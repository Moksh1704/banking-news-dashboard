import requests
from io import BytesIO
from pypdf import PdfReader


def extract_text_from_pdf_url(pdf_url: str) -> str:
    """
    Download a PDF from a URL and extract text from all pages.
    """

    response = requests.get(pdf_url, timeout=30)
    response.raise_for_status()

    pdf_stream = BytesIO(response.content)
    reader = PdfReader(pdf_stream)

    text_chunks = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_chunks.append(page_text)

    return "\n".join(text_chunks)
