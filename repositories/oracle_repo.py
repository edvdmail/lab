# repositories/oracle_repo.py
from conexion import OracleEnterpriseConnection
import json
from typing import Optional, List, Dict

class OracleRepo:
    def __init__(self):
        self.db = OracleEnterpriseConnection()

    def connect(self) -> bool:
        return self.db.connect()

    def close(self):
        self.db.close_connection()

    # ====================== BATCH ======================
    def get_batch_files(self, fecha_ini: str, fecha_fin: str):
        """Obtiene archivos para procesar en batch"""
        sql = """
            SELECT
                us.identificacion,
                ar.nombre_archivo_almacenado  AS opcion1,
                ar.nombre_archivo             AS opcion2,
                ar.id_descripcion,
                ar.fecha_cargue,
                ar.id                         AS id_archivo,
                ar.id_usuario,
                CASE WHEN ar.analisis IS NOT NULL THEN 1 ELSE 0 END AS ya_analizado,
                ar.analisis
            FROM tkr_archivos ar
            JOIN tkr_usuarios us ON us.id = ar.id_usuario
            WHERE us.id_rol = 3
              AND ar.id_descripcion NOT IN (-19, -25, -24, 3)
      AND us.identificacion = '27576540'
              AND TRUNC(ar.fecha_cargue) BETWEEN TO_DATE(:P_FECINI, 'YYYYMMDD')
                                             AND TO_DATE(:P_FECFIN,  'YYYYMMDD')
            ORDER BY ar.id DESC
        """
        if self.connect():
            try:
                return self.db.execute_query(sql, {"P_FECINI": fecha_ini, "P_FECFIN": fecha_fin})
            finally:
                self.close()
        return None

    def get_batch_count(self, fecha_ini: str, fecha_fin: str):
        sql = """
            SELECT COUNT(*),
                   SUM(CASE WHEN ar.analisis IS NOT NULL THEN 1 ELSE 0 END) AS ya_analizados
            FROM tkr_archivos ar
            JOIN tkr_usuarios us ON us.id = ar.id_usuario
            WHERE us.id_rol = 3
              AND ar.id_descripcion NOT IN (-19, -25, -24, 3)
      AND us.identificacion = '27576540'
              AND TRUNC(ar.fecha_cargue) BETWEEN TO_DATE(:P_FECINI, 'YYYYMMDD')
                                             AND TO_DATE(:P_FECFIN,  'YYYYMMDD')
        """
        if self.connect():
            try:
                return self.db.execute_query(sql, {"P_FECINI": fecha_ini, "P_FECFIN": fecha_fin})
            finally:
                self.close()
        return None

    def check_ya_analizado(self, id_archivo: int):
        sql = "SELECT analisis FROM tkr_archivos WHERE id = :id_archivo AND analisis IS NOT NULL"
        if self.connect():
            try:
                return self.db.execute_query(sql, {"id_archivo": id_archivo})
            finally:
                self.close()
        return None

    def save_analysis(self, id_archivo: int, nombre_alternativo: str, analisis_json: str):
        sql = """
            UPDATE tkr_archivos
            SET nombre_alternativo = :nombre_alternativo,
                analisis           = :analisis
            WHERE id = :id_archivo
        """
        if self.connect():
            try:
                self.db.execute_query(sql, {
                    "nombre_alternativo": nombre_alternativo,
                    "analisis": analisis_json,
                    "id_archivo": id_archivo
                })
                return True
            finally:
                self.close()
        return False

    # ====================== EVOLUCIÓN ======================
    def get_analisis_usuario(self, id_usuario: int):
        sql = """
            SELECT analisis, nombre_alternativo, id, fecha_cargue
            FROM tkr_archivos
            WHERE id_usuario = :id_usuario
              AND analisis IS NOT NULL
            ORDER BY fecha_cargue ASC
        """
        if self.connect():
            try:
                return self.db.execute_query(sql, {"id_usuario": id_usuario})
            finally:
                self.close()
        return None