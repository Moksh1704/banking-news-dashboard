import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = genai.GenerativeModel("gemini-1.5-flash-latest")

def ask_gemini(prompt: str) -> str:
    try:
        response = MODEL.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"[LLM Error] {e}"
