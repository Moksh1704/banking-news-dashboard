import logging
import os
from typing import Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    logger.warning("GEMINI_API_KEY is not set. Gemini calls will fail.")


def _extract_text(response) -> Optional[str]:
    if not response:
        return None

    # response.text can raise ValueError when no valid parts are returned
    try:
        text = response.text
        if text:
            return text.strip()
    except Exception:
        pass

    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None

        candidate = candidates[0]
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        if not parts:
            return None

        part_texts = []
        for part in parts:
            part_text = getattr(part, "text", None)
            if part_text:
                part_texts.append(part_text)

        if part_texts:
            return "\n".join(part_texts).strip()
    except Exception:
        return None

    return None


def ask_gemini(
    prompt: str,
    temperature: float = 0.2,
    max_output_tokens: int = 512,
) -> Optional[str]:
    if not API_KEY:
        logger.error("Missing GEMINI_API_KEY. Cannot call Gemini.")
        return None

    try:
        model = genai.GenerativeModel(MODEL)
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            },
        )

        text = _extract_text(response)
        if not text:
            try:
                candidates = getattr(response, "candidates", None) or []
                finish_reason = getattr(candidates[0], "finish_reason", None) if candidates else None
                logger.error("Gemini returned no text. finish_reason=%s", finish_reason)
            except Exception:
                logger.error("Gemini returned no text.")
            return None

        return text
    except Exception:
        logger.exception("Gemini call failed.")
        return None


def ask_llm(
    prompt: str,
    temperature: float = 0.2,
    max_output_tokens: int = 512,
) -> Optional[str]:
    return ask_gemini(
        prompt=prompt,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
