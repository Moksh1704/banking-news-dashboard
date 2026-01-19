import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai

# -------------------------------------------------
# Load environment variables
# -------------------------------------------------
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in environment variables")

# -------------------------------------------------
# Configure Gemini
# -------------------------------------------------
genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "models/gemini-flash-latest"

model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    generation_config={
        "temperature": 0.0,       # deterministic classification
        "max_output_tokens": 5    # only YES / NO needed
    }
)

# -------------------------------------------------
# Prompt template (STRICT YES / NO)
# -------------------------------------------------
CLASSIFICATION_PROMPT = """
You are a strict classifier.

Task:
Decide whether the following content is related to BANKING or FINANCE.

Banking / Finance includes:
- Banks, RBI, central banks
- Interest rates, repo rate
- Loans, credit, deposits
- Financial markets, stocks, bonds
- Monetary or financial policy
- Corporate finance, banking regulation

Rules:
- Respond with ONLY one word: YES or NO
- Do NOT explain
- Do NOT add punctuation

Content:
Title: "{title}"
Description: "{description}"

Answer:
"""

# -------------------------------------------------
# Public function used by youtube_news.py
# -------------------------------------------------
def is_banking_content(title: str, description: str) -> bool:
    """
    Uses Gemini Flash LLM to classify content as banking-related or not.
    Returns True if banking/finance related, else False.
    """

    try:
        prompt = CLASSIFICATION_PROMPT.format(
            title=title or "",
            description=description or ""
        )

        response = model.generate_content(prompt)

        if not response or not response.text:
            logging.warning("Empty LLM response")
            return False

        decision = response.text.strip().upper()

        return decision == "YES"

    except Exception as e:
        logging.error(f"LLM classification error: {e}")
        return False
