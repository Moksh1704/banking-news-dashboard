import re


def clean_text(text: str) -> str:
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove RBI boilerplate patterns
    boilerplate_patterns = [
        r"www\.rbi\.org\.in.*?Phone.*?\d+",
        r"Department of Communication.*?Mumbai\s*-\s*\d+",
        r"संचार विभाग.*?फोन.*?\d+",
    ]

    for pattern in boilerplate_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text.strip()
