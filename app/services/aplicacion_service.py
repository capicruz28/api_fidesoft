from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceError,
    ValidationError,
    DatabaseError,
)
from app.db.queries import execute_insert, execute_query, execute_update
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class AplicacionService(BaseService):
    """
    Servicio para administración de aplicaciones.

    Reglas:
    - Código único (`codigo`)
    - DELETE administrativo desactiva (`es_activo = 0`)
    """

    BOOL_FIELDS = {"es_activo"}

    @staticmethod
    def _convert_bool_fields(row: Dict[str, Any]) -> Dict[str, Any]:
        for f in AplicacionService.BOOL_FIELDS:
            if f in row and isinstance(row[f], int):
                row[f] = bool(row[f])
        return row

    @staticmethod
    @BaseService.handle_service_errors
    async def crear_aplicacion(app_data: Dict[str, Any]) -> Dict[str, Any]:
        nombre = (app_data.get("nombre") or "").strip()
        codigo = (app_data.get("codigo") or "").strip()

        if not nombre:
            raise ValidationError(detail="El nombre es requerido.", internal_code="APP_NOMBRE_REQUIRED")
        if not codigo:
            raise ValidationError(detail="El código es requerido.", internal_code="APP_CODIGO_REQUIRED")

        try:
            existe = execute_query("SELECT aplicacion_id FROM aplicacion WHERE codigo = ?", (codigo,))
            if existe:
                raise ConflictError(
                    detail=f"Ya existe una aplicación con código '{codigo}'.",
                    internal_code="APP_CODIGO_CONFLICT",
                )

            insert_query = """
            INSERT INTO aplicacion (nombre, codigo, descripcion, es_activo)
            OUTPUT INSERTED.aplicacion_id, INSERTED.nombre, INSERTED.codigo, INSERTED.descripcion,
                   INSERTED.es_activo, INSERTED.fecha_creacion
            VALUES (?, ?, ?, ?)
            """
            params = (
                nombre,
                codigo,
                app_data.get("descripcion"),
                bool(app_data.get("es_activo", True)),
            )
            result = execute_insert(insert_query, params)
            if not result:
                raise ServiceError(
                    status_code=500,
                    detail="No se pudo crear la aplicación en la base de datos.",
                    internal_code="APP_CREATION_FAILED",
                )
            return AplicacionService._convert_bool_fields(result)

        except (ValidationError, ConflictError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error BD al crear aplicación: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al crear la aplicación",
                internal_code="APP_CREATION_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al crear aplicación: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al crear la aplicación",
                internal_code="APP_CREATION_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def listar_aplicaciones(incluir_inactivas: bool = True) -> List[Dict[str, Any]]:
        try:
            query = """
            SELECT aplicacion_id, nombre, codigo, descripcion, es_activo, fecha_creacion
            FROM aplicacion
            """
            if not incluir_inactivas:
                query += " WHERE es_activo = 1"
            query += " ORDER BY nombre ASC"

            rows = execute_query(query)
            return [AplicacionService._convert_bool_fields(r) for r in rows]
        except DatabaseError as db_err:
            logger.error(f"Error BD al listar aplicaciones: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al listar aplicaciones",
                internal_code="APP_LIST_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al listar aplicaciones: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al listar aplicaciones",
                internal_code="APP_LIST_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_aplicacion_por_id(aplicacion_id: int) -> Optional[Dict[str, Any]]:
        try:
            query = """
            SELECT aplicacion_id, nombre, codigo, descripcion, es_activo, fecha_creacion
            FROM aplicacion
            WHERE aplicacion_id = ?
            """
            rows = execute_query(query, (aplicacion_id,))
            if not rows:
                return None
            return AplicacionService._convert_bool_fields(rows[0])
        except DatabaseError as db_err:
            logger.error(f"Error BD al obtener aplicación {aplicacion_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener la aplicación",
                internal_code="APP_RETRIEVAL_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al obtener aplicación {aplicacion_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener la aplicación",
                internal_code="APP_RETRIEVAL_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def actualizar_aplicacion(aplicacion_id: int, app_data: Dict[str, Any]) -> Dict[str, Any]:
        actual = await AplicacionService.obtener_aplicacion_por_id(aplicacion_id)
        if not actual:
            raise NotFoundError(
                detail=f"Aplicación con ID {aplicacion_id} no encontrada.",
                internal_code="APP_NOT_FOUND",
            )

        nuevo_codigo = app_data.get("codigo")
        if nuevo_codigo and str(nuevo_codigo).strip() != str(actual.get("codigo", "")).strip():
            existe = execute_query(
                "SELECT aplicacion_id FROM aplicacion WHERE codigo = ? AND aplicacion_id != ?",
                (str(nuevo_codigo).strip(), aplicacion_id),
            )
            if existe:
                raise ConflictError(
                    detail=f"Ya existe una aplicación con código '{str(nuevo_codigo).strip()}'.",
                    internal_code="APP_CODIGO_CONFLICT",
                )

        update_parts: List[str] = []
        params: List[Any] = []

        campos_permitidos = {
            "nombre": "nombre",
            "codigo": "codigo",
            "descripcion": "descripcion",
            "es_activo": "es_activo",
        }

        for field, db_field in campos_permitidos.items():
            if field in app_data and app_data[field] is not None:
                update_parts.append(f"{db_field} = ?")
                params.append(app_data[field])

        if not update_parts:
            raise ValidationError(
                detail="Se debe proporcionar al menos un campo para actualizar la aplicación.",
                internal_code="NO_UPDATE_DATA",
            )

        params.append(aplicacion_id)

        try:
            update_query = f"""
            UPDATE aplicacion
            SET {', '.join(update_parts)}
            OUTPUT INSERTED.aplicacion_id, INSERTED.nombre, INSERTED.codigo, INSERTED.descripcion,
                   INSERTED.es_activo, INSERTED.fecha_creacion
            WHERE aplicacion_id = ?
            """
            result = execute_update(update_query, tuple(params))
            if not result:
                raise ServiceError(
                    status_code=404,
                    detail="Aplicación no encontrada o no se pudo modificar.",
                    internal_code="APP_UPDATE_FAILED",
                )
            return AplicacionService._convert_bool_fields(result)

        except (ValidationError, ConflictError, NotFoundError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error BD al actualizar aplicación {aplicacion_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al actualizar la aplicación",
                internal_code="APP_UPDATE_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al actualizar aplicación {aplicacion_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al actualizar la aplicación",
                internal_code="APP_UPDATE_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def desactivar_aplicacion(aplicacion_id: int) -> Dict[str, Any]:
        actual = await AplicacionService.obtener_aplicacion_por_id(aplicacion_id)
        if not actual:
            raise NotFoundError(
                detail=f"Aplicación con ID {aplicacion_id} no encontrada.",
                internal_code="APP_NOT_FOUND",
            )

        try:
            query = """
            UPDATE aplicacion
            SET es_activo = 0
            OUTPUT INSERTED.aplicacion_id, INSERTED.nombre, INSERTED.codigo, INSERTED.descripcion,
                   INSERTED.es_activo, INSERTED.fecha_creacion
            WHERE aplicacion_id = ?
            """
            result = execute_update(query, (aplicacion_id,))
            if not result:
                raise ServiceError(
                    status_code=500,
                    detail="No se pudo desactivar la aplicación.",
                    internal_code="APP_DEACTIVATION_FAILED",
                )
            return AplicacionService._convert_bool_fields(result)

        except (NotFoundError, ValidationError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error BD al desactivar aplicación {aplicacion_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al desactivar la aplicación",
                internal_code="APP_DEACTIVATION_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al desactivar aplicación {aplicacion_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al desactivar la aplicación",
                internal_code="APP_DEACTIVATION_UNEXPECTED_ERROR",
            )

