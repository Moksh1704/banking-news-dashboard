from backend.app.services.web_scraper import fetch_web_article
from backend.app.services.text_cleaner import clean_text
from backend.app.services.text_chunker import chunk_text

url = "https://www.livemint.com/industry/banking"

raw = fetch_web_article(url)
cleaned = clean_text(raw)
chunks = chunk_text(cleaned)

print("Chunks extracted:", len(chunks))
print(chunks[0][:500])
