# extractors/pdf_extractor.py
import io
import re
import requests
from fastapi import HTTPException

import pdfplumber

from config import settings
from .pdf_unlock import is_pdf_encrypted, unlock_pdf_with_fallbacks


def extract_text_native_pdf(file_bytes: bytes) -> str:
    """Extrae texto de PDF usando pdfplumber con división inteligente de zonas"""
    try:
        all_pages_text = []

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                h = page.height
                w = page.width

                # Zonas de la página
                header_box = (0, 0, w, h * 0.12)
                body_box = (0, h * 0.12, w, h * 0.88)
                footer_box = (0, h * 0.88, w, h)

                header_text = (page.within_bbox(header_box).extract_text() or "").strip()
                body_text = (page.within_bbox(body_box).extract_text() or "").strip()
                footer_text = (page.within_bbox(footer_box).extract_text() or "").strip()

                # Extraer tablas
                tables_text = []
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            line = " | ".join(str(cell).strip() for cell in row if cell is not None)
                            if line.strip():
                                tables_text.append(line)

                # Construir página
                page_parts = []
                if header_text:
                    page_parts.append(f"[ENCABEZADO]\n{header_text}")
                if tables_text:
                    page_parts.append("[TABLAS]\n" + "\n".join(tables_text))
                if body_text:
                    page_parts.append(f"[CUERPO]\n{body_text}")
                if footer_text:
                    page_parts.append(f"[PIE DE PÁGINA]\n{footer_text}")

                all_pages_text.append("\n".join(page_parts))

        return "\n\n=== NUEVA PÁGINA ===\n\n".join(all_pages_text).strip()

    except Exception as e:
        print(f"[pdfplumber] Error en página: {e}")
        return ""


def extract_text_ocr(file_bytes: bytes, content_type: str) -> str:
    """Extrae texto usando OCR.space como fallback"""
    if not settings.OCR_SPACE_API_KEY:
        raise HTTPException(status_code=500, detail="OCR_SPACE_API_KEY no configurada en .env")

    try:
        ext = "pdf" if "pdf" in content_type.lower() else "jpg"
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": (f"document.{ext}", file_bytes)},
            data={
                "apikey": settings.OCR_SPACE_API_KEY,
                "language": "spa",
                "isOverlayRequired": False,
                "OCREngine": 2,
                "scale": True,
                "isTable": True,
            },
            timeout=90
        )
        result = response.json()

        if result.get("IsErroredOnProcessing"):
            error = result.get("ErrorMessage", "Error desconocido en OCR")
            raise HTTPException(status_code=400, detail=str(error))

        parsed_results = result.get("ParsedResults", [])
        return "\n".join(item.get("ParsedText", "") for item in parsed_results).strip()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en OCR.Space: {str(e)}")


def extract_text(file_bytes: bytes, content_type: str, url_file: str = "") -> str:
    """Función principal de extracción de texto"""
    # Si es PDF, intentar extracción nativa primero
    if "pdf" in content_type.lower():
        # Intentar desbloquear si está protegido
        if is_pdf_encrypted(file_bytes):
            # El unlock se maneja normalmente en analysis_service
            pass

        native_text = extract_text_native_pdf(file_bytes)
        if len(native_text.strip()) >= settings.PDF_MIN_CHARS:
            print(f"[EXTRACTOR] Texto nativo OK ({len(native_text)} caracteres)")
            return native_text

        print("[EXTRACTOR] Texto nativo insuficiente → usando OCR")
        return extract_text_ocr(file_bytes, content_type)

    # Para imágenes directamente usar OCR
    return extract_text_ocr(file_bytes, content_type)