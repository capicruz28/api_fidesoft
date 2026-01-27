# app/services/notificaciones_service.py
"""
Servicio para manejo de notificaciones push usando Firebase Cloud Messaging.
"""

import logging
from typing import List, Dict, Any, Optional
from app.db.queries import (
    SELECT_DISPOSITIVO_BY_TOKEN,
    INSERT_DISPOSITIVO,
    UPDATE_DISPOSITIVO_TOKEN,
    SELECT_TOKENS_APROBADORES,
    SELECT_TOKENS_BY_CODIGOS_TRABAJADORES,
    SELECT_AREA_TRABAJADOR,
    SELECT_APROBADORES_POR_TRABAJADOR
)
from app.db.queries import execute_query, execute_insert, execute_update
from app.core.exceptions import ServiceError
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)

# Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("firebase-admin no está instalado. Las notificaciones push no funcionarán.")


class NotificacionesService(BaseService):
    """Servicio para manejo de notificaciones push"""

    @staticmethod
    def inicializar_firebase(credential_path: Optional[str] = None):
        """
        Inicializa Firebase Admin SDK.
        
        Args:
            credential_path: Ruta al archivo JSON de credenciales de Firebase.
                            Si es None, intenta usar variable de entorno o inicialización previa.
        """
        if not FIREBASE_AVAILABLE:
            logger.error("Firebase Admin SDK no está disponible")
            return False
        
        try:
            # Verificar si ya está inicializado
            try:
                firebase_admin.get_app()
                logger.info("Firebase Admin SDK ya está inicializado")
                return True
            except ValueError:
                # No está inicializado, proceder a inicializar
                pass
            
            if credential_path:
                cred = credentials.Certificate(credential_path)
                firebase_admin.initialize_app(cred)
                logger.info(f"Firebase Admin SDK inicializado con credenciales de: {credential_path}")
            else:
                # Intentar usar credenciales por defecto (variable de entorno GOOGLE_APPLICATION_CREDENTIALS)
                firebase_admin.initialize_app()
                logger.info("Firebase Admin SDK inicializado con credenciales por defecto")
            
            return True
        except Exception as e:
            logger.error(f"Error inicializando Firebase Admin SDK: {str(e)}")
            return False

    @staticmethod
    @BaseService.handle_service_errors
    async def registrar_token_dispositivo(
        token_fcm: str,
        codigo_trabajador: str,
        plataforma: str,
        modelo_dispositivo: Optional[str] = None,
        version_app: Optional[str] = None,
        version_so: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Registra o actualiza el token FCM de un dispositivo.
        
        Args:
            token_fcm: Token de Firebase Cloud Messaging
            codigo_trabajador: Código del trabajador
            plataforma: 'A' (Android) o 'I' (iOS)
            modelo_dispositivo: Modelo del dispositivo (opcional)
            version_app: Versión de la app (opcional)
            version_so: Versión del SO (opcional)
            
        Returns:
            Dict con id_dispositivo y mensaje
        """
        try:
            # Verificar si el token ya existe
            dispositivo_existente = execute_query(
                SELECT_DISPOSITIVO_BY_TOKEN,
                (token_fcm,)
            )
            
            if dispositivo_existente:
                # Actualizar dispositivo existente
                params = (
                    modelo_dispositivo,
                    version_app,
                    version_so,
                    token_fcm
                )
                resultado = execute_update(UPDATE_DISPOSITIVO_TOKEN, params)
                
                if resultado and 'id_dispositivo' in resultado:
                    id_dispositivo = resultado['id_dispositivo']
                    logger.info(f"Token actualizado para dispositivo {id_dispositivo}")
                    return {
                        'mensaje': 'Token actualizado exitosamente',
                        'id_dispositivo': id_dispositivo
                    }
                else:
                    raise ServiceError(
                        status_code=500,
                        detail="Error al actualizar el token",
                        internal_code="TOKEN_UPDATE_ERROR"
                    )
            else:
                # Insertar nuevo dispositivo
                params = (
                    codigo_trabajador,
                    token_fcm,
                    plataforma,
                    modelo_dispositivo,
                    version_app,
                    version_so
                )
                resultado = execute_insert(INSERT_DISPOSITIVO, params)
                
                if resultado and 'id_dispositivo' in resultado:
                    id_dispositivo = resultado['id_dispositivo']
                    logger.info(f"Token registrado para dispositivo {id_dispositivo}")
                    return {
                        'mensaje': 'Token registrado exitosamente',
                        'id_dispositivo': id_dispositivo
                    }
                else:
                    raise ServiceError(
                        status_code=500,
                        detail="Error al registrar el token",
                        internal_code="TOKEN_REGISTER_ERROR"
                    )
                    
        except Exception as e:
            logger.exception(f"Error registrando token: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error al registrar token del dispositivo",
                internal_code="TOKEN_REGISTER_ERROR"
            )

    @staticmethod
    def obtener_tokens_aprobadores(codigo_area: str) -> List[str]:
        """
        Obtiene los tokens FCM de los aprobadores de un área.
        
        Args:
            codigo_area: Código del área
            
        Returns:
            Lista de tokens FCM
        """
        try:
            resultado = execute_query(
                SELECT_TOKENS_APROBADORES,
                (codigo_area,)
            )
            
            tokens = [row['token_fcm'] for row in resultado if row.get('token_fcm')]
            logger.info(
                f"Se encontraron {len(tokens)} tokens para aprobadores del área {codigo_area}. "
                f"Total aprobadores encontrados: {len(resultado)}"
            )
            
            if resultado and len(tokens) == 0:
                logger.warning(
                    f"Se encontraron {len(resultado)} aprobadores pero ninguno tiene token FCM válido. "
                    f"Códigos: {[r.get('codigo_trabajador') for r in resultado]}"
                )
            
            return tokens
            
        except Exception as e:
            logger.exception(f"Error obteniendo tokens de aprobadores: {str(e)}")
            return []
    
    @staticmethod
    def obtener_tokens_aprobadores_por_trabajador(codigo_trabajador: str) -> List[str]:
        """
        Obtiene los tokens FCM de los aprobadores según la jerarquía del trabajador solicitante.
        Este método es más preciso que obtener_tokens_aprobadores porque considera área, sección y cargo.
        
        Args:
            codigo_trabajador: Código del trabajador que creó la solicitud
            
        Returns:
            Lista de tokens FCM de los aprobadores
        """
        try:
            # Primero obtener los aprobadores según la jerarquía del trabajador
            aprobadores = execute_query(
                SELECT_APROBADORES_POR_TRABAJADOR,
                (codigo_trabajador,)
            )
            
            if not aprobadores:
                logger.warning(f"No se encontraron aprobadores para el trabajador {codigo_trabajador}")
                return []
            
            codigos_aprobadores = [apr['codigo_trabajador_aprobador'] for apr in aprobadores]
            logger.info(
                f"Se encontraron {len(codigos_aprobadores)} aprobadores para trabajador {codigo_trabajador}: {codigos_aprobadores}"
            )
            
            # Obtener tokens de esos aprobadores
            tokens = NotificacionesService.obtener_tokens_por_codigos(codigos_aprobadores)
            
            logger.info(
                f"Se obtuvieron {len(tokens)} tokens FCM de {len(codigos_aprobadores)} aprobadores para trabajador {codigo_trabajador}"
            )
            
            return tokens
            
        except Exception as e:
            logger.exception(f"Error obteniendo tokens de aprobadores por trabajador: {str(e)}")
            return []

    @staticmethod
    def obtener_tokens_por_codigos(codigos_trabajadores: List[str]) -> List[str]:
        """
        Obtiene los tokens FCM de una lista de códigos de trabajadores.
        
        Args:
            codigos_trabajadores: Lista de códigos de trabajadores
            
        Returns:
            Lista de tokens FCM
        """
        try:
            if not codigos_trabajadores:
                return []
            
            # Construir query con placeholders dinámicos
            # SQL Server requiere que los placeholders sean explícitos
            placeholders = ','.join(['?' for _ in codigos_trabajadores])
            query = SELECT_TOKENS_BY_CODIGOS_TRABAJADORES.format(placeholders)
            
            resultado = execute_query(query, tuple(codigos_trabajadores))
            
            tokens = [row['token_fcm'] for row in resultado if row.get('token_fcm')]
            logger.info(f"Se encontraron {len(tokens)} tokens para {len(codigos_trabajadores)} trabajadores")
            return tokens
            
        except Exception as e:
            logger.exception(f"Error obteniendo tokens por códigos: {str(e)}")
            return []

    @staticmethod
    def enviar_notificacion_multicast(
        tokens: List[str],
        titulo: str,
        cuerpo: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Envía una notificación push a múltiples dispositivos usando Firebase Cloud Messaging.
        
        Args:
            tokens: Lista de tokens FCM
            titulo: Título de la notificación
            cuerpo: Cuerpo de la notificación
            data: Datos adicionales (opcional)
            
        Returns:
            Dict con información del resultado del envío
        """
        if not FIREBASE_AVAILABLE:
            logger.warning("Firebase Admin SDK no está disponible. No se puede enviar notificación.")
            return {
                'enviado': False,
                'mensaje': 'Firebase Admin SDK no está disponible',
                'success_count': 0,
                'failure_count': len(tokens) if tokens else 0
            }
        
        if not tokens:
            logger.warning("No hay tokens para enviar notificación")
            return {
                'enviado': False,
                'mensaje': 'No hay tokens disponibles',
                'success_count': 0,
                'failure_count': 0
            }
        
        try:
            # Preparar datos
            data_dict = data or {}
            # Asegurar que todos los valores en data sean strings
            data_dict = {k: str(v) for k, v in data_dict.items()}
            
            # Crear mensaje multicast
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=titulo,
                    body=cuerpo
                ),
                data=data_dict,
                tokens=tokens,
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
            
            # Enviar notificación
            response = messaging.send_multicast(message)
            
            logger.info(
                f"Notificaciones enviadas: {response.success_count}/{len(tokens)} exitosas, "
                f"{response.failure_count} fallidas"
            )
            
            # Manejar tokens inválidos
            if response.failure_count > 0:
                invalid_tokens = []
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        if resp.exception:
                            error_code = resp.exception.code
                            error_message = str(resp.exception)
                            logger.warning(
                                f"Error enviando notificación a token {idx}: {error_code} - {error_message}"
                            )
                            # Códigos que indican token inválido
                            if error_code in ['INVALID_ARGUMENT', 'UNREGISTERED', 'NOT_FOUND']:
                                invalid_tokens.append(tokens[idx])
                
                if invalid_tokens:
                    logger.warning(f"Se encontraron {len(invalid_tokens)} tokens inválidos que deberían marcarse como inactivos")
                    # TODO: Marcar tokens como inactivos en la BD
            
            return {
                'enviado': True,
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'total_tokens': len(tokens)
            }
            
        except Exception as e:
            logger.exception(f"Error enviando notificación multicast: {str(e)}")
            return {
                'enviado': False,
                'mensaje': str(e),
                'success_count': 0,
                'failure_count': len(tokens) if tokens else 0
            }

    @staticmethod
    async def enviar_notificacion_nueva_solicitud(
        id_solicitud: int,
        tipo_solicitud: str,
        codigo_trabajador: str,
        nombre_trabajador: str,
        codigo_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía notificación push cuando se crea una nueva solicitud.
        
        Args:
            id_solicitud: ID de la solicitud creada
            tipo_solicitud: 'V' (vacaciones) o 'P' (permiso)
            codigo_trabajador: Código del trabajador que creó la solicitud
            nombre_trabajador: Nombre del trabajador
            codigo_area: Código del área del trabajador (opcional, se obtiene si no se proporciona)
            
        Returns:
            Dict con información del resultado del envío
        """
        try:
            # Si no se proporciona código de área, obtenerlo del trabajador
            if not codigo_area:
                area_result = execute_query(
                    SELECT_AREA_TRABAJADOR,
                    (codigo_trabajador,)
                )
                if area_result and area_result[0].get('codigo_area'):
                    codigo_area = area_result[0]['codigo_area']
                else:
                    logger.warning(f"No se pudo obtener código de área para trabajador {codigo_trabajador}")
                    return {
                        'enviado': False,
                        'mensaje': 'No se pudo determinar el área del trabajador',
                        'success_count': 0,
                        'failure_count': 0
                    }
            
            # Obtener tokens de aprobadores según la jerarquía del trabajador
            # Usar método más preciso que considera área, sección y cargo
            tokens = NotificacionesService.obtener_tokens_aprobadores_por_trabajador(codigo_trabajador)
            
            # Si no hay tokens con el método preciso, intentar con el método por área
            if not tokens:
                logger.info(f"No se encontraron tokens con método preciso, intentando por área {codigo_area}")
                tokens = NotificacionesService.obtener_tokens_aprobadores(codigo_area)
            
            if not tokens:
                logger.warning(
                    f"No hay tokens de aprobadores para trabajador {codigo_trabajador} (área: {codigo_area}). "
                    f"Verificar que existan aprobadores en ppavac_jerarquia y tokens en ppavac_dispositivo."
                )
                return {
                    'enviado': False,
                    'mensaje': 'No hay aprobadores con tokens registrados',
                    'success_count': 0,
                    'failure_count': 0
                }
            
            logger.info(f"Se enviarán notificaciones a {len(tokens)} dispositivos para solicitud {id_solicitud}")
            
            # Preparar mensaje
            tipo_texto = 'vacaciones' if tipo_solicitud == 'V' else 'permiso'
            titulo = "Nueva solicitud pendiente"
            cuerpo = f"Solicitud de {tipo_texto} de {nombre_trabajador}"
            
            # Preparar datos
            data = {
                'tipo_solicitud': tipo_solicitud,
                'id_solicitud': str(id_solicitud),
                'codigo_trabajador': codigo_trabajador,
                'tipo': 'nueva_solicitud'
            }
            
            # Enviar notificación
            logger.info(
                f"Enviando notificación push para solicitud {id_solicitud}: "
                f"tipo={tipo_solicitud}, trabajador={codigo_trabajador}, tokens={len(tokens)}"
            )
            
            resultado = NotificacionesService.enviar_notificacion_multicast(
                tokens=tokens,
                titulo=titulo,
                cuerpo=cuerpo,
                data=data
            )
            
            if resultado.get('enviado'):
                logger.info(
                    f"✅ Notificación de nueva solicitud {id_solicitud} enviada exitosamente: "
                    f"{resultado.get('success_count', 0)}/{len(tokens)} dispositivos"
                )
            else:
                logger.error(
                    f"❌ Error enviando notificación para solicitud {id_solicitud}: "
                    f"{resultado.get('mensaje', 'Error desconocido')}"
                )
            
            return resultado
            
        except Exception as e:
            logger.exception(f"Error enviando notificación de nueva solicitud: {str(e)}")
            return {
                'enviado': False,
                'mensaje': str(e),
                'success_count': 0,
                'failure_count': 0
            }
