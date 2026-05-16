# routers/analyze.py
from fastapi import APIRouter
from schemas.request import AnalyzeRequest
from services.analysis_service import AnalysisService

router = APIRouter()

analysis_service = AnalysisService()

@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    result = await analysis_service.analizar_archivo(
        url=req.url,
        id_usuario=req.id_usuario,
        id_archivo=req.id_archivo,
        identificacion=req.identificacion,
        output_lang=req.output_lang or "es",
        force_reprocess=req.force_reprocess or False
    )
    return result