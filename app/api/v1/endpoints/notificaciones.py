# app/api/v1/endpoints/notificaciones.py
"""
Endpoints para gestión de notificaciones push.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
import logging

from app.schemas.vacaciones_permisos import (
    DispositivoRegistroToken,
    DispositivoRegistroResponse
)
from app.services.notificaciones_service import NotificacionesService
from app.api.deps import get_current_active_user
from app.schemas.usuario import UsuarioReadWithRoles
from app.api.v1.endpoints.vacaciones_permisos_mobile import obtener_codigo_trabajador

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/registrar-token",
    response_model=DispositivoRegistroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar token de dispositivo",
    description="Registra o actualiza el token FCM de un dispositivo asociado a un usuario"
)
async def registrar_token_dispositivo(
    dispositivo_data: DispositivoRegistroToken,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """
    Registra o actualiza el token FCM de un dispositivo.
    
    Validaciones:
    - El código_trabajador debe corresponder al usuario autenticado
    - El token_fcm debe ser único
    - La plataforma debe ser 'A' (Android) o 'I' (iOS)
    """
    try:
        # Verificar que el código de trabajador corresponde al usuario autenticado
        codigo_trabajador_usuario = obtener_codigo_trabajador(current_user)
        
        if dispositivo_data.codigo_trabajador != codigo_trabajador_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El código de trabajador no corresponde al usuario autenticado"
            )
        
        # Registrar o actualizar token
        resultado = await NotificacionesService.registrar_token_dispositivo(
            token_fcm=dispositivo_data.token_fcm,
            codigo_trabajador=dispositivo_data.codigo_trabajador,
            plataforma=dispositivo_data.plataforma,
            modelo_dispositivo=dispositivo_data.modelo_dispositivo,
            version_app=dispositivo_data.version_app,
            version_so=dispositivo_data.version_so
        )
        
        logger.info(
            f"Token registrado/actualizado para usuario {current_user.nombre_usuario}, "
            f"dispositivo {resultado.get('id_dispositivo')}"
        )
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error registrando token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al registrar token del dispositivo"
        )


@router.post(
    "/test-envio",
    summary="Probar envío de notificación",
    description="Endpoint de prueba para verificar que el envío de notificaciones funciona"
)
async def test_envio_notificacion(
    token_fcm: str = Query(..., description="Token FCM a probar"),
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """
    Endpoint de prueba para verificar que el envío de notificaciones funciona.
    Usar con el token_fcm del aprobador desde la base de datos.
    """
    try:
        from firebase_admin import messaging
        
        # Verificar que Firebase esté disponible
        try:
            import firebase_admin
            from firebase_admin import messaging
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Firebase Admin SDK no está disponible. Instale firebase-admin."
            )
        
        message = messaging.Message(
            notification=messaging.Notification(
                title="Prueba de Notificación",
                body="Esta es una notificación de prueba desde el backend"
            ),
            data={
                "tipo_solicitud": "V",
                "id_solicitud": "999",
                "tipo": "test"
            },
            token=token_fcm,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    channel_id='fidesoft_channel',
                    sound='default'
                )
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1
                    )
                )
            )
        )
        
        response = messaging.send(message)
        logger.info(f"Notificación de prueba enviada exitosamente: {response}")
        
        return {
            "success": True,
            "message": "Notificación enviada exitosamente",
            "message_id": response
        }
    except Exception as e:
        logger.exception(f"Error en prueba de notificación: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al enviar notificación de prueba: {str(e)}"
        )
