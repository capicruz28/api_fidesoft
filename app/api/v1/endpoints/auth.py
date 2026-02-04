# app/api/v1/endpoints/auth.py
"""
Módulo de endpoints para la gestión de la autenticación de usuarios (Login, Logout, Refresh Token).

Este módulo maneja el flujo de autenticación basado en JWT y cookies seguras.

Características principales:
- **Login:** Verifica credenciales, genera un Access Token y un Refresh Token (establecido en cookie HttpOnly).
- **Me:** Permite al usuario obtener su información y roles usando el Access Token.
- **Refresh:** Genera un nuevo Access Token usando el Refresh Token de la cookie (implementando rotación de refresh token).
- **Logout:** Elimina la cookie del Refresh Token para cerrar la sesión.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict

from app.schemas.auth import Token, UserDataWithRoles
from app.schemas.usuario import UsuarioReadWithRoles, PasswordChange
from app.core.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_user_from_refresh,
)
from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.exceptions import CustomException
from app.services.usuario_service import UsuarioService
from app.api.deps import get_current_active_user

router = APIRouter()
logger = get_logger(__name__)

# ----------------------------------------------------------------------
# --- Endpoint para Login ---
# ----------------------------------------------------------------------
@router.post(
    "/login/",
    response_model=Token,
    summary="Autenticar usuario y obtener token",
    description="""
    Verifica credenciales (nombre de usuario/email y contraseña) proporcionadas mediante formulario `OAuth2PasswordRequestForm`. 
    Genera un **Access Token** (retornado en el cuerpo de la respuesta) y un **Refresh Token** (establecido como cookie HttpOnly) 
    para mantener la sesión y refrescar el Access Token. Retorna los datos básicos del usuario, incluyendo sus roles.

    **Respuestas:**
    - 200: Autenticación exitosa y tokens generados.
    - 401: Credenciales inválidas.
    - 500: Error interno del servidor durante el proceso.
    """
)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Realiza la autenticación del usuario y emite los tokens de sesión.

    Args:
        response: Objeto Response de FastAPI para manipular cookies.
        form_data: Objeto de formulario con `username` y `password` para autenticar.

    Returns:
        Token: Objeto que contiene el Access Token, tipo de token y los datos completos del usuario (`UserDataWithRoles`).

    Raises:
        HTTPException: Si la autenticación falla (401) o por un error interno (500).
    """
    usuario_service = UsuarioService()
    try:
        # 1) Autenticación (maneja 401 si falla)
        user_base_data = await authenticate_user(form_data.username, form_data.password)

        # 2) Roles
        user_id = user_base_data.get('usuario_id')
        user_role_names = await usuario_service.get_user_role_names(user_id=user_id)

        user_full_data = {**user_base_data, "roles": user_role_names}

        # 3) Tokens
        access_token = create_access_token(data={"sub": form_data.username})
        refresh_token = create_refresh_token(data={"sub": form_data.username})

        # 4) Setear refresh en cookie HttpOnly con configuración dinámica
        response.set_cookie(
            key=settings.REFRESH_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,      # False en dev, True en prod
            samesite=settings.COOKIE_SAMESITE,  # "none" en dev, "lax" en prod
            max_age=settings.REFRESH_COOKIE_MAX_AGE,
            path="/",
        )

        logger.info(f"Usuario {form_data.username} autenticado exitosamente")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_data": user_full_data
        }

    except HTTPException:
        # Re-lanza 401 si proviene de authenticate_user
        raise
    except Exception as e:
        logger.exception(f"Error inesperado en /login/ para usuario {form_data.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error inesperado durante el proceso de login."
        )

