"""
Módulo de endpoints para la administración de clientes.

Incluye:
- CRUD completo de clientes (con soft delete)
- Listado con paginación y filtros
- Detalle con conexiones incluidas
"""

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from typing import Optional

from app.api.deps import RoleChecker
from app.core.exceptions import CustomException
from app.core.logging_config import get_logger
from app.schemas.cliente import ClienteCreate, ClienteListResponse, ClienteResponse, ClienteUpdate
from app.services.cliente_service import ClienteService

logger = get_logger(__name__)
router = APIRouter()

require_admin = RoleChecker(["Administrador"])


@router.get(
    "/",
    response_model=ClienteListResponse,
    summary="Listar clientes (paginado)",
    description="Lista clientes con paginación y filtros (ruc, razon_social, es_activo).",
    dependencies=[Depends(require_admin)],
)
async def listar_clientes(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=100, description="Elementos por página"),
    ruc: Optional[str] = Query(None, description="Filtro por RUC (LIKE)"),
    razon_social: Optional[str] = Query(None, description="Filtro por razón social (LIKE)"),
    es_activo: Optional[bool] = Query(None, description="Filtro por estado activo"),
):
    try:
        return await ClienteService.listar_clientes(
            page=page,
            limit=limit,
            ruc=ruc,
            razon_social=razon_social,
            es_activo=es_activo,
        )
    except CustomException as ce:
        logger.warning(f"Error de negocio al listar clientes: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception("Error inesperado en GET /clientes/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al listar clientes.",
        )


@router.get(
    "/{cliente_id}/",
    response_model=ClienteResponse,
    summary="Detalle de cliente (con conexiones)",
    dependencies=[Depends(require_admin)],
)
async def obtener_cliente(cliente_id: int):
    try:
        cliente = await ClienteService.obtener_cliente_detalle(cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente con ID {cliente_id} no encontrado.",
            )
        return cliente
    except HTTPException:
        raise
    except CustomException as ce:
        logger.warning(f"Error de negocio al obtener cliente {cliente_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception(f"Error inesperado en GET /clientes/{cliente_id}/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener el cliente.",
        )


@router.post(
    "/",
    response_model=ClienteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear cliente",
    dependencies=[Depends(require_admin)],
)
async def crear_cliente(cliente_in: ClienteCreate = Body(...)):
    try:
        created = await ClienteService.crear_cliente(cliente_in.model_dump())
        created["conexiones"] = []
        return created
    except CustomException as ce:
        logger.warning(f"Error de negocio al crear cliente: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception("Error inesperado en POST /clientes/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al crear el cliente.",
        )


@router.put(
    "/{cliente_id}/",
    response_model=ClienteResponse,
    summary="Actualizar cliente",
    dependencies=[Depends(require_admin)],
)
async def actualizar_cliente(cliente_id: int, cliente_in: ClienteUpdate = Body(...)):
    update_data = cliente_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se debe proporcionar al menos un campo para actualizar el cliente.",
        )

    try:
        updated = await ClienteService.actualizar_cliente(cliente_id, update_data)
        updated["conexiones"] = await __get_conexiones_safe(cliente_id)
        return updated
    except CustomException as ce:
        logger.warning(f"Error de negocio al actualizar cliente {cliente_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception(f"Error inesperado en PUT /clientes/{cliente_id}/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al actualizar el cliente.",
        )


@router.delete(
    "/{cliente_id}/",
    response_model=ClienteResponse,
    summary="Soft delete de cliente",
    dependencies=[Depends(require_admin)],
)
async def eliminar_cliente(cliente_id: int):
    try:
        deleted = await ClienteService.eliminar_cliente_soft(cliente_id)
        deleted["conexiones"] = []
        return deleted
    except CustomException as ce:
        logger.warning(f"Error de negocio al eliminar cliente {cliente_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception(f"Error inesperado en DELETE /clientes/{cliente_id}/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al eliminar el cliente.",
        )


async def __get_conexiones_safe(cliente_id: int):
    """
    Helper interno para retornar conexiones del cliente sin romper el endpoint
    si hay un problema no crítico en la lectura de conexiones.
    """
    try:
        from app.services.cliente_conexion_service import ClienteConexionService

        return await ClienteConexionService.listar_conexiones_por_cliente(cliente_id)
    except Exception:
        return []

