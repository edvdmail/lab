# core/cups.py
import json
from pathlib import Path
import pandas as pd
import re
import unicodedata
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CUPS_CATALOG_PATH = Path(__file__).parent.parent / "cups_catalog_integrado.json"

_CUPS_CATALOG = None
_CUPS_VEC = None
_CUPS_MAT = None


def _norm_cups(s: str) -> str:
    """Normaliza texto para búsqueda CUPS"""
    s = str(s).upper().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_cups_catalog(force_reload: bool = False):
    """Carga el catálogo grande de CUPS"""
    global _CUPS_CATALOG, _CUPS_VEC, _CUPS_MAT

    if _CUPS_CATALOG is not None and not force_reload:
        return _CUPS_CATALOG

    try:
        with open(CUPS_CATALOG_PATH, encoding='utf-8') as f:
            data = json.load(f)

        df = pd.DataFrame(data)
        df["_norm"] = df["NOMBRE_PROCEDIMIENTO"].apply(_norm_cups)
        
        _CUPS_CATALOG = df

        _CUPS_VEC = TfidfVectorizer(ngram_range=(1, 3), analyzer="word", min_df=1)
        _CUPS_MAT = _CUPS_VEC.fit_transform(_CUPS_CATALOG["_norm"])

        print(f"✅ [CUPS] Catálogo cargado correctamente: {len(_CUPS_CATALOG)} procedimientos")
        return _CUPS_CATALOG

    except Exception as e:
        print(f"❌ Error cargando cups_catalog_integrado.json: {e}")
        return pd.DataFrame()


def asignar_cups(
    tipo_examen: str, 
    fhir_category: str = "", 
    codigo_cups_llm=None, 
    score_min: float = 0.20
) -> dict:
    """Asigna código CUPS usando el catálogo grande"""
    empty = {
        "codigo_cups": None, 
        "nombre_cups": None, 
        "cups_score": 0.0, 
        "cups_fuente": "sin_match"
    }

    if _CUPS_CATALOG is None or _CUPS_CATALOG.empty:
        load_cups_catalog()

    if _CUPS_CATALOG.empty:
        return empty

    # Si el LLM ya devolvió un código válido
    if codigo_cups_llm:
        hit = _CUPS_CATALOG[_CUPS_CATALOG["CODIGO_CUPS"].astype(str) == str(codigo_cups_llm).strip()]
        if not hit.empty:
            r = hit.iloc[0]
            return {
                "codigo_cups": r["CODIGO_CUPS"],
                "nombre_cups": r["NOMBRE_PROCEDIMIENTO"],
                "cups_score": 1.0,
                "cups_fuente": "llm"
            }

    # Búsqueda por similitud
    q = _norm_cups(tipo_examen)
    sims = cosine_similarity(_CUPS_VEC.transform([q]), _CUPS_MAT).flatten()
    gi = int(np.argmax(sims))
    bs = float(sims[gi])

    if bs < score_min:
        return {**empty, "cups_score": round(bs, 3)}

    r = _CUPS_CATALOG.iloc[gi]
    return {
        "codigo_cups": r["CODIGO_CUPS"],
        "nombre_cups": r["NOMBRE_PROCEDIMIENTO"],
        "cups_score": round(bs, 3),
        "cups_fuente": "catalogo"
    }