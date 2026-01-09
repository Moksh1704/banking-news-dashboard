from backend.app.services.rbi_pdf_scraper import fetch_rbi_pdf_links
from backend.app.services.pdf_parser import extract_text_from_pdf_url

pdfs = fetch_rbi_pdf_links(limit=1)

print("PDFs found:", len(pdfs))

for pdf in pdfs:
    print("=" * 60)
    print("TITLE:", pdf["title"])
    print("URL:", pdf["pdf_url"])

    text = extract_text_from_pdf_url(pdf["pdf_url"])
    print("Extracted text length:", len(text))
    print(text[:500])
