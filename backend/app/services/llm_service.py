import subprocess


def ask_ollama(prompt: str) -> str:
    process = subprocess.Popen(
        ["ollama", "run", "tinyllama"],  # 🔒 FORCE tinyllama
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )

    stdout, stderr = process.communicate(prompt, timeout=180)

    output = (stdout or "").strip()
    if not output:
        output = (stderr or "").strip()

    if not output:
        return "[No response from LLM]"

    return output
