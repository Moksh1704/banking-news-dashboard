import subprocess
from typing import Optional


def _call_llm(prompt: str) -> Optional[str]:
    """
    Calls a local LLM (Ollama).
    Replace model name if needed.
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


def is_banking_or_finance_content(title: str, description: str) -> bool:
    """
    Uses an LLM to decide whether content is related
    to banking or finance.

    Returns:
        True  -> Banking / Finance
        False -> Not related
    """

    prompt = f"""
You are a strict classifier.

Determine whether the following content is related
to BANKING or FINANCE.

Rules:
- Reply ONLY with YES or NO
- No explanation
- If unsure, reply NO

Title:
{title}

Description:
{description}

Answer:
"""

    response = _call_llm(prompt)

    if not response:
        return False

    return response.strip().upper() == "YES"
