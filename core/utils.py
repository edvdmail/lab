# core/utils.py
import re
import unicodedata
import requests
import urllib.parse
from typing import Tuple
from datetime import datetime
from config import settings


def clean_json(raw: str) -> str:
    """Extrae el bloque JSON válido del texto que devuelve Ollama"""
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return raw[start:end]
        return raw
    except:
        return raw


def build_nombre_alternativo(tipo_examen: str, fecha: str = "") -> str:
    """Genera nombre alternativo para guardar en BD"""
    nombre = tipo_examen or "Examen"
    nombre = unicodedata.normalize("NFD", nombre)
    nombre = "".join(c for c in nombre if unicodedata.category(c) != "Mn")
    nombre = re.sub(r"[^a-zA-Z0-9\s]", "", nombre).strip()
    nombre = re.sub(r"\s+", "_", nombre)

    if fecha and re.match(r"^\d{8}$", fecha):
        return f"{nombre}_{fecha}"
    return nombre


def download_file(url: str) -> Tuple[bytes, str]:
    """Descarga un archivo desde URL"""
    resp = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; LabAnalyzer/3.0)"},
        timeout=30
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("content-type", "")


def descargar_con_fallback(opcion1: str, opcion2: str) -> Tuple[bytes, str, str]:
    """Intenta descargar con fallback opcion1 → opcion2"""
    base = settings.BASE_URL_FILES
    for nombre in [opcion1, opcion2]:
        if not nombre:
            continue
        try:
            url = base + urllib.parse.quote(str(nombre).strip(), safe="/._-")
            file_bytes, content_type = download_file(url)
            return file_bytes, content_type, nombre
        except:
            continue
    raise Exception("No se pudo descargar el archivo con ninguno de los nombres")


# Funciones que estaban dando error de import
def _extraer_valor_numerico(valor_str: str):
    """Extrae número de un string (valor de laboratorio)"""
    if not valor_str:
        return None
    m = re.search(r"-?\d+[.,]?\d*", str(valor_str))
    if m:
        try:
            return float(m.group(0).replace(",", "."))
        except:
            return None
    return None


def _parse_fecha_to_datetime(raw: str):
    """Convierte fecha en string a objeto datetime"""
    if not raw:
        return None

    formatos = [
        "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d",
        "%d-%b-%Y", "%d %b %Y", "%d/%m/%Y %H:%M", "%Y%m%d",
        "%d.%m.%Y"
    ]

    raw_norm = str(raw).strip()
    mes_map = {
        "ene": "Jan", "feb": "Feb", "mar": "Mar", "abr": "Apr",
        "may": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
        "sep": "Sep", "oct": "Oct", "nov": "Nov", "dic": "Dec",
    }

    for es, en in mes_map.items():
        raw_norm = re.sub(rf"\b{es}\.?\b", en, raw_norm, flags=re.IGNORECASE)

    for fmt in formatos:
        try:
            return datetime.strptime(raw_norm, fmt)
        except:
            continue
    return None