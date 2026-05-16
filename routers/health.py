# routers/health.py
from fastapi import APIRouter
from config import settings
import requests

router = APIRouter()   # ← Sin prefix

@router.get("/health")
def health():
    """Verifica estado de Ollama"""
    try:
        resp = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=8)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("name") for m in data.get("models", [])]

        return {
            "status": "ok",
            "ollama_models": models,
            "model_activo": settings.OLLAMA_MODEL,
            "version": "3.0.0"
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}