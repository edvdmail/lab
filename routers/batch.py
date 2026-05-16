# routers/batch.py
from fastapi import APIRouter
from schemas.request import BatchRequest
from services.batch_service import BatchService

router = APIRouter()   # ← Sin prefix aquí tampoco

batch_service = BatchService()

@router.post("/batch")
async def start_batch(req: BatchRequest):
    return await batch_service.start_batch(req)

@router.get("/batch/status")
def batch_status():
    return batch_service.get_status()

@router.post("/batch/cancel")
def cancel_batch():
    return batch_service.cancel()

@router.get("/batch/preview")
def batch_preview(fecha_ini: str, fecha_fin: str):
    return batch_service.preview(fecha_ini, fecha_fin)