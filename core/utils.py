# core/utils.py
import re
import unicodedata
import requests
import urllib.parse
from typing import Optional, Tuple
from datetime import datetime
from config import settings


# ── Texto / JSON ──────────────────────────────────────────────────────────────

def clean_json(raw: str) -> str:
    """Extrae el bloque JSON válido del texto que devuelve el LLM."""
    try:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            return raw[start:end]
        return raw
    except Exception:
        return raw


def build_nombre_alternativo(tipo_examen: str, fecha: str = "") -> str:
    """Genera nombre alternativo para guardar en BD."""
    nombre = tipo_examen or "Examen"
    nombre = unicodedata.normalize("NFD", nombre)
    nombre = "".join(c for c in nombre if unicodedata.category(c) != "Mn")
    nombre = re.sub(r"[^a-zA-Z0-9\s]", "", nombre).strip()
    nombre = re.sub(r"\s+", "_", nombre)
    if fecha and re.match(r"^\d{8}$", str(fecha)):
        return f"{nombre}_{fecha}"
    return nombre


# ── Descarga ──────────────────────────────────────────────────────────────────

def download_file(url: str) -> Tuple[bytes, str]:
    resp = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; LabAnalyzer/2.0)"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("content-type", "")


def descargar_con_fallback(opcion1: str, opcion2: str) -> Tuple[bytes, str, str]:
    base = settings.BASE_URL_FILES
    for nombre in [opcion1, opcion2]:
        if not nombre:
            continue
        try:
            url = base + urllib.parse.quote(str(nombre).strip(), safe="/._-")
            file_bytes, content_type = download_file(url)
            return file_bytes, content_type, nombre
        except Exception:
            continue
    raise Exception("No se pudo descargar el archivo con ninguno de los nombres")


# ── Fechas ────────────────────────────────────────────────────────────────────

_MES_MAP = {
    "ene": "Jan", "feb": "Feb", "mar": "Mar", "abr": "Apr",
    "may": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
    "sep": "Sep", "oct": "Oct", "nov": "Nov", "dic": "Dec",
}
_DATE_FMTS = [
    "%Y%m%d",
    "%d/%m/%Y", "%Y/%m/%d",
    "%d-%m-%Y", "%Y-%m-%d",
    "%d-%b-%Y", "%d %b %Y",
    "%d/%m/%Y %H:%M",
    "%d.%m.%Y",
    "%Y-%m-%dT%H:%M:%S",
]


def _parse_fecha_to_datetime(raw) -> Optional[datetime]:
    if not raw:
        return None
    s = str(raw).strip()
    for es, en in _MES_MAP.items():
        s = re.sub(rf"\b{es}\.?\b", en, s, flags=re.IGNORECASE)
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s[:len(fmt)], fmt)
        except Exception:
            continue
    return None


def normalizar_fecha_yyyymmdd(raw) -> Optional[str]:
    """Convierte cualquier formato de fecha a YYYYMMDD, o None si no parsea."""
    dt = _parse_fecha_to_datetime(raw)
    return dt.strftime("%Y%m%d") if dt else None


def _extraer_valor_numerico(valor_str) -> Optional[float]:
    if not valor_str:
        return None
    m = re.search(r"-?\d+[.,]?\d*", str(valor_str))
    if m:
        try:
            return float(m.group(0).replace(",", "."))
        except Exception:
            return None
    return None


# ── Normalización de estado de resultado ─────────────────────────────────────

def _normalizar_estado_resultado(estado) -> str:
    if not estado:
        return "sin_dato"
    e = str(estado).lower().strip()
    if e in ("normal", "dentro de rango", "dentro del rango", "en rango"):
        return "normal"
    if e in ("alto", "elevado", "high", "h", "por encima"):
        return "alto"
    if e in ("bajo", "low", "l", "por debajo"):
        return "bajo"
    if e in ("normal", "alto", "bajo", "sin_dato"):
        return e
    return "sin_dato"


