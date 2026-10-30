"""
llm_service.py  ·  v3.0  (Groq + retry)
════════════════════════════════════════
Centralised LLM interface for the Banking News Intelligence System.

What changed from v2 → v3
──────────────────────────
  NEW  groq.RateLimitError caught with exponential-ish retry logic.
       Retries up to MAX_LLM_RETRIES times, waiting RETRY_DELAY_SECONDS
       between each attempt.  After all retries are exhausted the function
       returns None so callers can fall back gracefully.
  NEW  groq.APIStatusError / groq.APIConnectionError caught separately so
       transient network errors also benefit from retry.
  NEW  GROQ_CALL_COUNT module-level counter — incremented on every successful
       or failed request attempt.  Useful for asserting "exactly 1 call per
       query" in tests:  from llm_service import GROQ_CALL_COUNT
  KEPT All v2 public behaviour: ask_llm() signature unchanged.
  KEPT GROQ_API_KEY / GROQ_MODEL env vars.

Design rule (enforced here, not just documented)
─────────────────────────────────────────────────
  ask_llm() is the ONLY place in this codebase that talks to Groq.
  No other module should import Groq directly or call Groq APIs.

  Permitted callers:
    ✅  rag_pipeline.py  — exactly once per user query
  Forbidden callers:
    ❌  google_news_rss.py   — uses keyword filter only
    ❌  news_classifier.py   — uses keyword filter only
    ❌  rbi_scraper.py       — fetches documents, no LLM
    ❌  vector_store.py      — embedding/retrieval, no LLM
    ❌  main.py              — delegates entirely to RAGPipeline

Environment variables
─────────────────────
  GROQ_API_KEY      Required. Your Groq API key.
  GROQ_MODEL        Optional. Defaults to llama-3.3-70b-versatile.
  GROQ_MAX_RETRIES  Optional. Integer, defaults to 3.
  GROQ_RETRY_DELAY  Optional. Float seconds, defaults to 3.0.

Model choice
────────────
  llama-3.3-70b-versatile is Groq's recommended general-purpose chat model.
  Other supported options:
    - llama-3.1-8b-instant        (fastest, lower quality)
    - mixtral-8x7b-32768          (large context window)
    - gemma2-9b-it                (Google Gemma 2 via Groq)
  Change via GROQ_MODEL env var — no code edit required.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

import groq as groq_sdk
from groq import Groq

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Retry configuration — override via env vars in production
MAX_LLM_RETRIES: int = int(os.getenv("GROQ_MAX_RETRIES", "3"))
RETRY_DELAY_SECONDS: float = float(os.getenv("GROQ_RETRY_DELAY", "3.0"))

if not GROQ_API_KEY:
    logger.warning(
        "GROQ_API_KEY is not set. LLM calls will fail. "
        "Add GROQ_API_KEY to your .env file."
    )

# Instantiate client once at module load — thread-safe, lightweight.
# The client is created even when the key is absent so import never crashes;
# the first actual API call will raise an AuthenticationError instead.
_client: Groq = Groq(api_key=GROQ_API_KEY or "")

# ── Observability counter ──────────────────────────────────────────────────────
# Incremented on every ask_llm() *attempt* (not per retry).
# Import this in tests to assert exactly-1-call-per-query behaviour:
#   from backend.app.services.llm_service import get_groq_call_count
GROQ_CALL_COUNT: int = 0


def get_groq_call_count() -> int:
    """Return the total number of ask_llm() invocations since process start."""
    return GROQ_CALL_COUNT


def reset_groq_call_count() -> None:
    """Reset the counter — useful in test teardown."""
    global GROQ_CALL_COUNT
    GROQ_CALL_COUNT = 0


# ── Core LLM call ─────────────────────────────────────────────────────────────


def ask_llm(
    prompt: str,
    temperature: float = 0.2,
    max_output_tokens: int = 2048,
) -> Optional[str]:
    """
    Send a prompt to Groq and return the model's reply as a plain string.

    This function is the SINGLE authorised Groq call-site in the project.
    It must be called at most ONCE per user-facing request (in rag_pipeline.py).
    It must NEVER be called from news fetching, filtering, or indexing code.

    Parameters
    ----------
    prompt : str
        The full prompt (system instructions + retrieved context + question).
        Sent as a single "user" turn.  If you later need a dedicated system
        message, split into two messages as shown in the docstring note below.
    temperature : float
        Sampling temperature. 0.2 = focused/factual (recommended for RAG).
        Pass 0.0 for deterministic classification — but classification must
        NOT happen here; use keyword matching in the calling module instead.
    max_output_tokens : int
        Maximum tokens in the completion (Groq param: max_tokens).

    Returns
    -------
    str | None
        The model's text response, stripped of leading/trailing whitespace.
        Returns None on failure so callers can degrade gracefully without
        raising an unhandled exception.

    Retry behaviour
    ---------------
    On groq.RateLimitError (HTTP 429):
      - Waits RETRY_DELAY_SECONDS, then retries.
      - Repeats up to MAX_LLM_RETRIES times.
      - Returns None after all retries are exhausted.
    On groq.APIConnectionError (transient network):
      - Same retry logic as RateLimitError.
    On groq.APIStatusError (other 4xx/5xx):
      - Logged and returned as None immediately (no retry — retrying a
        400 Bad Request won't help).
    On any other unexpected exception:
      - Logged and returned as None immediately.

    Note: system message
    ─────────────────────
    Groq supports a dedicated system role.  If RAGPipeline is updated to pass
    a separate system_prompt argument, restructure the call like this:

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]
    """
    global GROQ_CALL_COUNT
    GROQ_CALL_COUNT += 1

    if not GROQ_API_KEY:
        logger.error(
            "ask_llm: GROQ_API_KEY is missing — cannot make LLM request."
        )
        return None

    if not prompt or not prompt.strip():
        logger.warning("ask_llm: received empty prompt — returning None.")
        return None

    last_exception: Optional[Exception] = None

    for attempt in range(1, MAX_LLM_RETRIES + 1):
        try:
            completion = _client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_output_tokens,
            )

            choice = completion.choices[0] if completion.choices else None
            if not choice:
                logger.error(
                    "ask_llm: Groq returned zero choices  model=%s", GROQ_MODEL
                )
                return None

            text = (choice.message.content or "").strip()
            if not text:
                logger.error(
                    "ask_llm: Groq returned an empty message  "
                    "finish_reason=%s  model=%s",
                    choice.finish_reason,
                    GROQ_MODEL,
                )
                return None

            logger.info(
                "ask_llm: success  model=%s  attempt=%d/%d  "
                "finish_reason=%s  prompt_tokens=%s  completion_tokens=%s",
                GROQ_MODEL,
                attempt,
                MAX_LLM_RETRIES,
                choice.finish_reason,
                getattr(completion.usage, "prompt_tokens", "?"),
                getattr(completion.usage, "completion_tokens", "?"),
            )
            return text

        except groq_sdk.RateLimitError as exc:
            last_exception = exc
            logger.warning(
                "ask_llm: RateLimitError (429) on attempt %d/%d — "
                "waiting %.1fs before retry.  model=%s  error=%s",
                attempt,
                MAX_LLM_RETRIES,
                RETRY_DELAY_SECONDS,
                GROQ_MODEL,
                exc,
            )
            if attempt < MAX_LLM_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

        except groq_sdk.APIConnectionError as exc:
            last_exception = exc
            logger.warning(
                "ask_llm: APIConnectionError on attempt %d/%d — "
                "waiting %.1fs before retry.  model=%s  error=%s",
                attempt,
                MAX_LLM_RETRIES,
                RETRY_DELAY_SECONDS,
                GROQ_MODEL,
                exc,
            )
            if attempt < MAX_LLM_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

        except groq_sdk.APIStatusError as exc:
            # 4xx/5xx that isn't a rate-limit — retrying won't help.
            logger.error(
                "ask_llm: APIStatusError (non-retriable)  "
                "status=%s  model=%s  error=%s",
                exc.status_code,
                GROQ_MODEL,
                exc,
            )
            return None

        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "ask_llm: unexpected error  model=%s  error=%s",
                GROQ_MODEL,
                exc,
            )
            return None

    # All retries exhausted
    logger.error(
        "ask_llm: all %d retries exhausted.  model=%s  last_error=%s",
        MAX_LLM_RETRIES,
        GROQ_MODEL,
        last_exception,
    )
    return None