from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

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


class ClienteService(BaseService):
    """
    Servicio para administración de clientes.

    Reglas:
    - Soft delete: `es_eliminado = 1` (nunca borrar físicamente)
    - Siempre filtrar `es_eliminado = 0` en consultas
    - `fecha_actualizacion` se actualiza automáticamente en cada PUT
    """

    BOOL_FIELDS = {"es_activo", "es_eliminado"}

    @staticmethod
    def _convert_bool_fields(row: Dict[str, Any]) -> Dict[str, Any]:
        for f in ClienteService.BOOL_FIELDS:
            if f in row and isinstance(row[f], int):
                row[f] = bool(row[f])
        return row

    @staticmethod
    @BaseService.handle_service_errors
    async def crear_cliente(cliente_data: Dict[str, Any]) -> Dict[str, Any]:
        razon_social = (cliente_data.get("razon_social") or "").strip()
        ruc = (cliente_data.get("ruc") or "").strip()

        if not razon_social:
            raise ValidationError(detail="La razón social es requerida.", internal_code="CLIENTE_RAZON_REQUIRED")
        if not ruc:
            raise ValidationError(detail="El RUC es requerido.", internal_code="CLIENTE_RUC_REQUIRED")

        try:
            existe = execute_query(
                "SELECT cliente_id, es_eliminado FROM cliente WHERE ruc = ?",
                (ruc,),
            )
            if existe:
                raise ConflictError(
                    detail=f"Ya existe un cliente con RUC '{ruc}'.",
                    internal_code="CLIENTE_RUC_CONFLICT",
                )

            insert_query = """
            INSERT INTO cliente (
                razon_social, ruc, representante, direccion, telefono, correo, logo_url, es_activo, es_eliminado
            )
            OUTPUT
                INSERTED.cliente_id, INSERTED.razon_social, INSERTED.ruc, INSERTED.representante,
                INSERTED.direccion, INSERTED.telefono, INSERTED.correo, INSERTED.logo_url,
                INSERTED.es_activo, INSERTED.fecha_creacion, INSERTED.fecha_actualizacion, INSERTED.es_eliminado
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """

            params = (
                razon_social,
                ruc,
                cliente_data.get("representante"),
                cliente_data.get("direccion"),
                cliente_data.get("telefono"),
                cliente_data.get("correo"),
                cliente_data.get("logo_url"),
                bool(cliente_data.get("es_activo", True)),
            )

            result = execute_insert(insert_query, params)
            if not result:
                raise ServiceError(
                    status_code=500,
                    detail="No se pudo crear el cliente en la base de datos.",
                    internal_code="CLIENTE_CREATION_FAILED",
                )

            return ClienteService._convert_bool_fields(result)

        except (ValidationError, ConflictError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error BD al crear cliente: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al crear el cliente",
                internal_code="CLIENTE_CREATION_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al crear cliente: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al crear el cliente",
                internal_code="CLIENTE_CREATION_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_cliente_por_id(cliente_id: int) -> Optional[Dict[str, Any]]:
        try:
            query = """
            SELECT
                cliente_id, razon_social, ruc, representante, direccion, telefono, correo,
                logo_url, es_activo, fecha_creacion, fecha_actualizacion, es_eliminado
            FROM cliente
            WHERE cliente_id = ? AND es_eliminado = 0
            """
            rows = execute_query(query, (cliente_id,))
            if not rows:
                return None
            return ClienteService._convert_bool_fields(rows[0])
        except DatabaseError as db_err:
            logger.error(f"Error BD al obtener cliente {cliente_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener el cliente",
                internal_code="CLIENTE_RETRIEVAL_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al obtener cliente {cliente_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener el cliente",
                internal_code="CLIENTE_RETRIEVAL_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_cliente_detalle(cliente_id: int) -> Optional[Dict[str, Any]]:
        cliente = await ClienteService.obtener_cliente_por_id(cliente_id)
        if not cliente:
            return None

        try:
            conexiones_query = """
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
            conexiones = execute_query(conexiones_query, (cliente_id,))
            for c in conexiones:
                if "es_activo" in c and isinstance(c["es_activo"], int):
                    c["es_activo"] = bool(c["es_activo"])
                if "es_principal" in c and isinstance(c["es_principal"], int):
                    c["es_principal"] = bool(c["es_principal"])

            cliente["conexiones"] = conexiones
            return cliente

        except DatabaseError as db_err:
            logger.error(f"Error BD al obtener conexiones de cliente {cliente_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener el detalle del cliente",
                internal_code="CLIENTE_DETAIL_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al obtener detalle de cliente {cliente_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener el detalle del cliente",
                internal_code="CLIENTE_DETAIL_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def buscar_por_ruc(ruc: str) -> Optional[Dict[str, Any]]:
        ruc = (ruc or "").strip()
        if not ruc:
            raise ValidationError(detail="El RUC es requerido.", internal_code="CLIENTE_RUC_REQUIRED")

        try:
            query = """
            SELECT
                cliente_id, razon_social, ruc, representante, direccion, telefono, correo,
                logo_url, es_activo, fecha_creacion, fecha_actualizacion, es_eliminado
            FROM cliente
            WHERE ruc = ? AND es_eliminado = 0
            """
            rows = execute_query(query, (ruc,))
            if not rows:
                return None
            return ClienteService._convert_bool_fields(rows[0])
        except DatabaseError as db_err:
            logger.error(f"Error BD al buscar cliente por ruc {ruc}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al buscar cliente por RUC",
                internal_code="CLIENTE_RUC_SEARCH_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al buscar cliente por ruc {ruc}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al buscar cliente por RUC",
                internal_code="CLIENTE_RUC_SEARCH_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def listar_clientes(
        page: int = 1,
        limit: int = 10,
        ruc: Optional[str] = None,
        razon_social: Optional[str] = None,
        es_activo: Optional[bool] = None,
    ) -> Dict[str, Any]:
        if page < 1:
            raise ValidationError(detail="El número de página debe ser mayor o igual a 1.", internal_code="INVALID_PAGE_NUMBER")
        if limit < 1:
            raise ValidationError(detail="El límite por página debe ser mayor o igual a 1.", internal_code="INVALID_LIMIT")

        ruc_param = f"%{ruc.strip()}%" if ruc else None
        rs_param = f"%{razon_social.strip()}%" if razon_social else None

        offset = (page - 1) * limit
        start_row = offset + 1
        end_row = offset + limit

        try:
            count_query = """
            SELECT COUNT(*) AS total
            FROM cliente
            WHERE es_eliminado = 0
              AND (? IS NULL OR ruc LIKE ?)
              AND (? IS NULL OR razon_social LIKE ?)
              AND (? IS NULL OR es_activo = ?)
            """
            count_params: Tuple[Any, ...] = (
                ruc_param, ruc_param,
                rs_param, rs_param,
                es_activo, es_activo,
            )
            count_result = execute_query(count_query, count_params)
            total = count_result[0]["total"] if count_result else 0

            items: List[Dict[str, Any]] = []
            if total > 0:
                select_query = """
                WITH ClientesPaginados AS (
                    SELECT
                        cliente_id,
                        ROW_NUMBER() OVER (ORDER BY cliente_id DESC) AS rn
                    FROM cliente
                    WHERE es_eliminado = 0
                      AND (? IS NULL OR ruc LIKE ?)
                      AND (? IS NULL OR razon_social LIKE ?)
                      AND (? IS NULL OR es_activo = ?)
                )
                SELECT
                    c.cliente_id, c.razon_social, c.ruc, c.representante, c.direccion, c.telefono,
                    c.correo, c.logo_url, c.es_activo, c.fecha_creacion, c.fecha_actualizacion, c.es_eliminado
                FROM ClientesPaginados cp
                INNER JOIN cliente c ON c.cliente_id = cp.cliente_id
                WHERE cp.rn BETWEEN ? AND ?
                ORDER BY cp.rn ASC
                """
                select_params: Tuple[Any, ...] = (
                    ruc_param, ruc_param,
                    rs_param, rs_param,
                    es_activo, es_activo,
                    start_row, end_row,
                )
                items = execute_query(select_query, select_params)
                items = [ClienteService._convert_bool_fields(i) for i in items]

            total_paginas = math.ceil(total / limit) if limit > 0 else 0
            return {
                "clientes": items,
                "total_clientes": total,
                "pagina_actual": page,
                "total_paginas": total_paginas,
            }

        except (ValidationError, ServiceError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error BD al listar clientes: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al listar clientes",
                internal_code="CLIENTE_LIST_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al listar clientes: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al listar clientes",
                internal_code="CLIENTE_LIST_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def actualizar_cliente(cliente_id: int, cliente_data: Dict[str, Any]) -> Dict[str, Any]:
        cliente_actual = await ClienteService.obtener_cliente_por_id(cliente_id)
        if not cliente_actual:
            raise NotFoundError(
                detail=f"Cliente con ID {cliente_id} no encontrado.",
                internal_code="CLIENTE_NOT_FOUND",
            )

        nuevo_ruc = cliente_data.get("ruc")
        if nuevo_ruc and str(nuevo_ruc).strip() != str(cliente_actual.get("ruc", "")).strip():
            existe = execute_query(
                "SELECT cliente_id FROM cliente WHERE ruc = ? AND cliente_id != ?",
                (str(nuevo_ruc).strip(), cliente_id),
            )
            if existe:
                raise ConflictError(
                    detail=f"Ya existe un cliente con RUC '{str(nuevo_ruc).strip()}'.",
                    internal_code="CLIENTE_RUC_CONFLICT",
                )

        update_parts: List[str] = []
        params: List[Any] = []

        campos_permitidos = {
            "razon_social": "razon_social",
            "ruc": "ruc",
            "representante": "representante",
            "direccion": "direccion",
            "telefono": "telefono",
            "correo": "correo",
            "logo_url": "logo_url",
            "es_activo": "es_activo",
        }

        for field, db_field in campos_permitidos.items():
            if field in cliente_data and cliente_data[field] is not None:
                update_parts.append(f"{db_field} = ?")
                params.append(cliente_data[field])

        if not update_parts:
            raise ValidationError(
                detail="Se debe proporcionar al menos un campo para actualizar el cliente.",
                internal_code="NO_UPDATE_DATA",
            )

        update_parts.append("fecha_actualizacion = GETDATE()")
        params.append(cliente_id)

        try:
            update_query = f"""
            UPDATE cliente
            SET {', '.join(update_parts)}
            OUTPUT
                INSERTED.cliente_id, INSERTED.razon_social, INSERTED.ruc, INSERTED.representante,
                INSERTED.direccion, INSERTED.telefono, INSERTED.correo, INSERTED.logo_url,
                INSERTED.es_activo, INSERTED.fecha_creacion, INSERTED.fecha_actualizacion, INSERTED.es_eliminado
            WHERE cliente_id = ? AND es_eliminado = 0
            """
            result = execute_update(update_query, tuple(params))
            if not result:
                raise ServiceError(
                    status_code=404,
                    detail="Cliente no encontrado o no se pudo modificar.",
                    internal_code="CLIENTE_UPDATE_FAILED",
                )
            return ClienteService._convert_bool_fields(result)
        except (ValidationError, ConflictError, NotFoundError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error BD al actualizar cliente {cliente_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al actualizar el cliente",
                internal_code="CLIENTE_UPDATE_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al actualizar cliente {cliente_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al actualizar el cliente",
                internal_code="CLIENTE_UPDATE_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def eliminar_cliente_soft(cliente_id: int) -> Dict[str, Any]:
        try:
            estado = execute_query(
                "SELECT es_eliminado FROM cliente WHERE cliente_id = ?",
                (cliente_id,),
            )
            if not estado:
                raise NotFoundError(
                    detail=f"Cliente con ID {cliente_id} no encontrado.",
                    internal_code="CLIENTE_NOT_FOUND",
                )
            if estado[0].get("es_eliminado") in (1, True):
                cliente = await ClienteService.obtener_cliente_por_id(cliente_id)
                if cliente:
                    return cliente
                raise NotFoundError(
                    detail=f"Cliente con ID {cliente_id} no encontrado.",
                    internal_code="CLIENTE_NOT_FOUND",
                )

            delete_query = """
            UPDATE cliente
            SET es_eliminado = 1, es_activo = 0, fecha_actualizacion = GETDATE()
            OUTPUT
                INSERTED.cliente_id, INSERTED.razon_social, INSERTED.ruc, INSERTED.representante,
                INSERTED.direccion, INSERTED.telefono, INSERTED.correo, INSERTED.logo_url,
                INSERTED.es_activo, INSERTED.fecha_creacion, INSERTED.fecha_actualizacion, INSERTED.es_eliminado
            WHERE cliente_id = ? AND es_eliminado = 0
            """
            result = execute_update(delete_query, (cliente_id,))
            if not result:
                raise ServiceError(
                    status_code=409,
                    detail="Conflicto al eliminar el cliente, posible concurrencia.",
                    internal_code="CLIENTE_DELETE_CONFLICT",
                )
            return ClienteService._convert_bool_fields(result)

        except (NotFoundError, ValidationError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error BD al eliminar cliente {cliente_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al eliminar el cliente",
                internal_code="CLIENTE_DELETE_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado al eliminar cliente {cliente_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al eliminar el cliente",
                internal_code="CLIENTE_DELETE_UNEXPECTED_ERROR",
            )

