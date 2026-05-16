# services/analysis_service.py
import json
import requests
from typing import Dict, Any

from config import settings

# Imports corregidos (usando imports relativos desde la raíz)
from core.cups import asignar_cups
from core.classification import enrich_exam_with_classification
from extractors.pdf_extractor import extract_text
from extractors.pdf_unlock import unlock_pdf_with_fallbacks
from repositories.oracle_repo import OracleRepo
from core.utils import (
    clean_json, 
    build_nombre_alternativo, 
    download_file, 
    descargar_con_fallback
)
from core.ollama import ollama_chat
from core.prompts import get_system_prompt, get_user_prompt


class AnalysisService:
    
    def __init__(self):
        self.repo = OracleRepo()

    async def analizar_archivo(
        self,
        url: str = "",
        id_usuario: int = None,
        id_archivo: int = None,
        identificacion: str = "",
        output_lang: str = "es",
        force_reprocess: bool = False,
        opcion1: str = "",
        opcion2: str = "",
        id_descripcion: int = 0,
    ) -> Dict[str, Any]:
        """Servicio principal de análisis de un archivo"""

        # 1. Verificar caché
        if id_archivo and not force_reprocess:
            cached = self.repo.check_ya_analizado(id_archivo)
            if cached:
                try:
                    analisis_str = cached[0][0].read() if hasattr(cached[0][0], "read") else str(cached[0][0])
                    result = json.loads(analisis_str)
                    result["cached"] = True
                    return result
                except:
                    pass

        # 2. Descargar archivo (con fallback opcion1/opcion2)
        try:
            if opcion1 or opcion2:
                file_bytes, content_type, nombre_usado = descargar_con_fallback(opcion1, opcion2)
            else:
                file_bytes, content_type = download_file(url)
        except Exception as e:
            return {"error": f"Error descarga: {str(e)}", "examenes": []}

        # 3. Desbloquear PDF si está protegido
        ext = "pdf" if "pdf" in content_type.lower() else "jpg"
        if ext == "pdf":
            unlocked = unlock_pdf_with_fallbacks(file_bytes, identificacion)
            if unlocked:
                file_bytes = unlocked

        # 4. Extraer texto (pdfplumber + OCR fallback)
        text = extract_text(file_bytes, content_type, url or nombre_usado)
        if len(text.strip()) < settings.PDF_MIN_CHARS:
            return {"error": "NO_SE_PUDO_LEER_DOCUMENTO", "examenes": []}

        # 5. Llamada a Ollama
        system_prompt = get_system_prompt(output_lang)
        user_prompt = get_user_prompt(text, output_lang)

        try:
            raw_response = ollama_chat(user_prompt, system=system_prompt)
            raw_parsed = json.loads(clean_json(raw_response))
        except Exception as e:
            return {"error": "NO_SE_PUDO_PARSEAR_JSON", "raw_output": raw_response[:800]}

        # 6. Normalizar y enriquecer con CUPS + clasificación
        result = self._normalize_result(raw_parsed, id_usuario, id_archivo)

        # 7. Guardar en Oracle
        if id_archivo:
            self._save_to_database(result, id_archivo, id_descripcion, opcion2)

        result["cached"] = False
        return result

    def _normalize_result(self, raw_parsed: dict, id_usuario: int, id_archivo: int) -> dict:
        """Normaliza y enriquece el resultado con CUPS y clasificación"""
        from core.utils import normalize_to_multi
        return normalize_to_multi(raw_parsed, id_usuario, id_archivo)

    def _save_to_database(self, result: dict, id_archivo: int, id_descripcion: int, opcion2: str):
        """Guarda el análisis en Oracle"""
        examenes = result.get("examenes", [])
        
        if int(id_descripcion or 0) == -22 and opcion2:
            nombre_alt = str(opcion2).strip()
        elif len(examenes) == 1:
            nombre_alt = build_nombre_alternativo(
                examenes[0].get("tipo_examen", "Examen"),
                examenes[0].get("fecha", "")
            )
        else:
            nombre_alt = build_nombre_alternativo(f"MultiExamen_{len(examenes)}", "")

        result["nombre_alternativo"] = nombre_alt

        try:
            analisis_json = json.dumps(result, ensure_ascii=False)
            self.repo.save_analysis(id_archivo, nombre_alt, analisis_json)
        except Exception as e:
            print(f"[AnalysisService] Error guardando en BD: {e}")