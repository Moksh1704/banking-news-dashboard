import requests


def resolve_google_news_url(url: str) -> str:
    """
    Resolves Google News redirect URLs to the original publisher URL
    """
    try:
        response = requests.get(
            url,
            allow_redirects=True,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        return response.url
    except Exception:
        return url
