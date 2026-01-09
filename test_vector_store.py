from backend.app.services.pdf_parser import extract_text_from_pdf_url
from backend.app.services.text_cleaner import clean_text
from backend.app.services.text_chunker import chunk_text
from backend.app.services.vector_store import VectorStore

# RBI PDF used earlier
pdf_url = "https://www.rbi.org.in/commonman/Upload/English/PressRelease/PDFs/PR1791.pdf"

raw_text = extract_text_from_pdf_url(pdf_url)
cleaned_text = clean_text(raw_text)
chunks = chunk_text(cleaned_text)

store = VectorStore()
store.add_documents(chunks)

results = store.search("What action did RBI take?")

print("Retrieved chunks:")
for r in results:
    print("=" * 60)
    print(r[:300])