# ── Clasificación FHIR ────────────────────────────────────────────────────────

_CLASIF_KW = {
    "RAD":  ["rayos x", "rx", "radiografia", "ecografia", "ecografía", "tomografia",
             "tac", "resonancia", "mri", "rm", "mamografia", "densitometria",
             "gammagrafia", "ultrasonido"],
    "PAT":  ["biopsia", "histologia", "citologia", "anatomia patologica",
             "papanicolau", "pap"],
    "CARD": ["ecg", "electrocardiograma", "holter", "ecocardiograma",
             "ergometria", "mapa"],
}
_DISCIPLINA_MAP = {
    "LAB":  ("Laboratorio Clínico",      "Bioquímica"),
    "RAD":  ("Imagenología",             "Radiología"),
    "PAT":  ("Patología",                "Anatomía Patológica"),
    "CARD": ("Cardiología Diagnóstica",  "Cardiología"),
    "OT":   ("Otro",                     "Otro"),
}


def normalizar_clasificacion(
    tipo_examen: str,
    disciplina: Optional[str] = None,
    subcategoria: Optional[str] = None,
    fhir_category: Optional[str] = None,
) -> dict:
    """Devuelve disciplina, subcategoria y fhir_category normalizados."""
    # Si ya viene completo del LLM, respetarlo
    if fhir_category and fhir_category.upper() in _DISCIPLINA_MAP:
        fhir = fhir_category.upper()
        disc, sub = _DISCIPLINA_MAP[fhir]
        return {
            "fhir_category": fhir,
            "disciplina":    disciplina or disc,
            "subcategoria":  subcategoria or sub,
        }
    # Inferir por palabras clave
    texto = (tipo_examen or "").lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    for fhir, kws in _CLASIF_KW.items():
        if any(kw in texto for kw in kws):
            disc, sub = _DISCIPLINA_MAP[fhir]
            return {"fhir_category": fhir, "disciplina": disc, "subcategoria": sub}
    return {"fhir_category": "LAB", "disciplina": "Laboratorio Clínico", "subcategoria": "Bioquímica"}


def _infer_imaging_modality(tipo_examen: str) -> Optional[str]:
    t = (tipo_examen or "").lower()
    if any(k in t for k in ["tac", "tomografia", "ct"]):
        return "CT"
    if any(k in t for k in ["resonancia", "mri", "rm"]):
        return "MR"
    if any(k in t for k in ["ecografia", "ecografía", "ultrasonido", "us"]):
        return "US"
    if any(k in t for k in ["rx", "rayos", "radiografia"]):
        return "DX"
    if any(k in t for k in ["mamografia"]):
        return "MG"
    return None


# ── normalize_to_multi ────────────────────────────────────────────────────────

