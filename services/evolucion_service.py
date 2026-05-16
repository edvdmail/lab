# services/evolucion_service.py
import json
from datetime import datetime
from schemas.request import EvolucionRequest
from repositories.oracle_repo import OracleRepo
from core.utils import _extraer_valor_numerico, _parse_fecha_to_datetime
import numpy as np
from scipy import stats as scipy_stats


class EvolucionService:
    def __init__(self):
        self.repo = OracleRepo()

    async def get_evolucion(self, req: EvolucionRequest):
        rows = self.repo.get_analisis_usuario(req.id_usuario)
        if not rows:
            return {
                "grupos": {},
                "narrativa": "No se encontraron análisis previos para este paciente.",
                "total_archivos": 0,
                "id_usuario": req.id_usuario
            }

        grupos = {}

        for row in rows:
            analisis_clob, _, _, fecha_cargue = row
            try:
                analisis_str = analisis_clob.read() if hasattr(analisis_clob, "read") else str(analisis_clob)
                data = json.loads(analisis_str)
            except:
                continue

            examenes = data.get("examenes", [])
            if not examenes and "resultados" in data:
                examenes = [data]

            for exam in examenes:
                tipo = (exam.get("tipo_examen") or "OTRO").strip().upper()
                fecha_raw = exam.get("fecha") or fecha_cargue
                fecha_dt = _parse_fecha_to_datetime(fecha_raw)
                if not fecha_dt:
                    continue

                if tipo not in grupos:
                    grupos[tipo] = {}

                for r in exam.get("resultados", []):
                    param = (r.get("parametro") or "").strip()
                    if not param:
                        continue

                    valor_num = _extraer_valor_numerico(r.get("valor"))
                    if valor_num is None:
                        continue

                    if param not in grupos[tipo]:
                        grupos[tipo][param] = {
                            "puntos": [],
                            "unidad": r.get("unidad") or "",
                            "referencia": r.get("referencia") or "",
                            "fhir_category": exam.get("fhir_category", "LAB")
                        }

                    fecha_str = fecha_dt.strftime("%d/%m/%Y")
                    if fecha_str not in {p["fecha_str"] for p in grupos[tipo][param]["puntos"]}:
                        grupos[tipo][param]["puntos"].append({
                            "fecha_str": fecha_str,
                            "fecha_dt": fecha_dt,
                            "valor_num": valor_num,
                            "estado": r.get("estado", "sin_dato"),
                            "unidad": r.get("unidad") or ""
                        })

        # Calcular tendencias y filtrar parámetros con ≥2 mediciones
        grupos_resultado = {}
        for tipo, params in grupos.items():
            params_filtrados = {p: info for p, info in params.items() if len(info["puntos"]) >= 2}
            if not params_filtrados:
                continue

            grupos_resultado[tipo] = {}
            for param, info in params_filtrados.items():
                puntos = sorted(info["puntos"], key=lambda x: x["fecha_dt"])
                tendencia = self._calcular_tendencia(puntos)

                grupos_resultado[tipo][param] = {
                    "puntos": [{k: v for k, v in p.items() if k != "fecha_dt"} for p in puntos],
                    "tendencia": tendencia,
                    "unidad": info["unidad"],
                    "referencia": info["referencia"],
                    "fhir_category": info["fhir_category"]
                }

        narrativa = self._generar_narrativa(grupos_resultado, req.id_usuario, req.output_lang)

        return {
            "grupos": grupos_resultado,
            "narrativa": narrativa,
            "total_archivos": len(rows),
            "id_usuario": req.id_usuario
        }

    def _calcular_tendencia(self, puntos: list) -> dict:
        if len(puntos) < 2:
            return {"direccion": "estable", "variacion_pct": 0.0, "pendiente": 0.0}

        vals = [p["valor_num"] for p in puntos]
        v0, vf = vals[0], vals[-1]
        variacion_pct = ((vf - v0) / abs(v0) * 100) if v0 != 0 else 0.0

        if len(puntos) == 2:
            pendiente = vf - v0
        else:
            xs = [(p["fecha_dt"] - puntos[0]["fecha_dt"]).days for p in puntos]
            slope, _, _, _, _ = scipy_stats.linregress(xs, vals)
            pendiente = slope

        direccion = "sube" if pendiente > 0.01 else "baja" if pendiente < -0.01 else "estable"

        return {
            "direccion": direccion,
            "variacion_pct": round(variacion_pct, 1),
            "pendiente": round(float(pendiente), 4)
        }

    def _generar_narrativa(self, grupos: dict, id_usuario: int, lang: str = "es") -> str:
        # Aquí puedes mejorar usando Ollama para generar narrativa más natural
        return "Evolución clínica generada. Se detectaron tendencias en los parámetros principales."