"""
Módulo de endpoints para la administración de conexiones (subrutas de cliente).

Rutas:
- GET    /clientes/{id}/conexiones
- POST   /clientes/{id}/conexiones
- PUT    /clientes/{id}/conexiones/{con_id}
- DELETE /clientes/{id}/conexiones/{con_id}
"""

from fastapi import APIRouter, Body, Depends, HTTPException, status
from typing import List

from app.api.deps import RoleChecker
from app.core.exceptions import CustomException
from app.core.logging_config import get_logger
from app.schemas.cliente_conexion import ConexionCreate, ConexionResponse, ConexionUpdate
from app.services.cliente_conexion_service import ClienteConexionService

logger = get_logger(__name__)
router = APIRouter()

require_admin = RoleChecker(["Administrador"])


@router.get(
    "/{cliente_id}/conexiones",
    response_model=List[ConexionResponse],
    summary="Listar conexiones del cliente",
    dependencies=[Depends(require_admin)],
)
async def listar_conexiones(cliente_id: int):
    try:
        return await ClienteConexionService.listar_conexiones_por_cliente(cliente_id)
    except CustomException as ce:
        logger.warning(f"Error de negocio al listar conexiones del cliente {cliente_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception(f"Error inesperado en GET /clientes/{cliente_id}/conexiones")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al listar conexiones.",
        )


@router.post(
    "/{cliente_id}/conexiones",
    response_model=ConexionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear conexión para cliente",
    dependencies=[Depends(require_admin)],
)
async def crear_conexion(cliente_id: int, conexion_in: ConexionCreate = Body(...)):
    try:
        return await ClienteConexionService.crear_conexion(cliente_id, conexion_in.model_dump())
    except CustomException as ce:
        logger.warning(f"Error de negocio al crear conexión para cliente {cliente_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception(f"Error inesperado en POST /clientes/{cliente_id}/conexiones")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al crear la conexión.",
        )


@router.put(
    "/{cliente_id}/conexiones/{conexion_id}",
    response_model=ConexionResponse,
    summary="Actualizar conexión del cliente",
    dependencies=[Depends(require_admin)],
)
async def actualizar_conexion(cliente_id: int, conexion_id: int, conexion_in: ConexionUpdate = Body(...)):
    update_data = conexion_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se debe proporcionar al menos un campo para actualizar la conexión.",
        )
    try:
        return await ClienteConexionService.actualizar_conexion(cliente_id, conexion_id, update_data)
    except CustomException as ce:
        logger.warning(
            f"Error de negocio al actualizar conexión {conexion_id} del cliente {cliente_id}: {ce.detail}"
        )
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception(f"Error inesperado en PUT /clientes/{cliente_id}/conexiones/{conexion_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al actualizar la conexión.",
        )


@router.delete(
    "/{cliente_id}/conexiones/{conexion_id}",
    response_model=ConexionResponse,
    summary="Desactivar conexión del cliente",
    dependencies=[Depends(require_admin)],
)
async def desactivar_conexion(cliente_id: int, conexion_id: int):
    try:
        return await ClienteConexionService.desactivar_conexion(cliente_id, conexion_id)
    except CustomException as ce:
        logger.warning(
            f"Error de negocio al desactivar conexión {conexion_id} del cliente {cliente_id}: {ce.detail}"
        )
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception(f"Error inesperado en DELETE /clientes/{cliente_id}/conexiones/{conexion_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al desactivar la conexión.",
        )