def normalize_to_multi(
    raw_parsed,
    id_usuario: int,
    id_archivo: Optional[int],
    source_text: str = "",
) -> dict:
    """
    Normaliza la respuesta del LLM al formato estándar con lista de examenes,
    enriquece cada examen con clasificación FHIR y código CUPS.
    """
    from core.cups import asignar_cups  # import aquí para evitar circular

    def _safe_dict(x):
        return x if isinstance(x, dict) else {}

    def fix_exam(exam: dict, prof_doc: dict, inst_doc: Optional[str]) -> dict:
        exam = _safe_dict(exam)
        exam.setdefault("resultados", [])
        exam.setdefault("notas_clinicas", [])

        # Fecha → YYYYMMDD
        exam["fecha"] = normalizar_fecha_yyyymmdd(exam.get("fecha"))

        if not exam.get("tipo_examen"):
            exam["tipo_examen"] = "EXAMEN"

        # Clasificación FHIR
        clasif = normalizar_clasificacion(
            exam.get("tipo_examen", ""),
            exam.get("disciplina"),
            exam.get("subcategoria"),
            exam.get("fhir_category"),
        )
        exam["disciplina"]    = clasif["disciplina"]
        exam["subcategoria"]  = clasif["subcategoria"]
        exam["fhir_category"] = clasif["fhir_category"]

        # Profesional / institución desde cabecera del documento
        if not exam.get("profesional") and prof_doc.get("nombre"):
            exam["profesional"]           = prof_doc.get("nombre")
            exam["cargo_profesional"]     = exam.get("cargo_profesional") or prof_doc.get("cargo")
            exam["registro_profesional"]  = exam.get("registro_profesional") or prof_doc.get("registro")
        if not exam.get("institucion") and inst_doc:
            exam["institucion"] = inst_doc

        fhir_cat = (exam.get("fhir_category") or "LAB").upper()

        # CUPS del examen
        cups_exam = asignar_cups(
            tipo_examen=exam.get("tipo_examen", ""),
            fhir_category=fhir_cat,
            codigo_cups_llm=exam.get("codigo_cups"),
        )
        exam["codigo_cups"] = cups_exam["codigo_cups"]
        exam["nombre_cups"] = cups_exam["nombre_cups"]
        exam["cups_score"]  = cups_exam["cups_score"]
        exam["cups_fuente"] = cups_exam["cups_fuente"]

        # Resultados
        fixed_results = []
        for res in exam.get("resultados", []):
            if not isinstance(res, dict):
                continue
            res.setdefault("parametro",  "Parametro")
            res.setdefault("valor",      None)
            res.setdefault("unidad",     None)
            res.setdefault("referencia", None)
            res.setdefault("estado",     "sin_dato")
            res.setdefault("metodo",     None)
            res.setdefault("nota",       None)
            res["estado"] = _normalizar_estado_resultado(res.get("estado"))

            if fhir_cat in {"RAD", "PAT", "CARD", "OT"}:
                res["codigo_cups"] = res.get("codigo_cups")
                res["nombre_cups"] = None
                res["cups_score"]  = 0.0
                res["cups_fuente"] = "n/a"
            else:
                cups_p = asignar_cups(
                    tipo_examen=res.get("parametro", ""),
                    fhir_category=fhir_cat,
                    codigo_cups_llm=res.get("codigo_cups"),
                    score_min=0.25,
                )
                res["codigo_cups"] = cups_p["codigo_cups"]
                res["nombre_cups"] = cups_p["nombre_cups"]
                res["cups_score"]  = cups_p["cups_score"]
                res["cups_fuente"] = cups_p["cups_fuente"]

            fixed_results.append(res)

        exam["resultados"] = fixed_results

        # FHIR imaging study (solo RAD)
        if fhir_cat == "RAD":
            exam["fhir_imaging_study"] = exam.get("fhir_imaging_study") or {
                "modalidad_dicom": _infer_imaging_modality(exam.get("tipo_examen", "")),
                "region_anatomica": exam.get("region_anatomica"),
            }
        else:
            exam["fhir_imaging_study"] = None

        return exam

    # ── Parsear estructura raíz ───────────────────────────────────────────────
    prof_doc = {}
    inst_doc = None
    examenes = []

    if isinstance(raw_parsed, list):
        examenes = raw_parsed
    elif isinstance(raw_parsed, dict):
        prof_doc = _safe_dict(raw_parsed.get("profesional_documento"))
        inst_doc = raw_parsed.get("institucion_documento")
        if isinstance(raw_parsed.get("examenes"), list):
            examenes = raw_parsed["examenes"]
        else:
            examenes = [raw_parsed]

    examenes = [fix_exam(e, prof_doc, inst_doc) for e in examenes if isinstance(e, dict)]

    return {
        "profesional_documento": prof_doc or None,
        "institucion_documento": inst_doc,
        "examenes":              examenes,
        "id_usuario":            id_usuario,
        "id_archivo":            id_archivo,
        "multi":                 len(examenes) > 1,
    }