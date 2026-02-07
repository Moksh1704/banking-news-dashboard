from typing import Optional

from backend.app.services.llm_service import ask_llm


def llm_call(prompt: str, temperature: float = 0.2) -> Optional[str]:
    return ask_llm(prompt=prompt, temperature=temperature)
