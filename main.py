# main.py

"""
════════════════════════════════════════════════════════════════════════════════
  LabAnalyzer v3.0 — Batch Extracción Clínica + Evolución (Ollama Edition)
════════════════════════════════════════════════════════════════════════════════
  - Procesamiento batch por rango de fechas
  - LLM via Ollama local (sin Groq)
  - Clasificación FHIR y asignación de códigos CUPS
  - Evolución clínica longitudinal con análisis de tendencias
  - Narrativas clínicas automatizadas
  - Password de PDF = identificacion del usuario (sin interacción)
════════════════════════════════════════════════════════════════════════════════
"""
import sys
from pathlib import Path

# === SOLUCIÓN AL PROBLEMA DE IMPORTS ===
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

print(f"✅ Directorio base agregado al PATH: {BASE_DIR}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import settings

# Routers
from routers.health import router as health_router
from routers.batch import router as batch_router
from routers.analyze import router as analyze_router
from routers.evolucion import router as evolucion_router

app = FastAPI(
    title="LabAnalyzer v3.0 — Teker Salud",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(health_router)
app.include_router(batch_router, prefix="/batch", tags=["batch"])
app.include_router(analyze_router, tags=["analyze"])
app.include_router(evolucion_router, tags=["evolucion"])


@app.on_event("startup")
async def startup_event():
    try:
        from core.cups import load_cups_catalog
        load_cups_catalog()
        print(f"🚀 LabAnalyzer v3.0 iniciado correctamente")
        print(f"📊 Modelo Ollama: {settings.OLLAMA_MODEL}")
    except Exception as e:
        print(f"⚠️ Error en startup: {e}")

from fastapi.responses import HTMLResponse
from pathlib import Path

@app.get("/", response_class=HTMLResponse)
def home():
    html_path = Path(__file__).parent / "templates" / "index.html"
    return html_path.read_text(encoding="utf-8")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)