# ----------------------------------------------------------------------
# --- Endpoint para Obtener Usuario Actual (Me) ---
# ----------------------------------------------------------------------
@router.get(
    "/me/",
    response_model=UserDataWithRoles,
    summary="Obtener usuario actual",
    description="""
    Retorna los datos completos del usuario autenticado, incluyendo roles y metadatos. 
    Requiere un **Access Token válido** en el header `Authorization: Bearer <token>`.

    **Permisos requeridos:**
    - Autenticación (Access Token válido).

    **Respuestas:**
    - 200: Datos del usuario actual recuperados.
    - 401: Token inválido o expirado.
    - 500: Error interno del servidor.
    """
)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Recupera los datos del usuario identificado por el Access Token.

    Args:
        current_user: Diccionario con los datos del usuario extraídos del Access Token (proporcionado por `get_current_user`).

    Returns:
        UserDataWithRoles: Objeto con todos los datos del usuario, incluyendo roles.

    Raises:
        HTTPException: Si el token es inválido o expirado (401), o error interno (500).
    """
    logger.info(f"Solicitud /me/ recibida para usuario: {current_user.get('nombre_usuario')}")
    try:
        usuario_service = UsuarioService()
        user_id = current_user.get('usuario_id')
        # Obtener roles, que es la información extra
        user_role_names = await usuario_service.get_user_role_names(user_id=user_id)
        user_full_data = {**current_user, "roles": user_role_names}
        return user_full_data
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error en /me/: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo datos del usuario"
        )


# ----------------------------------------------------------------------
# --- Endpoint para Debug de Roles (útil para verificar roles) ---
# ----------------------------------------------------------------------
@router.get(
    "/me/roles/",
    response_model=Dict,
    summary="Obtener roles detallados del usuario actual",
    description="""
    Retorna información detallada de los roles del usuario autenticado.
    Útil para debugging y verificar qué roles tiene asignados.
    
    **Permisos requeridos:**
    - Autenticación (Access Token válido).
    """
)
async def get_my_roles(
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """
    Retorna información detallada de los roles del usuario actual.
    Útil para verificar si el rol 'SuperAdministrador' está correctamente asignado.
    """
    try:
        roles_info = []
        for role in current_user.roles:
            roles_info.append({
                "rol_id": role.rol_id,
                "nombre": role.nombre,
                "nombre_normalizado": role.nombre.strip().lower(),
                "descripcion": role.descripcion,
                "es_activo": role.es_activo
            })
        
        return {
            "usuario_id": current_user.usuario_id,
            "nombre_usuario": current_user.nombre_usuario,
            "roles": roles_info,
            "nombres_roles": [role.nombre for role in current_user.roles],
            "tiene_superadmin": any(
                role.nombre.strip().lower() == "superadministrador" 
                for role in current_user.roles
            )
        }
    except Exception as e:
        logger.exception(f"Error obteniendo roles detallados: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo roles del usuario"
        )

# ----------------------------------------------------------------------
# --- Endpoint para Refrescar Access Token ---
# ----------------------------------------------------------------------
@router.post(
    "/refresh/",
    response_model=Token,
    summary="Refrescar Access Token",
    description="""
    Genera un nuevo Access Token usando el **Refresh Token** que debe estar presente en la **cookie HttpOnly**. 
    Además, **rota el Refresh Token** (emite uno nuevo y lo reemplaza en la cookie) para mayor seguridad.

    **Respuestas:**
    - 200: Tokens refrescados exitosamente.
    - 401: Refresh Token ausente, inválido o expirado.
    - 500: Error interno del servidor.
    """
)
async def refresh_access_token(
    request: Request,
    response: Response,
    current_user: dict = Depends(get_current_user_from_refresh)
):
    """
    Genera un nuevo Access Token y rota el Refresh Token.

    Args:
        request: Objeto Request para inspeccionar cookies entrantes.
        response: Objeto Response para establecer la nueva cookie HttpOnly.
        current_user: Payload del Refresh Token validado (proporcionado por `get_current_user_from_refresh`).

    Returns:
        Token: Objeto que contiene el nuevo Access Token y tipo de token.

    Raises:
        HTTPException: Si el token es inválido (401) o error interno (500).
    """
    # Logs para depuración (mantenidos del código original)
    cookies = request.cookies
    logger.info(f"🍪 [REFRESH] Cookies recibidas: {list(cookies.keys())}")
    logger.info(f"🍪 [REFRESH] refresh_token presente: {'refresh_token' in cookies}")
    if settings.REFRESH_COOKIE_NAME in cookies:
        token_preview = cookies[settings.REFRESH_COOKIE_NAME][:30] if len(cookies[settings.REFRESH_COOKIE_NAME]) > 30 else cookies[settings.REFRESH_COOKIE_NAME]
        logger.info(f"🍪 [REFRESH] refresh_token value (primeros 30 chars): {token_preview}...")
    else:
        logger.warning(f"⚠️ [REFRESH] NO SE RECIBIÓ COOKIE {settings.REFRESH_COOKIE_NAME}")
    
    logger.info(f"🔍 [REFRESH] Headers recibidos: {dict(request.headers)}")

    try:
        username = current_user.get("nombre_usuario") # Asumiendo que el payload del refresh tiene "nombre_usuario" o "sub"
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no válido en el refresh token")

        # 1) Access
        new_access_token = create_access_token(data={"sub": username})

        # 2) Rotar refresh
        new_refresh_token = create_refresh_token(data={"sub": username})
        response.set_cookie(
            key=settings.REFRESH_COOKIE_NAME,
            value=new_refresh_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=settings.REFRESH_COOKIE_MAX_AGE,
            path="/",
        )
        logger.info(f"✅ [REFRESH] Token refrescado exitosamente para usuario: {username}")
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "user_data": None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error en /refresh/: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al refrescar el token"
        )

# ----------------------------------------------------------------------
# --- Endpoint para Cerrar Sesión (Logout) ---
# ----------------------------------------------------------------------
@router.post(
    "/logout/",
    summary="Cerrar sesión",
    description="""
    Cierra la sesión del usuario eliminando el **Refresh Token** de la cookie del navegador. 
    Esto invalida la capacidad de obtener nuevos Access Tokens.

    **Respuestas:**
    - 200: Cookie eliminada exitosamente.
    """
)
async def logout(response: Response):
    """
    Cierra la sesión eliminando la cookie del Refresh Token.

    Args:
        response: Objeto Response de FastAPI para manipular cookies.

    Returns:
        Dict[str, str]: Mensaje de éxito.

    Raises:
        None (Esta operación es idempotente y no suele fallar con un código de error de cliente/servidor).
    """
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path="/",
        samesite=settings.COOKIE_SAMESITE
    )
    logger.info("Usuario cerró sesión exitosamente")
    return {"message": "Sesión cerrada exitosamente"}

# ----------------------------------------------------------------------
# --- Endpoint para Cambiar Contraseña Propia ---
# ----------------------------------------------------------------------
@router.post(
    "/change-password/",
    response_model=dict,
    summary="Cambiar contraseña propia",
    description="""
    Permite a un usuario autenticado cambiar su propia contraseña proporcionando
    la contraseña actual y la nueva contraseña.
    
    **Permisos requeridos:**
    - Autenticación (Access Token válido en header `Authorization: Bearer <token>`)
    
    **Validaciones:**
    - La contraseña actual debe ser correcta
    - La nueva contraseña debe ser diferente a la actual
    - La nueva contraseña debe cumplir con las políticas de seguridad:
      - Mínimo 8 caracteres
      - Al menos una letra mayúscula
      - Al menos una letra minúscula
      - Al menos un número
    
    **Funciona para:**
    - Usuarios web (con Access Token en header Authorization)
    - Usuarios mobile (con Access Token en header Authorization)
    - Usuarios locales (origen_datos='local')
    - Usuarios cliente (origen_datos='cliente')
    
    **Respuestas:**
    - 200: Contraseña cambiada exitosamente
    - 400: Contraseña actual incorrecta o nueva contraseña igual a la actual
    - 401: Token inválido o expirado
    - 422: Error de validación en la nueva contraseña
    - 500: Error interno del servidor
    """
)
async def change_password(
    password_change: PasswordChange,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """
    Endpoint para que un usuario autenticado cambie su propia contraseña.
    
    Este endpoint funciona automáticamente con el usuario del token JWT,
    no requiere especificar usuario_id en la URL.
    
    Args:
        password_change: Datos con contraseña actual y nueva contraseña
        current_user: Usuario autenticado obtenido del Access Token
        
    Returns:
        dict: Resultado del cambio con metadatos
        
    Raises:
        HTTPException: En caso de error de validación, no autorizado o error interno
    """
    logger.info(f"Solicitud POST /auth/change-password/ recibida para usuario ID: {current_user.usuario_id}")
    
    try:
        usuario_service = UsuarioService()
        result = await usuario_service.cambiar_contrasena_propia(
            usuario_id=current_user.usuario_id,
            contrasena_actual=password_change.contrasena_actual,
            nueva_contrasena=password_change.nueva_contrasena
        )
        
        logger.info(f"Contraseña cambiada exitosamente para usuario ID {current_user.usuario_id}")
        return result
        
    except CustomException as ce:
        logger.warning(f"Error de negocio al cambiar contraseña para usuario {current_user.usuario_id}: {ce.detail}")
        raise HTTPException(
            status_code=ce.status_code, 
            detail=ce.detail
        )
    except Exception as e:
        logger.exception(f"Error inesperado en endpoint POST /auth/change-password/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al cambiar la contraseña."
        )