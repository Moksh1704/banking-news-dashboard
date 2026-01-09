from backend.app.services.pdf_parser import extract_text_from_pdf_url
from backend.app.services.text_cleaner import clean_text
from backend.app.services.text_chunker import chunk_text

pdf_url = "https://www.rbi.org.in/commonman/Upload/English/PressRelease/PDFs/PR1791.pdf"

raw_text = extract_text_from_pdf_url(pdf_url)
cleaned = clean_text(raw_text)
chunks = chunk_text(cleaned)

print("Total chunks:", len(chunks))
print("=" * 60)
print(chunks[0])
