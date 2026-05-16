# schemas/request.py
from pydantic import BaseModel
from typing import Optional


class BatchRequest(BaseModel):
    """Petición para procesamiento en batch"""
    fecha_ini: str                    # Formato YYYYMMDD
    fecha_fin: str                    # Formato YYYYMMDD
    output_lang: Optional[str] = 'es'
    force_reprocess: Optional[bool] = False


class AnalyzeRequest(BaseModel):
    """Análisis de un archivo individual"""
    url: str
    id_usuario: int
    identificacion: str               # Usado como contraseña del PDF
    id_archivo: Optional[int] = None
    output_lang: Optional[str] = 'es'
    force_reprocess: Optional[bool] = False


class EvolucionRequest(BaseModel):
    """Solicitud de evolución clínica"""
    id_usuario: int
    output_lang: Optional[str] = 'es'


class SaveAnalysisRequest(BaseModel):
    """Guardar análisis manualmente"""
    id_archivo: int
    nombre_alternativo: str
    analisis: str