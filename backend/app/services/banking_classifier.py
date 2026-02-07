import os
import google.generativeai as genai


# ============================
# CONFIG
# ============================

API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)

MODEL_NAME = "gemini-flash-latest"


# ============================
# LLM CLASSIFIER
# ============================

def is_banking_content_llm(title: str, description: str) -> bool:
    """
    Uses Gemini LLM to check if content is banking/finance related
    """

    if not API_KEY:
        # If no API key → allow by default (fallback)
        return True


    try:

        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""
You are a classifier.

Check whether the following content is related to banking, finance,
RBI, loans, credit, stock market, economy, or financial policy.

Reply ONLY with YES or NO.

Title: {title}

Description: {description}
"""

        response = model.generate_content(prompt)

        try:
            result = response.text.strip().upper()
        except Exception:
            # If response has no parts, treat as non-banking to be safe
            return False

        if "YES" in result:
            return True
        else:
            return False

    except Exception as e:

        print("LLM classification error:", e)

        # Fallback → don't block news
        return True
