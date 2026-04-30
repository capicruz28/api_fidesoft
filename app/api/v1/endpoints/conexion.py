"""
Endpoint especial para apps móviles/desktop: búsqueda de conexiones por RUC y aplicación.

Protegido solo con JWT (usuario activo), sin requerimiento de rol administrador.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict

from app.api.deps import get_current_active_user
from app.core.exceptions import CustomException
from app.core.logging_config import get_logger
from app.schemas.usuario import UsuarioReadWithRoles
from app.services.cliente_conexion_service import ClienteConexionService

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/buscar",
    response_model=Dict,
    summary="Buscar conexiones por RUC y app",
    description="Devuelve conexiones activas del cliente activo para una aplicación dada.",
    dependencies=[Depends(get_current_active_user)],
)
async def buscar_conexion(
    ruc: str = Query(..., description="RUC del cliente"),
    app: str = Query(..., description="Código de la aplicación"),
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user),
):
    try:
        return await ClienteConexionService.get_conexiones_por_ruc(ruc=ruc, codigo_app=app)
    except CustomException as ce:
        logger.warning(f"Error de negocio en búsqueda de conexión (user={current_user.nombre_usuario}): {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception:
        logger.exception("Error inesperado en GET /conexion/buscar")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al buscar conexiones.",
        )

