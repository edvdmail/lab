# core/classification.py
"""
Clasificación FHIR y por disciplinas para exámenes de laboratorio e imágenes.
"""

_CLASIF_KEYWORDS = {
    "Laboratorio Clínico": [
        "hemograma", "hematología", "bioquímica", "glucosa", "creatinina", "colesterol",
        "triglicéridos", "urea", "uricemia", "bilirrubina", "transaminasa", "ast", "alt",
        "laboratorio", "bacteriología", "microbiología", "cultivo", "antibiograma",
        "serología", "elisa", "pcr", "coagulación", "tp", "tpt", "tsh", "t3", "t4",
        "hormona", "cortisol", "orina", "parcial de orina"
    ],
    "Imagenología": [
        "rayos x", "rx", "radiografía", "ecografía", "ecografia", "tomografía", "tac",
        "resonancia", "mri", "rm", "mamografía", "densitometría", "gammagrafía"
    ],
    "Patología": [
        "biopsia", "histología", "citología", "anatomía patológica", "papanicolau", "pap"
    ],
    "Cardiología Diagnóstica": [
        "ecg", "electrocardiograma", "holter", "ecocardiograma", "ergometría"
    ]
}

_SUBCATEG_KEYWORDS = {
    "Hematología": ["hemograma", "leucocito", "eritrocito", "plaqueta", "hematocrito", "hemoglobina"],
    "Bioquímica": ["glucosa", "creatinina", "urea", "colesterol", "triglicéridos", "bilirrubina", "transaminasa"],
    "Microbiología": ["cultivo", "antibiograma", "gram"],
    "Coagulación": ["tp", "tpt", "inr", "fibrinógeno"],
    "Endocrinología": ["tsh", "t3", "t4", "cortisol", "hormona"],
    "Radiografía (RX)": ["rayos x", "rx", "radiografía"],
    "Ecografía (US)": ["ecografía", "ecografia", "ultrasonido"],
    "Tomografía Computarizada (TAC/CT)": ["tomografía", "tac"],
    "Resonancia Magnética (RM/MRI)": ["resonancia", "mri", "rm"],
    "Mamografía": ["mamografía"],
}


def clasificar_examen(tipo_examen: str) -> dict:
    """
    Clasifica un examen según su nombre y devuelve disciplina, subcategoría y categoría FHIR.
    """
    if not tipo_examen:
        return {
            "disciplina": "Laboratorio Clínico",
            "subcategoria": "Bioquímica",
            "fhir_category": "LAB"
        }

    texto = tipo_examen.lower().strip()

    disciplina = "Laboratorio Clínico"
    fhir_category = "LAB"
    subcategoria = "Bioquímica"

    # 1. Determinar Disciplina principal
    for disc, keywords in _CLASIF_KEYWORDS.items():
        if any(kw in texto for kw in keywords):
            disciplina = disc
            if disc == "Imagenología":
                fhir_category = "RAD"
            elif disc == "Patología":
                fhir_category = "PAT"
            elif disc == "Cardiología Diagnóstica":
                fhir_category = "CARD"
            break

    # 2. Determinar Subcategoría
    for sub, keywords in _SUBCATEG_KEYWORDS.items():
        if any(kw in texto for kw in keywords):
            subcategoria = sub
            break

    return {
        "disciplina": disciplina,
        "subcategoria": subcategoria,
        "fhir_category": fhir_category
    }


# Función auxiliar para normalizar resultados (usada en analysis_service)
def enrich_exam_with_classification(exam: dict) -> dict:
    """Enriquece un examen con clasificación FHIR si no la tiene"""
    if not exam.get("fhir_category") or not exam.get("disciplina"):
        clasif = clasificar_examen(exam.get("tipo_examen", ""))
        exam.setdefault("disciplina", clasif["disciplina"])
        exam.setdefault("subcategoria", clasif["subcategoria"])
        exam.setdefault("fhir_category", clasif["fhir_category"])
    return exam