import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

RBI_PRESS_RELEASE_LIST = (
    "https://www.rbi.org.in/commonman/English/Scripts/PressReleases.aspx"
)


def fetch_rbi_pdf_links(limit: int = 5):
    """
    Fetch RBI press release PDF links.
    """

    response = requests.get(RBI_PRESS_RELEASE_LIST, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    pdf_links = []

    for a in soup.select("a[href$='.PDF'], a[href$='.pdf']"):
        if len(pdf_links) >= limit:
            break

        href = a.get("href")
        if not href:
            continue

        full_url = urljoin(RBI_PRESS_RELEASE_LIST, href)

        title = a.get_text(strip=True)

        pdf_links.append({
            "source": "RBI",
            "title": title,
            "pdf_url": full_url
        })

    return pdf_links
