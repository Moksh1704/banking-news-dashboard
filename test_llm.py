from backend.app.services.llm_service import ask_llm

prompt = """
Explain RBI repo rate in simple terms for a bank employee.
"""

response = ask_llm(prompt)
print("LLM RESPONSE:\n")
print(response)
