# routers/batch.py
from fastapi import APIRouter
from schemas.request import BatchRequest
from services.batch_service import BatchService

router = APIRouter()

batch_service = BatchService()

# NOTA: main.py ya registra este router con prefix="/batch"
# Por eso los paths aquí van sin /batch al inicio:
#   POST   /batch          ← antes era /batch/batch (duplicado)
#   GET    /batch/status   ← antes era /batch/batch/status
#   POST   /batch/cancel   ← antes era /batch/batch/cancel
#   GET    /batch/preview  ← antes era /batch/batch/preview

@router.post("")
async def start_batch(req: BatchRequest):
    return batch_service.start_batch(req)

@router.get("/status")
def batch_status():
    return batch_service.get_status()

@router.post("/cancel")
def cancel_batch():
    return batch_service.cancel()

@router.get("/preview")
def batch_preview(fecha_ini: str, fecha_fin: str):
    return batch_service.preview(fecha_ini, fecha_fin)