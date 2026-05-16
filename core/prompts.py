# core/prompts.py
"""
Prompts especializados para Ollama
"""

_SYSTEM_ES = """Eres un experto en interoperabilidad FHIR y clasificación de exámenes diagnósticos.
Extrae TODOS los exámenes del texto proporcionado y genera la estructura exacta solicitada.
Devuelve ÚNICAMENTE JSON válido."""

_SYSTEM_EN = """You are an expert in FHIR interoperability and diagnostic exam classification.
Extract ALL exams and return ONLY valid JSON with the exact structure."""

def get_system_prompt(lang: str = "es") -> str:
    return _SYSTEM_ES if lang != "en" else _SYSTEM_EN


def get_user_prompt(texto_documento: str, lang: str = "es") -> str:
    base = """Analiza el siguiente texto con uno o varios exámenes clínicos.
Devuelve SOLO JSON con esta estructura exacta:"""

    estructura = """
{
  "profesional_documento": {"nombre": null, "cargo": null, "registro": null},
  "institucion_documento": null,
  "examenes": [
    {
      "fecha": "YYYYMMDD",
      "tipo_examen": "STRING CORTO EN MAYÚSCULAS",
      "disciplina": "string",
      "subcategoria": "string",
      "fhir_category": "LAB|RAD|PAT|CARD|OT",
      "resultados": [
        {
          "parametro": "string",
          "valor": "string",
          "unidad": null,
          "referencia": null,
          "estado": "normal|alto|bajo|sin_dato"
        }
      ],
      "notas_clinicas": [],
      "notas_medico": null,
      "notas_paciente": null
    }
  ]
}
"""

    return f"{base}\n\n{estructura}\n\nTexto del documento:\n{texto_documento}"