# app/services/usuario_service.py
from datetime import datetime
import math
from typing import Dict, List, Optional, Any
import logging

# 🗄️ IMPORTACIONES DE BASE DE DATOS
from app.db.queries import (
    execute_query, execute_insert, execute_update, execute_auth_query,
    SELECT_USUARIOS_PAGINATED, COUNT_USUARIOS_PAGINATED
)

# 📋 SCHEMAS
from app.schemas.usuario import UsuarioReadWithRoles, PaginatedUsuarioResponse
from app.schemas.rol import RolRead

# 🔐 SEGURIDAD
from app.core.security import get_password_hash, verify_password

# 🚨 EXCEPCIONES - Nuevo sistema de manejo de errores
from app.core.exceptions import (
    ValidationError, NotFoundError, ConflictError, ServiceError, DatabaseError
)

# 🏗️ BASE SERVICE - Clase base para manejo consistente de errores
from app.services.base_service import BaseService

# 👥 SERVICIOS RELACIONADOS
from app.services.rol_service import RolService

logger = logging.getLogger(__name__)

class UsuarioService(BaseService):
    """
    Servicio para gestión completa de usuarios del sistema.
    
    ⚠️ IMPORTANTE: Este servicio maneja operaciones críticas relacionadas con:
    - Creación, actualización y eliminación de usuarios
    - Gestión de roles y permisos de usuarios
    - Autenticación y gestión de sesiones
    
    CARACTERÍSTICAS PRINCIPALES:
    - Herencia de BaseService para manejo automático de errores
    - Validaciones robustas de seguridad e integridad de datos
    - Manejo seguro de contraseñas con hash bcrypt
    - Logging detallado para auditoría de seguridad
    """

    @staticmethod
    @BaseService.handle_service_errors
    async def get_user_role_names(user_id: int) -> List[str]:
        """
        Obtiene solo los NOMBRES de roles activos para un usuario.
        
        🎯 OPTIMIZACIÓN: Diseñado específicamente para el endpoint de login
        donde solo se necesitan los nombres de roles, no toda la información.
        
        Args:
            user_id: ID del usuario cuyos roles se quieren obtener
            
        Returns:
            List[str]: Lista de nombres de roles activos del usuario
            
        Raises:
            ServiceError: Si hay errores en la consulta
        """
        role_names = []
        try:
            query = """
            SELECT r.nombre
            FROM dbo.rol r
            INNER JOIN dbo.usuario_rol ur ON r.rol_id = ur.rol_id
            WHERE ur.usuario_id = ? AND ur.es_activo = 1 AND r.es_activo = 1;
            """
            
            results = execute_query(query, (user_id,))
            
            if results:
                role_names = [row['nombre'] for row in results if 'nombre' in row]
                logger.debug(f"Roles obtenidos para usuario ID {user_id}: {role_names}")
            else:
                logger.debug(f"No se encontraron roles activos para usuario ID {user_id}")

        except DatabaseError as db_err:
            logger.error(f"Error de BD en get_user_role_names: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener nombres de roles",
                internal_code="ROLE_NAMES_RETRIEVAL_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en get_user_role_names: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener nombres de roles",
                internal_code="ROLE_NAMES_RETRIEVAL_UNEXPECTED_ERROR"
            )

        return role_names

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_usuario_por_id(usuario_id: int) -> Optional[Dict]:
        """
        Obtiene un usuario por su ID (excluyendo usuarios eliminados).
        
        🔍 BÚSQUEDA SEGURA:
        - Solo retorna usuarios no eliminados
        - Incluye todos los datos básicos del usuario
        - Retorna None si no existe
        
        Args:
            usuario_id: ID del usuario a buscar
            
        Returns:
            Optional[Dict]: Datos del usuario o None si no existe
            
        Raises:
            ServiceError: Si hay errores en la consulta
        """
        try:
            query = """
            SELECT
                usuario_id, nombre_usuario, correo, nombre, apellido,
                es_activo, correo_confirmado, fecha_creacion, fecha_ultimo_acceso,
                fecha_actualizacion
            FROM dbo.usuario
            WHERE usuario_id = ? AND es_eliminado = 0
            """
            
            resultados = execute_query(query, (usuario_id,))
            
            if not resultados:
                logger.debug(f"Usuario con ID {usuario_id} no encontrado o está eliminado")
                return None

            return resultados[0]

        except DatabaseError as db_err:
            logger.error(f"Error de BD al obtener usuario {usuario_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener usuario",
                internal_code="USER_RETRIEVAL_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al obtener usuario {usuario_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener usuario",
                internal_code="USER_RETRIEVAL_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def verificar_usuario_existente(nombre_usuario: str) -> bool:
        #, correo: str
        """        
        Verifica si ya existe un usuario con el mismo nombre de usuario o correo.
        
        🛡️ PREVENCIÓN DE DUPLICADOS:
        - Busca en toda la tabla (incluyendo inactivos y eliminados)
        - Comparación insensible a mayúsculas/minúsculas
        - Identifica exactamente qué campo causa conflicto
        
        Args:
            nombre_usuario: Nombre de usuario a verificar
            correo: Correo electrónico a verificar
            
        Returns:
            bool: False si no existe conflicto (éxito)
            
        Raises:
            ConflictError: Si ya existe un usuario con ese nombre o correo
        """
        try:
            query = """
            SELECT nombre_usuario
            FROM dbo.usuario
            WHERE (LOWER(nombre_usuario) = LOWER(?))
            """
            #, correo
            #OR LOWER(correo) = LOWER(?)
            params = (nombre_usuario.lower())
            #, correo.lower()
            resultados = execute_query(query, params)

            if resultados:
                # 🎯 IDENTIFICAR CAMPO EN CONFLICTO
                nombre_usuario_coincide = any(
                    r['nombre_usuario'].lower() == nombre_usuario.lower() 
                    for r in resultados
                )
                #correo_coincide = any(
                #    r['correo'].lower() == correo.lower() 
                #    for r in resultados
                #)

                if nombre_usuario_coincide:
                    raise ConflictError(
                        detail="El nombre de usuario ya está en uso.",
                        internal_code="USERNAME_CONFLICT"
                    )
                #if correo_coincide:
                #    raise ConflictError(
                #        detail="El correo electrónico ya está registrado.",
                #        internal_code="EMAIL_CONFLICT"
                #    )

            return False
            
        except ConflictError:
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD en verificar_usuario_existente: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al verificar usuario existente",
                internal_code="USER_VERIFICATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en verificar_usuario_existente: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al verificar usuario existente",
                internal_code="USER_VERIFICATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def crear_usuario(usuario_data: Dict) -> Dict:
        """
        Crea un nuevo usuario en el sistema con validaciones completas.
        
        🆕 CREACIÓN SEGURA:
        - Valida duplicados antes de insertar
        - Aplica hash seguro a la contraseña
        - Establece valores por defecto seguros
        
        Args:
            usuario_data: Datos del usuario a crear (incluye contraseña en texto plano)
            
        Returns:
            Dict: Usuario creado (sin contraseña)
            
        Raises:
            ConflictError: Si el nombre de usuario o correo ya existen
            ServiceError: Si la creación falla
        """
        logger.info(f"Intentando crear usuario: {usuario_data.get('nombre_usuario')}")
        
        try:
            # 🚫 VALIDAR DUPLICADOS
            await UsuarioService.verificar_usuario_existente(
                usuario_data['nombre_usuario']                
            )
            #usuario_data['correo']    
            # 🔐 APLICAR HASH SEGURO A CONTRASEÑA
            hashed_password = get_password_hash(usuario_data['contrasena'])

            # 💾 EJECUTAR INSERCIÓN
            insert_query = """
            INSERT INTO dbo.usuario (
                nombre_usuario, correo, contrasena, nombre, apellido,
                es_activo, correo_confirmado, es_eliminado,
                origen_datos, codigo_trabajador_externo
            )
            OUTPUT
                INSERTED.usuario_id, INSERTED.nombre_usuario, INSERTED.correo,
                INSERTED.nombre, INSERTED.apellido, INSERTED.es_activo,
                INSERTED.correo_confirmado, INSERTED.fecha_creacion,
                INSERTED.origen_datos, INSERTED.codigo_trabajador_externo
            VALUES (?, ?, ?, ?, ?, 1, 0, 0, ?, ?)
            """
            
            params = (
                usuario_data['nombre_usuario'],
                usuario_data['correo'],
                hashed_password,
                usuario_data.get('nombre'),
                usuario_data.get('apellido'),
                usuario_data.get('origen_datos', 'local'), 
                usuario_data.get('codigo_trabajador_externo').strip() if usuario_data.get('codigo_trabajador_externo') else None
            )
            
            result = execute_insert(insert_query, params)

            if not result:
                raise ServiceError(
                    status_code=500,
                    detail="No se pudo crear el usuario en la base de datos",
                    internal_code="USER_CREATION_FAILED"
                )

            logger.info(f"Usuario creado exitosamente con ID: {result.get('usuario_id')}")
            return result

        except (ValidationError, ConflictError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al crear usuario: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al crear usuario",
                internal_code="USER_CREATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al crear usuario: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al crear usuario",
                internal_code="USER_CREATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def actualizar_usuario(usuario_id: int, usuario_data: Dict) -> Dict:
        """
        Actualiza un usuario existente con validaciones de integridad.
        
        🔄 ACTUALIZACIÓN PARCIAL:
        - Solo actualiza campos proporcionados
        - Valida duplicados si se cambian campos únicos
        - Actualiza automáticamente la fecha de modificación
        
        Args:
            usuario_id: ID del usuario a actualizar
            usuario_data: Campos a actualizar (parcial)
            
        Returns:
            Dict: Usuario actualizado
            
        Raises:
            NotFoundError: Si el usuario no existe
            ConflictError: Si los nuevos datos causan conflictos
            ServiceError: Si la actualización falla
        """
        logger.info(f"Intentando actualizar usuario ID: {usuario_id}")

        try:
            # 🔍 VERIFICAR EXISTENCIA DEL USUARIO
            usuario_existente = await UsuarioService.obtener_usuario_por_id(usuario_id)
            if not usuario_existente:
                raise NotFoundError(
                    detail="Usuario no encontrado",
                    internal_code="USER_NOT_FOUND"
                )

            # 🚫 VALIDAR DUPLICADOS SI SE CAMBIAN CAMPOS ÚNICOS
            check_duplicates = False
            if 'nombre_usuario' in usuario_data and usuario_data['nombre_usuario'] != usuario_existente.get('nombre_usuario'):
                check_duplicates = True
            #if 'correo' in usuario_data and usuario_data['correo'] != usuario_existente.get('correo'):
            #    check_duplicates = True

            if check_duplicates:
                verify_query = """
                SELECT usuario_id, nombre_usuario
                FROM dbo.usuario
                WHERE (nombre_usuario = ?)
                AND usuario_id != ? AND es_eliminado = 0
                """
                #, correo
                #OR correo = ?
                check_nombre_usuario = usuario_data.get('nombre_usuario', usuario_existente.get('nombre_usuario'))
                #check_correo = usuario_data.get('correo', usuario_existente.get('correo'))
                params_verify = (check_nombre_usuario, usuario_id)
                #, check_correo
                duplicados = execute_query(verify_query, params_verify)

                if duplicados:
                    if any(d['nombre_usuario'] == check_nombre_usuario for d in duplicados):
                         raise ConflictError(
                             detail=f"El nombre de usuario '{check_nombre_usuario}' ya está en uso.",
                             internal_code="USERNAME_CONFLICT"
                         )
                    #if any(d['correo'] == check_correo for d in duplicados):
                    #     raise ConflictError(
                    #         detail=f"El correo '{check_correo}' ya está en uso.",
                    #         internal_code="EMAIL_CONFLICT"
                    #     )

            # 🛠️ CONSTRUIR ACTUALIZACIÓN DINÁMICA
            update_parts = []
            params_update = []
            campos_permitidos = {'nombre_usuario', 'correo', 'nombre', 'apellido', 'es_activo'}

            campos_actualizados = False
            for field in campos_permitidos:
                if field in usuario_data and usuario_data[field] is not None:
                    update_parts.append(f"{field} = ?")
                    params_update.append(usuario_data[field])
                    campos_actualizados = True

            if not campos_actualizados:
                logger.info(f"No hay campos válidos para actualizar para usuario ID {usuario_id}")
                raise ValidationError(
                    detail="No hay campos válidos para actualizar",
                    internal_code="NO_UPDATE_DATA"
                )

            update_parts.append("fecha_actualizacion = GETDATE()")
            params_update.append(usuario_id)

            # 💾 EJECUTAR ACTUALIZACIÓN
            update_query = f"""
            UPDATE dbo.usuario
            SET {', '.join(update_parts)}
            OUTPUT
                INSERTED.usuario_id, INSERTED.nombre_usuario, INSERTED.correo,
                INSERTED.nombre, INSERTED.apellido, INSERTED.es_activo,
                INSERTED.correo_confirmado, INSERTED.fecha_creacion, 
                INSERTED.fecha_actualizacion
            WHERE usuario_id = ? AND es_eliminado = 0
            """
            
            result = execute_update(update_query, tuple(params_update))

            if not result:
                logger.warning(f"No se pudo actualizar el usuario ID {usuario_id}")
                raise ServiceError(
                    status_code=404,
                    detail="Error al actualizar el usuario, no encontrado o no se pudo modificar",
                    internal_code="USER_UPDATE_FAILED"
                )

            logger.info(f"Usuario ID {usuario_id} actualizado exitosamente")
            return result

        except (ValidationError, NotFoundError, ConflictError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al actualizar usuario {usuario_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al actualizar usuario",
                internal_code="USER_UPDATE_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al actualizar usuario {usuario_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al actualizar usuario",
                internal_code="USER_UPDATE_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def eliminar_usuario(usuario_id: int) -> Dict:
        """
        Realiza un borrado lógico del usuario y desactiva sus roles.
        
        🗑️ ELIMINACIÓN SEGURA:
        - Borrado lógico (no físico)
        - Desactiva automáticamente al usuario
        - Desactiva todas sus asignaciones de roles
        
        Args:
            usuario_id: ID del usuario a eliminar
            
        Returns:
            Dict: Resultado de la eliminación con metadatos
            
        Raises:
            NotFoundError: Si el usuario no existe
            ServiceError: Si la eliminación falla
        """
        logger.info(f"Intentando eliminar usuario ID: {usuario_id}")

        try:
            # 🔍 VERIFICAR EXISTENCIA Y ESTADO
            check_query = "SELECT es_eliminado FROM dbo.usuario WHERE usuario_id = ?"
            user_status = execute_query(check_query, (usuario_id,))

            if not user_status:
                 raise NotFoundError(
                     detail="Usuario no encontrado",
                     internal_code="USER_NOT_FOUND"
                 )
                 
            if user_status[0]['es_eliminado']:
                 logger.info(f"Usuario ID {usuario_id} ya estaba eliminado")
                 return {
                     "message": "Usuario ya estaba eliminado", 
                     "usuario_id": usuario_id
                 }

            # 💾 EJECUTAR BORRADO LÓGICO
            update_query = """
            UPDATE dbo.usuario
            SET es_eliminado = 1, es_activo = 0, fecha_actualizacion = GETDATE()
            OUTPUT INSERTED.usuario_id, INSERTED.nombre_usuario, INSERTED.es_eliminado
            WHERE usuario_id = ? AND es_eliminado = 0
            """
            
            result = execute_update(update_query, (usuario_id,))

            if not result:
                logger.warning(f"No se pudo eliminar lógicamente el usuario ID {usuario_id}")
                raise ServiceError(
                    status_code=409,
                    detail="Conflicto al eliminar el usuario, posible concurrencia",
                    internal_code="USER_DELETION_CONFLICT"
                )

            # 🔄 DESACTIVAR ROLES ASOCIADOS
            try:
                deactivate_roles_query = """
                UPDATE dbo.usuario_rol SET es_activo = 0
                WHERE usuario_id = ? AND es_activo = 1
                """
                execute_update(deactivate_roles_query, (usuario_id,))
                logger.info(f"Roles desactivados para usuario eliminado ID {usuario_id}")
            except Exception as role_error:
                 logger.error(f"Error desactivando roles para usuario {usuario_id}: {role_error}")
                 # 🟡 NO FALLAR LA ELIMINACIÓN PRINCIPAL POR ESTO

            logger.info(f"Usuario ID {usuario_id} eliminado lógicamente exitosamente")
            return {
                "message": "Usuario eliminado lógicamente exitosamente",
                "usuario_id": result['usuario_id'],
                "es_eliminado": result['es_eliminado']
            }

        except (ValidationError, NotFoundError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al eliminar usuario {usuario_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al eliminar usuario",
                internal_code="USER_DELETION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al eliminar usuario {usuario_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al eliminar usuario",
                internal_code="USER_DELETION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def asignar_rol_a_usuario(usuario_id: int, rol_id: int) -> Dict:
        """
        Asigna un rol a un usuario con validaciones completas.
        
        🔄 COMPORTAMIENTO INTELIGENTE:
        - Si la asignación existe e está inactiva: la reactiva
        - Si la asignación existe y está activa: retorna la existente
        - Si no existe: crea una nueva asignación
        
        Args:
            usuario_id: ID del usuario
            rol_id: ID del rol a asignar
            
        Returns:
            Dict: Asignación usuario-rol creada o reactivada
            
        Raises:
            NotFoundError: Si el usuario o rol no existen
            ValidationError: Si el rol no está activo
            ServiceError: Si la asignación falla
        """
        logger.info(f"Intentando asignar rol {rol_id} a usuario {usuario_id}")

        try:
            # 👤 VALIDAR QUE EL USUARIO EXISTE
            usuario = await UsuarioService.obtener_usuario_por_id(usuario_id)
            if not usuario:
                raise NotFoundError(
                    detail=f"Usuario con ID {usuario_id} no encontrado.",
                    internal_code="USER_NOT_FOUND"
                )

            # 🎭 VALIDAR QUE EL ROL EXISTE Y ESTÁ ACTIVO
            rol = await RolService.obtener_rol_por_id(rol_id)
            if not rol:
                raise NotFoundError(
                    detail=f"Rol con ID {rol_id} no encontrado.",
                    internal_code="ROLE_NOT_FOUND"
                )
            if not rol['es_activo']:
                raise ValidationError(
                    detail=f"Rol con ID {rol_id} no está activo.",
                    internal_code="ROLE_INACTIVE"
                )

            # 🔍 VERIFICAR ASIGNACIÓN EXISTENTE
            check_query = """
            SELECT usuario_rol_id, es_activo
            FROM dbo.usuario_rol
            WHERE usuario_id = ? AND rol_id = ?
            """
            
            existing_assignment = execute_query(check_query, (usuario_id, rol_id))

            if existing_assignment:
                assignment = existing_assignment[0]
                
                if assignment['es_activo']:
                    # ✅ ASIGNACIÓN YA ACTIVA - Retornar existente
                    logger.info(f"Rol ID {rol_id} ya está asignado y activo para usuario ID {usuario_id}")
                    get_assignment_query = """
                    SELECT usuario_rol_id, usuario_id, rol_id, fecha_asignacion, es_activo
                    FROM dbo.usuario_rol WHERE usuario_rol_id = ?
                    """
                    final_result = execute_query(get_assignment_query, (assignment['usuario_rol_id'],))
                    if not final_result:
                        raise ServiceError(
                            status_code=500,
                            detail="Error obteniendo datos de asignación existente",
                            internal_code="EXISTING_ASSIGNMENT_RETRIEVAL_ERROR"
                        )
                    return final_result[0]
                else:
                    # 🔄 REACTIVAR ASIGNACIÓN EXISTENTE
                    logger.info(f"Reactivando asignación existente para usuario {usuario_id}, rol {rol_id}")
                    update_query = """
                    UPDATE dbo.usuario_rol
                    SET es_activo = 1, fecha_asignacion = GETDATE()
                    OUTPUT INSERTED.usuario_rol_id, INSERTED.usuario_id, INSERTED.rol_id,
                           INSERTED.fecha_asignacion, INSERTED.es_activo
                    WHERE usuario_rol_id = ?
                    """
                    result = execute_update(update_query, (assignment['usuario_rol_id'],))
                    if not result:
                        raise ServiceError(
                            status_code=500,
                            detail="Error reactivando la asignación de rol",
                            internal_code="ROLE_REACTIVATION_ERROR"
                        )
                    logger.info(f"Asignación reactivada exitosamente")
                    return result
            else:
                # 🆕 CREAR NUEVA ASIGNACIÓN
                logger.info(f"Creando nueva asignación para usuario {usuario_id}, rol {rol_id}")
                insert_query = """
                INSERT INTO dbo.usuario_rol (usuario_id, rol_id, es_activo)
                OUTPUT INSERTED.usuario_rol_id, INSERTED.usuario_id, INSERTED.rol_id,
                       INSERTED.fecha_asignacion, INSERTED.es_activo
                VALUES (?, ?, 1)
                """
                result = execute_insert(insert_query, (usuario_id, rol_id))
                if not result:
                    raise ServiceError(
                        status_code=500,
                        detail="Error creando la asignación de rol",
                        internal_code="ROLE_ASSIGNMENT_ERROR"
                    )
                logger.info(f"Asignación creada exitosamente")
                return result

        except (ValidationError, NotFoundError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al asignar rol: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al asignar rol",
                internal_code="ROLE_ASSIGNMENT_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al asignar rol: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al asignar rol",
                internal_code="ROLE_ASSIGNMENT_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def revocar_rol_de_usuario(usuario_id: int, rol_id: int) -> Dict:
        """
        Revoca (desactiva) un rol asignado a un usuario.
        
        🚫 REVOCACIÓN SEGURA:
        - Verifica que la asignación exista
        - Evita operaciones redundantes
        - Mantiene el registro histórico
        
        Args:
            usuario_id: ID del usuario
            rol_id: ID del rol a revocar
            
        Returns:
            Dict: Asignación revocada
            
        Raises:
            NotFoundError: Si la asignación no existe
            ServiceError: Si la revocación falla
        """
        logger.info(f"Intentando revocar rol {rol_id} de usuario {usuario_id}")

        try:
            # 🔍 VERIFICAR EXISTENCIA DE LA ASIGNACIÓN
            check_query = """
            SELECT usuario_rol_id, es_activo
            FROM dbo.usuario_rol
            WHERE usuario_id = ? AND rol_id = ?
            """
            
            existing_assignment = execute_query(check_query, (usuario_id, rol_id))

            if not existing_assignment:
                 raise NotFoundError(
                     detail=f"No existe asignación entre usuario ID {usuario_id} y rol ID {rol_id}.",
                     internal_code="ASSIGNMENT_NOT_FOUND"
                 )

            assignment = existing_assignment[0]
            if not assignment['es_activo']:
                logger.info(f"La asignación ya estaba inactiva para usuario {usuario_id}, rol {rol_id}")
                get_assignment_query = """
                SELECT usuario_rol_id, usuario_id, rol_id, fecha_asignacion, es_activo
                FROM dbo.usuario_rol WHERE usuario_rol_id = ?
                """
                final_result = execute_query(get_assignment_query, (assignment['usuario_rol_id'],))
                return final_result[0] if final_result else {"message": "Asignación ya inactiva"}

            # 🗑️ DESACTIVAR LA ASIGNACIÓN
            logger.info(f"Desactivando asignación para usuario {usuario_id}, rol {rol_id}")
            update_query = """
            UPDATE dbo.usuario_rol
            SET es_activo = 0
            OUTPUT INSERTED.usuario_rol_id, INSERTED.usuario_id, INSERTED.rol_id,
                   INSERTED.fecha_asignacion, INSERTED.es_activo
            WHERE usuario_rol_id = ? AND es_activo = 1
            """
            
            result = execute_update(update_query, (assignment['usuario_rol_id'],))

            if not result:
                logger.warning(f"No se pudo desactivar la asignación ID {assignment['usuario_rol_id']}")
                get_assignment_query = """
                SELECT usuario_rol_id, usuario_id, rol_id, fecha_asignacion, es_activo
                FROM dbo.usuario_rol WHERE usuario_rol_id = ?
                """
                final_result = execute_query(get_assignment_query, (assignment['usuario_rol_id'],))
                return final_result[0] if final_result else {"message": "No se pudo desactivar la asignación"}

            logger.info(f"Asignación desactivada exitosamente")
            return result

        except (ValidationError, NotFoundError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al revocar rol: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al revocar rol",
                internal_code="ROLE_REVOCATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al revocar rol: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al revocar rol",
                internal_code="ROLE_REVOCATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_roles_de_usuario(usuario_id: int) -> List[Dict]:
        """
        Obtiene la lista completa de roles activos asignados a un usuario.
        
        📋 LISTA DETALLADA:
        - Incluye todos los datos del rol
        - Solo roles activos (usuario y rol)
        - Ordenado por nombre del rol
        
        Args:
            usuario_id: ID del usuario cuyos roles se quieren obtener
            
        Returns:
            List[Dict]: Lista de roles activos del usuario
            
        Raises:
            ServiceError: Si hay errores en la consulta
        """
        try:
            query = """
            SELECT
                r.rol_id, r.nombre, r.descripcion, r.es_activo, r.fecha_creacion
            FROM dbo.rol r
            INNER JOIN dbo.usuario_rol ur ON r.rol_id = ur.rol_id
            WHERE ur.usuario_id = ? AND ur.es_activo = 1 AND r.es_activo = 1
            ORDER BY r.nombre;
            """
            
            roles = execute_query(query, (usuario_id,))
            logger.debug(f"Obtenidos {len(roles)} roles activos para usuario ID {usuario_id}")
            return roles

        except DatabaseError as db_err:
            logger.error(f"Error de BD al obtener roles: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener roles del usuario",
                internal_code="USER_ROLES_RETRIEVAL_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al obtener roles: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener roles del usuario",
                internal_code="USER_ROLES_RETRIEVAL_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def get_usuarios_paginated(
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None
    ) -> Dict:
        """
        Obtiene una lista paginada de usuarios con sus roles.
        
        📊 PAGINACIÓN EFICIENTE:
        - Combina datos de usuario y roles en consultas optimizadas
        - Búsqueda en múltiples campos
        - Metadatos completos de paginación
        
        Args:
            page: Número de página (comienza en 1)
            limit: Número de usuarios por página
            search: Término de búsqueda opcional
            
        Returns:
            Dict: Respuesta paginada con usuarios y metadatos
            
        Raises:
            ValidationError: Si los parámetros son inválidos
            ServiceError: Si hay errores en la consulta
        """
        logger.info(f"Obteniendo usuarios paginados: page={page}, limit={limit}, search='{search}'")

        # 🚫 VALIDAR PARÁMETROS
        if page < 1:
            raise ValidationError(
                detail="El número de página debe ser mayor o igual a 1.",
                internal_code="INVALID_PAGE_NUMBER"
            )
        if limit < 1:
            raise ValidationError(
                detail="El límite por página debe ser mayor o igual a 0.",
                internal_code="INVALID_LIMIT"
            )

        offset = (page - 1) * limit
        search_param = f"%{search}%" if search else None

        try:
            # 📊 CONTAR TOTAL DE USUARIOS
            count_params = (search_param, search_param, search_param, search_param, search_param)
            count_result = execute_query(COUNT_USUARIOS_PAGINATED, count_params)

            if not count_result or not isinstance(count_result, list) or len(count_result) == 0:
                logger.error("Error al contar usuarios: resultado inesperado")
                raise ServiceError(
                    status_code=500,
                    detail="Error al obtener el total de usuarios",
                    internal_code="USER_COUNT_ERROR"
                )

            # 🎯 EXTRAER TOTAL DE FORMA ROBUSTA
            total_usuarios = count_result[0].get('') 
            if total_usuarios is None:
                try:
                    total_usuarios = list(count_result[0].values())[0]
                except (IndexError, AttributeError):
                    logger.error(f"No se pudo extraer el total de usuarios: {count_result[0]}")
                    raise ServiceError(
                        status_code=500,
                        detail="Error al interpretar el total de usuarios",
                        internal_code="USER_COUNT_PARSING_ERROR"
                    )

            logger.debug(f"Total de usuarios encontrados: {total_usuarios}")

            # 📋 OBTENER DATOS PAGINADOS CON ROLES
            # Parámetros: search (5 veces para WHERE), offset+1, offset+limit (para BETWEEN)
            start_row = offset + 1  # BETWEEN es inclusivo, ROW_NUMBER empieza en 1
            end_row = offset + limit
            data_params = (search_param, search_param, search_param, search_param, search_param, start_row, end_row)
            raw_results = execute_query(SELECT_USUARIOS_PAGINATED, data_params)

            # 🎯 PROCESAR RESULTADOS - AGRUPAR ROLES POR USUARIO
            usuarios_dict: Dict[int, UsuarioReadWithRoles] = {}
            
            if raw_results:
                logger.debug(f"Procesando {len(raw_results)} filas crudas")
                
                for row in raw_results:
                    usuario_id = row['usuario_id']
                    
                    if usuario_id not in usuarios_dict:
                        # 🆕 CREAR ENTRADA DE USUARIO
                        usuarios_dict[usuario_id] = UsuarioReadWithRoles(
                            usuario_id=row['usuario_id'],
                            nombre_usuario=row['nombre_usuario'],
                            correo=row['correo'],
                            nombre=row.get('nombre'),
                            apellido=row.get('apellido'),
                            es_activo=row['es_activo'],
                            correo_confirmado=row['correo_confirmado'],
                            fecha_creacion=row['fecha_creacion'],
                            fecha_ultimo_acceso=row.get('fecha_ultimo_acceso'),
                            fecha_actualizacion=row.get('fecha_actualizacion'),
                            roles=[]
                        )

                    # ➕ AGREGAR ROL SI EXISTE
                    if row.get('rol_id') is not None:
                        rol_obj = RolRead(
                            rol_id=row['rol_id'],
                            nombre=row['nombre_rol'],
                            descripcion=None,
                            es_activo=True,
                            fecha_creacion=datetime.now()
                        )
                        
                        # 🚫 EVITAR DUPLICADOS
                        if rol_obj not in usuarios_dict[usuario_id].roles:
                            usuarios_dict[usuario_id].roles.append(rol_obj)

            lista_usuarios_procesados = list(usuarios_dict.values())
            logger.debug(f"Procesados {len(lista_usuarios_procesados)} usuarios únicos")

            # 🧮 CALCULAR METADATOS DE PAGINACIÓN
            total_paginas = math.ceil(total_usuarios / limit) if limit > 0 else 0

            # 📦 CONSTRUIR RESPUESTA FINAL
            response_data = {
                "usuarios": [u.model_dump() for u in lista_usuarios_procesados],
                "total_usuarios": total_usuarios,
                "pagina_actual": page,
                "total_paginas": total_paginas
            }

            logger.info(f"Obtención paginada de usuarios completada exitosamente")
            return response_data

        except (ValidationError, ServiceError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD en get_usuarios_paginated: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener usuarios paginados",
                internal_code="USER_PAGINATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en get_usuarios_paginated: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener usuarios paginados",
                internal_code="USER_PAGINATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def resetear_contrasena(usuario_id: int, nueva_contrasena: str) -> Dict:
        """
        Resetea la contraseña de un usuario (solo para administradores).
        
        🔐 RESET SEGURO:
        - Verifica que el usuario exista y no esté eliminado
        - Detecta origen_datos para actualizar en la tabla correcta:
          - Si origen_datos='local' → actualiza en tabla usuario (con hash bcrypt)
          - Si origen_datos='cliente' → actualiza en tabla usuarios_web00 (texto plano)
        - Actualiza fecha de modificación
        - No requiere conocer la contraseña actual
        
        Args:
            usuario_id: ID del usuario cuya contraseña se reseteará
            nueva_contrasena: Nueva contraseña en texto plano
            
        Returns:
            Dict: Resultado del reset con metadatos
            
        Raises:
            NotFoundError: Si el usuario no existe
            ServiceError: Si el reset falla
        """
        logger.info(f"Intentando resetear contraseña para usuario ID: {usuario_id}")

        try:
            # 🔍 VERIFICAR EXISTENCIA DEL USUARIO Y OBTENER ORIGEN_DATOS
            from app.db.queries import GET_NOMBRE_USUARIO_BY_ID, UPDATE_CLIENTE_PASSWORD, AUTHENTICATE_CLIENTE_USER
            usuario_info = execute_query(GET_NOMBRE_USUARIO_BY_ID, (usuario_id,))
            
            if not usuario_info:
                raise NotFoundError(
                    detail="Usuario no encontrado",
                    internal_code="USER_NOT_FOUND"
                )
            
            usuario_data = usuario_info[0]
            origen_datos = usuario_data.get('origen_datos', 'local')
            nombre_usuario = usuario_data.get('nombre_usuario')

            if origen_datos == 'cliente':
                # 🟢 USUARIO CLIENTE: Actualizar en usuarios_web00 (texto plano)
                logger.info(f"Reseteando contraseña en usuarios_web00 para usuario cliente '{nombre_usuario}'")
                
                # Actualizar en usuarios_web00 (contraseña en texto plano)
                update_query_cliente = UPDATE_CLIENTE_PASSWORD
                execute_update(update_query_cliente, (nueva_contrasena, nombre_usuario))
                
                # Obtener datos del usuario para la respuesta
                usuario_existente = await UsuarioService.obtener_usuario_por_id(usuario_id)
                
                logger.info(f"Contraseña reseteada exitosamente en usuarios_web00 para usuario ID {usuario_id}")
                return {
                    "message": "Contraseña reseteada exitosamente en sistema cliente",
                    "usuario_id": usuario_id,
                    "nombre_usuario": nombre_usuario,
                    "origen_datos": "cliente"
                }
            else:
                # 🔵 USUARIO LOCAL: Actualizar en tabla usuario (con hash bcrypt)
                logger.info(f"Reseteando contraseña en tabla usuario para usuario local ID {usuario_id}")
                
                # 🔐 APLICAR HASH SEGURO A NUEVA CONTRASEÑA
                hashed_password = get_password_hash(nueva_contrasena)

                # 💾 EJECUTAR ACTUALIZACIÓN DE CONTRASEÑA
                update_query = """
                UPDATE dbo.usuario
                SET contrasena = ?, fecha_actualizacion = GETDATE()
                OUTPUT
                    INSERTED.usuario_id, INSERTED.nombre_usuario, INSERTED.correo,
                    INSERTED.nombre, INSERTED.apellido, INSERTED.es_activo
                WHERE usuario_id = ? AND es_eliminado = 0
                """
                
                result = execute_update(update_query, (hashed_password, usuario_id))

                if not result:
                    logger.warning(f"No se pudo resetear la contraseña del usuario ID {usuario_id}")
                    raise ServiceError(
                        status_code=404,
                        detail="Error al resetear la contraseña, usuario no encontrado o no se pudo modificar",
                        internal_code="PASSWORD_RESET_FAILED"
                    )

                logger.info(f"Contraseña reseteada exitosamente para usuario ID {usuario_id}")
                return {
                    "message": "Contraseña reseteada exitosamente",
                    "usuario_id": result['usuario_id'],
                    "nombre_usuario": result['nombre_usuario'],
                    "origen_datos": "local"
                }

        except (NotFoundError, ValidationError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al resetear contraseña para usuario {usuario_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al resetear contraseña",
                internal_code="PASSWORD_RESET_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al resetear contraseña para usuario {usuario_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al resetear contraseña",
                internal_code="PASSWORD_RESET_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def cambiar_contrasena_propia(usuario_id: int, contrasena_actual: str, nueva_contrasena: str) -> Dict:
        """
        Permite a un usuario cambiar su propia contraseña.
        
        🔐 CAMBIO SEGURO:
        - Verifica que el usuario exista y no esté eliminado
        - Detecta origen_datos para validar y actualizar en la tabla correcta:
          - Si origen_datos='local' → valida contra tabla usuario (hash bcrypt) y actualiza ahí
          - Si origen_datos='cliente' → valida contra usuarios_web00 (texto plano) y actualiza ahí
        - Valida la contraseña actual antes de cambiar
        - Aplica hash seguro a la nueva contraseña (solo para usuarios local)
        - Actualiza fecha de modificación
        
        Args:
            usuario_id: ID del usuario que cambiará su contraseña
            contrasena_actual: Contraseña actual en texto plano para verificación
            nueva_contrasena: Nueva contraseña en texto plano
            
        Returns:
            Dict: Resultado del cambio con metadatos
            
        Raises:
            NotFoundError: Si el usuario no existe
            ValidationError: Si la contraseña actual es incorrecta
            ServiceError: Si el cambio falla
        """
        logger.info(f"Intentando cambiar contraseña propia para usuario ID: {usuario_id}")

        try:
            # 🔍 VERIFICAR EXISTENCIA DEL USUARIO Y OBTENER ORIGEN_DATOS
            from app.db.queries import GET_NOMBRE_USUARIO_BY_ID, UPDATE_CLIENTE_PASSWORD, AUTHENTICATE_CLIENTE_USER
            
            usuario_info = execute_query(GET_NOMBRE_USUARIO_BY_ID, (usuario_id,))
            
            if not usuario_info:
                raise NotFoundError(
                    detail="Usuario no encontrado",
                    internal_code="USER_NOT_FOUND"
                )
            
            usuario_data = usuario_info[0]
            origen_datos = usuario_data.get('origen_datos', 'local')
            nombre_usuario = usuario_data.get('nombre_usuario')

            if origen_datos == 'cliente':
                # 🟢 USUARIO CLIENTE: Validar y actualizar en usuarios_web00 (texto plano)
                logger.info(f"Cambiando contraseña en usuarios_web00 para usuario cliente '{nombre_usuario}'")
                
                # Validar contraseña actual contra usuarios_web00
                cliente_user = execute_auth_query(AUTHENTICATE_CLIENTE_USER, (nombre_usuario,))
                
                if not cliente_user:
                    raise NotFoundError(
                        detail="Usuario no encontrado en sistema cliente",
                        internal_code="CLIENTE_USER_NOT_FOUND"
                    )
                
                if cliente_user['contrasena'] != contrasena_actual:
                    logger.warning(f"Intento de cambiar contraseña con contraseña actual incorrecta para usuario cliente '{nombre_usuario}'")
                    raise ValidationError(
                        detail="La contraseña actual es incorrecta",
                        internal_code="INVALID_CURRENT_PASSWORD"
                    )
                
                # Actualizar contraseña en usuarios_web00 (texto plano)
                execute_update(UPDATE_CLIENTE_PASSWORD, (nueva_contrasena, nombre_usuario))
                
                logger.info(f"Contraseña cambiada exitosamente en usuarios_web00 para usuario ID {usuario_id}")
                return {
                    "message": "Contraseña cambiada exitosamente en sistema cliente",
                    "usuario_id": usuario_id,
                    "nombre_usuario": nombre_usuario,
                    "origen_datos": "cliente"
                }
            else:
                # 🔵 USUARIO LOCAL: Validar y actualizar en tabla usuario (con hash bcrypt)
                logger.info(f"Cambiando contraseña en tabla usuario para usuario local ID {usuario_id}")
                
                # 🔍 VERIFICAR EXISTENCIA DEL USUARIO Y OBTENER CONTRASEÑA ACTUAL
                query = """
                SELECT usuario_id, nombre_usuario, contrasena, es_activo
                FROM dbo.usuario
                WHERE usuario_id = ? AND es_eliminado = 0
                """
                
                usuario_local_data = execute_query(query, (usuario_id,))
                
                if not usuario_local_data:
                    raise NotFoundError(
                        detail="Usuario no encontrado",
                        internal_code="USER_NOT_FOUND"
                    )

                usuario_local = usuario_local_data[0]
                
                # 🔐 VALIDAR CONTRASEÑA ACTUAL
                if not verify_password(contrasena_actual, usuario_local['contrasena']):
                    logger.warning(f"Intento de cambiar contraseña con contraseña actual incorrecta para usuario ID {usuario_id}")
                    raise ValidationError(
                        detail="La contraseña actual es incorrecta",
                        internal_code="INVALID_CURRENT_PASSWORD"
                    )

                # 🔐 APLICAR HASH SEGURO A NUEVA CONTRASEÑA
                hashed_password = get_password_hash(nueva_contrasena)

                # 💾 EJECUTAR ACTUALIZACIÓN DE CONTRASEÑA
                update_query = """
                UPDATE dbo.usuario
                SET contrasena = ?, fecha_actualizacion = GETDATE()
                OUTPUT
                    INSERTED.usuario_id, INSERTED.nombre_usuario, INSERTED.correo,
                    INSERTED.nombre, INSERTED.apellido, INSERTED.es_activo
                WHERE usuario_id = ? AND es_eliminado = 0
                """
                
                result = execute_update(update_query, (hashed_password, usuario_id))

                if not result:
                    logger.warning(f"No se pudo cambiar la contraseña del usuario ID {usuario_id}")
                    raise ServiceError(
                        status_code=404,
                        detail="Error al cambiar la contraseña, usuario no encontrado o no se pudo modificar",
                        internal_code="PASSWORD_CHANGE_FAILED"
                    )

                logger.info(f"Contraseña cambiada exitosamente para usuario ID {usuario_id}")
                return {
                    "message": "Contraseña cambiada exitosamente",
                    "usuario_id": result['usuario_id'],
                    "nombre_usuario": result['nombre_usuario'],
                    "origen_datos": "local"
                }

        except (NotFoundError, ValidationError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD al cambiar contraseña para usuario {usuario_id}: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al cambiar contraseña",
                internal_code="PASSWORD_CHANGE_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado al cambiar contraseña para usuario {usuario_id}: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al cambiar contraseña",
                internal_code="PASSWORD_CHANGE_UNEXPECTED_ERROR"
            )