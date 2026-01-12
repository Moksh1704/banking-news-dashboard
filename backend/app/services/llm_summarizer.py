import subprocess
from typing import Optional


def summarize_text(text: str) -> Optional[str]:
    """
    Generates a short, simple summary
    suitable for non-technical users.
    """

    prompt = f"""
Summarize the following content in 2–3 simple sentences.
Use plain language.
Focus only on banking or financial meaning.

Content:
{text}

Summary:
"""

    try:
        result = subprocess.run(
            ["ollama", "run", "tinyllama"],
            input=prompt,
            capture_output=True,
            timeout=30,
            encoding="utf-8",
            errors="ignore"
        )

        return result.stdout.strip()
    except Exception:
        return None
