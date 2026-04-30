"""
Módulo de endpoints para la administración de aplicaciones.

Incluye CRUD completo, con desactivación lógica en DELETE.
"""

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from typing import List, Optional

from app.api.deps import RoleChecker
from app.core.exceptions import CustomException
from app.core.logging_config import get_logger
from app.schemas.aplicacion import AplicacionCreate, AplicacionResponse, AplicacionUpdate
from app.services.aplicacion_service import AplicacionService

logger = get_logger(__name__)
router = APIRouter()

require_admin = RoleChecker(["Administrador"])


@router.get(
    "/",
    response_model=List[AplicacionResponse],
    summary="Listar aplicaciones",
    dependencies=[Depends(require_admin)],
)
async def listar_aplicaciones(
    incluir_inactivas: bool = Query(True, description="Incluir aplicaciones inactivas"),
):
    try:
        return await AplicacionService.listar_aplicaciones(incluir_inactivas=incluir_inactivas)
    except CustomException as ce:
        logger.warning(f"Error de negocio al listar aplicaciones: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception("Error inesperado en GET /aplicaciones/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al listar aplicaciones.",
        )


@router.get(
    "/{aplicacion_id}/",
    response_model=AplicacionResponse,
    summary="Detalle de aplicación",
    dependencies=[Depends(require_admin)],
)
async def obtener_aplicacion(aplicacion_id: int):
    try:
        app = await AplicacionService.obtener_aplicacion_por_id(aplicacion_id)
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aplicación con ID {aplicacion_id} no encontrada.",
            )
        return app
    except HTTPException:
        raise
    except CustomException as ce:
        logger.warning(f"Error de negocio al obtener aplicación {aplicacion_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception(f"Error inesperado en GET /aplicaciones/{aplicacion_id}/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener la aplicación.",
        )


@router.post(
    "/",
    response_model=AplicacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear aplicación",
    dependencies=[Depends(require_admin)],
)
async def crear_aplicacion(aplicacion_in: AplicacionCreate = Body(...)):
    try:
        return await AplicacionService.crear_aplicacion(aplicacion_in.model_dump())
    except CustomException as ce:
        logger.warning(f"Error de negocio al crear aplicación: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception("Error inesperado en POST /aplicaciones/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al crear la aplicación.",
        )


@router.put(
    "/{aplicacion_id}/",
    response_model=AplicacionResponse,
    summary="Actualizar aplicación",
    dependencies=[Depends(require_admin)],
)
async def actualizar_aplicacion(aplicacion_id: int, aplicacion_in: AplicacionUpdate = Body(...)):
    update_data = aplicacion_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se debe proporcionar al menos un campo para actualizar la aplicación.",
        )

    try:
        return await AplicacionService.actualizar_aplicacion(aplicacion_id, update_data)
    except CustomException as ce:
        logger.warning(f"Error de negocio al actualizar aplicación {aplicacion_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception(f"Error inesperado en PUT /aplicaciones/{aplicacion_id}/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al actualizar la aplicación.",
        )


@router.delete(
    "/{aplicacion_id}/",
    response_model=AplicacionResponse,
    summary="Desactivar aplicación",
    dependencies=[Depends(require_admin)],
)
async def desactivar_aplicacion(aplicacion_id: int):
    try:
        return await AplicacionService.desactivar_aplicacion(aplicacion_id)
    except CustomException as ce:
        logger.warning(f"Error de negocio al desactivar aplicación {aplicacion_id}: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception(f"Error inesperado en DELETE /aplicaciones/{aplicacion_id}/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al desactivar la aplicación.",
        )

