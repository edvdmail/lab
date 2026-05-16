# core/ollama.py
import requests
from config import settings
from fastapi import HTTPException

def ollama_chat(prompt: str, system: str = "", force_json: bool = True) -> str:
    """Cliente Ollama reutilizable"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": 8192,
            "repeat_penalty": 1.1,
        }
    }
    if force_json:
        payload["format"] = "json"

    try:
        resp = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=settings.OLLAMA_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error Ollama: {str(e)}")