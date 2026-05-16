# services/batch_service.py
import threading
import uuid
from datetime import datetime
from schemas.request import BatchRequest
from repositories.oracle_repo import OracleRepo
from services.analysis_service import AnalysisService
from fastapi import HTTPException

class BatchService:
    def __init__(self):
        self.analysis_service = AnalysisService()
        self.repo = OracleRepo()
        self._lock = threading.Lock()
        self._state = {
            "job_id": None,
            "running": False,
            "total": 0,
            "procesados": 0,
            "errores": 0,
            "omitidos": 0,
            "inicio": None,
            "fin": None,
            "log": [],
            "detalle": []
        }

    def _blog(self, msg: str, nivel: str = "info"):
        ts = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self._state["log"].append({"ts": ts, "nivel": nivel, "msg": msg})
            if len(self._state["log"]) > 300:
                self._state["log"] = self._state["log"][-300:]
        print(f"[BATCH {ts}] {msg}")

    def start_batch(self, req: BatchRequest):
        with self._lock:
            if self._state["running"]:
                raise HTTPException(status_code=409, detail="Ya hay un batch corriendo")

            job_id = str(uuid.uuid4())[:8]
            self._state.update({
                "job_id": job_id, "running": True,
                "total": 0, "procesados": 0, "errores": 0, "omitidos": 0,
                "inicio": datetime.now().isoformat(), "fin": None,
                "log": [], "detalle": []
            })

        threading.Thread(
            target=self._batch_worker,
            args=(job_id, req.fecha_ini, req.fecha_fin, req.output_lang, req.force_reprocess),
            daemon=True
        ).start()

        return {"ok": True, "job_id": job_id, "message": f"Batch iniciado {req.fecha_ini} → {req.fecha_fin}"}

    def _batch_worker(self, job_id, fecha_ini, fecha_fin, output_lang, force_reprocess):
        rows = self.repo.get_batch_files(fecha_ini, fecha_fin)
        if not rows:
            self._blog("No se encontraron archivos", "warn")
            self._finish_batch(job_id)
            return

        with self._lock:
            self._state["total"] = len(rows)

        for row in rows:
            with self._lock:
                if not self._state["running"] or self._state["job_id"] != job_id:
                    break

            identificacion, opcion1, opcion2, id_descripcion, _, id_archivo, id_usuario, ya_analizado, _ = row

            try:
                result = self.analysis_service.analizar_archivo(
                    url="",
                    id_usuario=id_usuario,
                    id_archivo=id_archivo,
                    identificacion=identificacion,
                    output_lang=output_lang,
                    force_reprocess=force_reprocess,
                    opcion1=opcion1 or "",
                    opcion2=opcion2 or "",
                    id_descripcion=id_descripcion or 0
                )
                status = "ok"
                self._blog(f"✓ [{id_archivo}] Procesado correctamente", "ok")
            except Exception as e:
                status = "error"
                self._blog(f"✗ [{id_archivo}] Error: {e}", "error")

            with self._lock:
                self._state["procesados"] += 1
                if status == "error":
                    self._state["errores"] += 1
                self._state["detalle"].append({
                    "id_archivo": int(id_archivo),
                    "nombre": opcion2 or opcion1 or str(id_archivo),
                    "status": status
                })

        self._finish_batch(job_id)

    def _finish_batch(self, job_id):
        with self._lock:
            if self._state["job_id"] == job_id:
                self._state["running"] = False
                self._state["fin"] = datetime.now().isoformat()

    def get_status(self):
        with self._lock:
            s = self._state.copy()
            total = s["total"] or 1
            s["pct"] = round((s["procesados"] / total) * 100, 1)
            return s

    def cancel(self):
        with self._lock:
            self._state["running"] = False
        return {"ok": True, "message": "Batch cancelado"}