from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ServiceError,
    ValidationError,
    DatabaseError,
)
from app.db.queries import execute_insert, execute_query, execute_transaction, execute_update
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class ClienteConexionService(BaseService):
    """
    Servicio para administración de conexiones por cliente.

    Reglas:
    - DELETE administrativo desactiva (`es_activo = 0`)
    - Soporta `es_principal`: si se marca, se desmarca el resto dentro del mismo cliente/aplicación
    """

    @staticmethod
    def _convert_bool_fields(row: Dict[str, Any]) -> Dict[str, Any]:
        for f in ("es_activo", "es_principal"):
            if f in row and isinstance(row[f], int):
                row[f] = bool(row[f])
        return row

    @staticmethod
    @BaseService.handle_service_errors
    async def listar_conexiones_por_cliente(cliente_id: int) -> List[Dict[str, Any]]:
        try:
            query = """
            SELECT
                cc.conexion_id, cc.cliente_id, cc.aplicacion_id,
                a.codigo AS aplicacion_codigo,
                cc.nombre, cc.entorno, cc.base_url, cc.descripcion,
                cc.es_principal, cc.es_activo, cc.fecha_creacion, cc.fecha_actualizacion
            FROM cliente_conexion cc
            INNER JOIN aplicacion a ON a.aplicacion_id = cc.aplicacion_id
            WHERE cc.cliente_id = ?
            ORDER BY cc.conexion_id ASC
            """
            rows = execute_query(query, (cliente_id,))
            return [ClienteConexionService._convert_bool_fields(r) for r in rows]
        except DatabaseError as db_err:
            logger.error(f"Error BD al listar conexiones del cliente {cliente_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al listar conexiones del cliente",
                internal_code="CONEXION_LIST_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al listar conexiones del cliente {cliente_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al listar conexiones del cliente",
                internal_code="CONEXION_LIST_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_conexion_por_id(cliente_id: int, conexion_id: int) -> Optional[Dict[str, Any]]:
        try:
            query = """
            SELECT
                cc.conexion_id, cc.cliente_id, cc.aplicacion_id,
                a.codigo AS aplicacion_codigo,
                cc.nombre, cc.entorno, cc.base_url, cc.descripcion,
                cc.es_principal, cc.es_activo, cc.fecha_creacion, cc.fecha_actualizacion
            FROM cliente_conexion cc
            INNER JOIN aplicacion a ON a.aplicacion_id = cc.aplicacion_id
            WHERE cc.cliente_id = ? AND cc.conexion_id = ?
            """
            rows = execute_query(query, (cliente_id, conexion_id))
            if not rows:
                return None
            return ClienteConexionService._convert_bool_fields(rows[0])
        except DatabaseError as db_err:
            logger.error(f"Error BD al obtener conexión {conexion_id} del cliente {cliente_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener la conexión",
                internal_code="CONEXION_RETRIEVAL_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al obtener conexión {conexion_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener la conexión",
                internal_code="CONEXION_RETRIEVAL_UNEXPECTED_ERROR",
            )

    @staticmethod
    def _verificar_cliente_activo_no_eliminado(cliente_id: int) -> None:
        row = execute_query(
            "SELECT cliente_id, es_activo, es_eliminado FROM cliente WHERE cliente_id = ?",
            (cliente_id,),
        )
        if not row:
            raise NotFoundError(
                detail=f"Cliente con ID {cliente_id} no encontrado.",
                internal_code="CLIENTE_NOT_FOUND",
            )
        es_eliminado = row[0].get("es_eliminado") in (1, True)
        if es_eliminado:
            raise NotFoundError(
                detail=f"Cliente con ID {cliente_id} no encontrado.",
                internal_code="CLIENTE_NOT_FOUND",
            )

    @staticmethod
    def _verificar_aplicacion_existente(aplicacion_id: int) -> None:
        row = execute_query(
            "SELECT aplicacion_id FROM aplicacion WHERE aplicacion_id = ?",
            (aplicacion_id,),
        )
        if not row:
            raise NotFoundError(
                detail=f"Aplicación con ID {aplicacion_id} no encontrada.",
                internal_code="APP_NOT_FOUND",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def crear_conexion(cliente_id: int, conexion_data: Dict[str, Any]) -> Dict[str, Any]:
        ClienteConexionService._verificar_cliente_activo_no_eliminado(cliente_id)

        aplicacion_id = conexion_data.get("aplicacion_id")
        if not aplicacion_id:
            raise ValidationError(detail="aplicacion_id es requerido.", internal_code="CONEXION_APP_REQUIRED")

        ClienteConexionService._verificar_aplicacion_existente(int(aplicacion_id))

        nombre = (conexion_data.get("nombre") or "").strip()
        base_url = (conexion_data.get("base_url") or "").strip()
        entorno = (conexion_data.get("entorno") or "produccion").strip()

        if not nombre:
            raise ValidationError(detail="El nombre de la conexión es requerido.", internal_code="CONEXION_NOMBRE_REQUIRED")
        if not base_url:
            raise ValidationError(detail="La base_url es requerida.", internal_code="CONEXION_URL_REQUIRED")

        es_principal = bool(conexion_data.get("es_principal", False))

        def _ops(cursor):
            if es_principal:
                cursor.execute(
                    """
                    UPDATE cliente_conexion
                    SET es_principal = 0, fecha_actualizacion = GETDATE()
                    WHERE cliente_id = ? AND aplicacion_id = ?
                    """,
                    (cliente_id, int(aplicacion_id)),
                )

            cursor.execute(
                """
                INSERT INTO cliente_conexion (
                    cliente_id, aplicacion_id, nombre, entorno, base_url, descripcion,
                    es_principal, es_activo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cliente_id,
                    int(aplicacion_id),
                    nombre,
                    entorno,
                    base_url,
                    conexion_data.get("descripcion"),
                    1 if es_principal else 0,
                    1 if bool(conexion_data.get("es_activo", True)) else 0,
                ),
            )

        try:
            execute_transaction(_ops)

            row = execute_query(
                """
                SELECT TOP 1
                    cc.conexion_id, cc.cliente_id, cc.aplicacion_id,
                    a.codigo AS aplicacion_codigo,
                    cc.nombre, cc.entorno, cc.base_url, cc.descripcion,
                    cc.es_principal, cc.es_activo, cc.fecha_creacion, cc.fecha_actualizacion
                FROM cliente_conexion cc
                INNER JOIN aplicacion a ON a.aplicacion_id = cc.aplicacion_id
                WHERE cc.cliente_id = ? AND cc.aplicacion_id = ?
                ORDER BY cc.conexion_id DESC
                """,
                (cliente_id, int(aplicacion_id)),
            )
            if not row:
                raise ServiceError(
                    status_code=500,
                    detail="No se pudo obtener la conexión creada.",
                    internal_code="CONEXION_CREATION_READBACK_FAILED",
                )
            return ClienteConexionService._convert_bool_fields(row[0])

        except (ValidationError, ConflictError, NotFoundError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error BD al crear conexión: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al crear la conexión",
                internal_code="CONEXION_CREATION_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al crear conexión: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al crear la conexión",
                internal_code="CONEXION_CREATION_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def actualizar_conexion(cliente_id: int, conexion_id: int, conexion_data: Dict[str, Any]) -> Dict[str, Any]:
        actual = await ClienteConexionService.obtener_conexion_por_id(cliente_id, conexion_id)
        if not actual:
            raise NotFoundError(
                detail=f"Conexión con ID {conexion_id} no encontrada para el cliente {cliente_id}.",
                internal_code="CONEXION_NOT_FOUND",
            )

        aplicacion_id = int(conexion_data.get("aplicacion_id") or actual["aplicacion_id"])
        if "aplicacion_id" in conexion_data and conexion_data["aplicacion_id"] is not None:
            ClienteConexionService._verificar_aplicacion_existente(aplicacion_id)

        update_parts: List[str] = []
        params: List[Any] = []

        campos_permitidos = {
            "aplicacion_id": "aplicacion_id",
            "nombre": "nombre",
            "entorno": "entorno",
            "base_url": "base_url",
            "descripcion": "descripcion",
            "es_principal": "es_principal",
            "es_activo": "es_activo",
        }

        for field, db_field in campos_permitidos.items():
            if field in conexion_data and conexion_data[field] is not None:
                update_parts.append(f"{db_field} = ?")
                params.append(conexion_data[field])

        if not update_parts:
            raise ValidationError(
                detail="Se debe proporcionar al menos un campo para actualizar la conexión.",
                internal_code="NO_UPDATE_DATA",
            )

        es_principal = bool(conexion_data.get("es_principal")) if "es_principal" in conexion_data else False

        def _ops(cursor):
            if es_principal:
                cursor.execute(
                    """
                    UPDATE cliente_conexion
                    SET es_principal = 0, fecha_actualizacion = GETDATE()
                    WHERE cliente_id = ? AND aplicacion_id = ? AND conexion_id != ?
                    """,
                    (cliente_id, aplicacion_id, conexion_id),
                )

            cursor.execute(
                f"""
                UPDATE cliente_conexion
                SET {', '.join(update_parts)}, fecha_actualizacion = GETDATE()
                WHERE cliente_id = ? AND conexion_id = ?
                """,
                tuple(params + [cliente_id, conexion_id]),
            )

        try:
            execute_transaction(_ops)
            updated = await ClienteConexionService.obtener_conexion_por_id(cliente_id, conexion_id)
            if not updated:
                raise ServiceError(
                    status_code=500,
                    detail="No se pudo obtener la conexión actualizada.",
                    internal_code="CONEXION_UPDATE_READBACK_FAILED",
                )
            return updated

        except (ValidationError, ConflictError, NotFoundError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error BD al actualizar conexión {conexion_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al actualizar la conexión",
                internal_code="CONEXION_UPDATE_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al actualizar conexión {conexion_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al actualizar la conexión",
                internal_code="CONEXION_UPDATE_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def desactivar_conexion(cliente_id: int, conexion_id: int) -> Dict[str, Any]:
        actual = await ClienteConexionService.obtener_conexion_por_id(cliente_id, conexion_id)
        if not actual:
            raise NotFoundError(
                detail=f"Conexión con ID {conexion_id} no encontrada para el cliente {cliente_id}.",
                internal_code="CONEXION_NOT_FOUND",
            )

        try:
            query = """
            UPDATE cliente_conexion
            SET es_activo = 0, fecha_actualizacion = GETDATE()
            WHERE cliente_id = ? AND conexion_id = ?
            """
            execute_update(query, (cliente_id, conexion_id))

            updated = await ClienteConexionService.obtener_conexion_por_id(cliente_id, conexion_id)
            if not updated:
                raise ServiceError(
                    status_code=500,
                    detail="No se pudo obtener la conexión desactivada.",
                    internal_code="CONEXION_DEACTIVATION_READBACK_FAILED",
                )
            return updated

        except (NotFoundError, ValidationError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error BD al desactivar conexión {conexion_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al desactivar la conexión",
                internal_code="CONEXION_DEACTIVATION_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al desactivar conexión {conexion_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al desactivar la conexión",
                internal_code="CONEXION_DEACTIVATION_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def get_conexiones_por_ruc(ruc: str, codigo_app: str) -> Dict[str, Any]:
        ruc = (ruc or "").strip()
        codigo_app = (codigo_app or "").strip()

        if not ruc:
            raise ValidationError(detail="El RUC es requerido.", internal_code="CLIENTE_RUC_REQUIRED")
        if not codigo_app:
            raise ValidationError(detail="El código de aplicación es requerido.", internal_code="APP_CODIGO_REQUIRED")

        try:
            cliente_rows = execute_query(
                """
                SELECT cliente_id, ruc, razon_social, es_activo, es_eliminado
                FROM cliente
                WHERE ruc = ?
                """,
                (ruc,),
            )
            if not cliente_rows:
                raise NotFoundError(
                    detail=f"No se encontró cliente con RUC '{ruc}'.",
                    internal_code="CLIENTE_NOT_FOUND",
                )

            cliente_row = cliente_rows[0]
            es_eliminado = cliente_row.get("es_eliminado") in (1, True)
            if es_eliminado:
                raise NotFoundError(
                    detail=f"No se encontró cliente con RUC '{ruc}'.",
                    internal_code="CLIENTE_NOT_FOUND",
                )

            es_activo = bool(cliente_row.get("es_activo")) if not isinstance(cliente_row.get("es_activo"), int) else bool(cliente_row.get("es_activo"))
            if not es_activo:
                raise AuthorizationError(
                    detail="Cliente inactivo",
                    internal_code="CLIENTE_INACTIVO",
                )

            conexiones = execute_query(
                """
                SELECT
                    cc.nombre, cc.entorno, cc.base_url, cc.es_principal,
                    a.codigo AS aplicacion_codigo
                FROM cliente_conexion cc
                INNER JOIN aplicacion a ON a.aplicacion_id = cc.aplicacion_id
                WHERE cc.cliente_id = ?
                  AND cc.es_activo = 1
                  AND a.codigo = ?
                  AND a.es_activo = 1
                ORDER BY cc.es_principal DESC, cc.conexion_id ASC
                """,
                (int(cliente_row["cliente_id"]), codigo_app),
            )
            for c in conexiones:
                if "es_principal" in c and isinstance(c["es_principal"], int):
                    c["es_principal"] = bool(c["es_principal"])

            return {
                "cliente": {
                    "ruc": cliente_row.get("ruc"),
                    "razon_social": cliente_row.get("razon_social"),
                },
                "conexiones": conexiones,
            }

        except (ValidationError, NotFoundError, AuthorizationError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error BD en get_conexiones_por_ruc: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al buscar conexiones",
                internal_code="CONEXION_PUBLICA_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado en get_conexiones_por_ruc: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al buscar conexiones",
                internal_code="CONEXION_PUBLICA_UNEXPECTED_ERROR",
            )

