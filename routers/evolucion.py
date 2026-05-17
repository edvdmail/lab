# routers/evolucion.py
from fastapi import APIRouter
from schemas.request import EvolucionRequest
from services.evolucion_service import EvolucionService

router = APIRouter(tags=["evolucion"])

evolucion_service = EvolucionService()

# NOTA: main.py registra este router SIN prefix, así que el path
# debe ser "/evolucion" para que el frontend lo encuentre en POST /evolucion
@router.post("/evolucion")
async def get_evolucion(req: EvolucionRequest):
    """Obtiene la evolución clínica longitudinal del paciente"""
    try:
        return await evolucion_service.get_evolucion(req)
    except Exception as e:
        return {
            "error": str(e),
            "grupos": {},
            "narrativa": "Error al cargar evolución clínica",
            "total_archivos": 0,
            "id_usuario": req.id_usuario
        }