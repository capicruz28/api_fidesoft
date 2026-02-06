# app/schemas/vacaciones_permisos.py
"""
Esquemas Pydantic para el Sistema de Gestión de Vacaciones y Permisos.

Este módulo define todos los esquemas de validación, creación, actualización 
y lectura para solicitudes de vacaciones y permisos, aprobaciones, notificaciones
y configuraciones del sistema.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


# ============================================
# SCHEMAS BASE
# ============================================

class SolicitudBase(BaseModel):
    """Schema base para solicitudes de vacaciones y permisos"""
    tipo_solicitud: str = Field(..., description="Tipo de solicitud: V=Vacaciones, P=Permiso")
    codigo_permiso: Optional[str] = Field(None, max_length=2, description="Código del permiso (NULL si es vacación)")
    codigo_trabajador: str = Field(..., max_length=8, description="Código del trabajador que solicita")
    fecha_inicio: date = Field(..., description="Fecha inicio del periodo solicitado")
    fecha_fin: date = Field(..., description="Fecha fin del periodo solicitado")
    dias_solicitados: Optional[Decimal] = Field(None, description="Días solicitados (calculado)")
    observacion: Optional[str] = Field(None, max_length=500, description="Observaciones/comentarios")
    motivo: Optional[str] = Field(None, max_length=2, description="Código de motivo (opcional)")

    @field_validator('tipo_solicitud')
    @classmethod
    def validar_tipo_solicitud(cls, v: str) -> str:
        if v.upper() not in ['V', 'P']:
            raise ValueError('tipo_solicitud debe ser V (Vacaciones) o P (Permiso)')
        return v.upper()

    @model_validator(mode='after')
    def validar_fechas(self):
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError('fecha_fin debe ser mayor o igual a fecha_inicio')
        return self


# ============================================
# SCHEMAS DE CREACIÓN
# ============================================

class SolicitudCreate(SolicitudBase):
    """Schema para crear una nueva solicitud"""
    pass


class AprobacionCreate(BaseModel):
    """Schema para crear/actualizar una aprobación"""
    id_solicitud: int = Field(..., description="ID de la solicitud")
    nivel: int = Field(..., description="Nivel de aprobación (1, 2, 3...)")
    codigo_trabajador_aprueba: str = Field(..., max_length=8, description="Código del trabajador que aprueba")
    estado: str = Field(..., description="Estado: P=Pendiente, A=Aprobado, R=Rechazado")
    observacion: Optional[str] = Field(None, max_length=500, description="Comentarios del aprobador")
    ip_dispositivo: Optional[str] = Field(None, max_length=50, description="IP o ID del dispositivo")

    @field_validator('estado')
    @classmethod
    def validar_estado(cls, v: str) -> str:
        if v.upper() not in ['P', 'A', 'R']:
            raise ValueError('estado debe ser P (Pendiente), A (Aprobado) o R (Rechazado)')
        return v.upper()


class SustitutoCreate(BaseModel):
    """Schema para crear un sustituto temporal"""
    codigo_trabajador_titular: str = Field(..., max_length=8, description="Código del aprobador titular")
    codigo_trabajador_sustituto: str = Field(..., max_length=8, description="Código del sustituto")
    fecha_desde: date = Field(..., description="Inicio del periodo de sustitución")
    fecha_hasta: date = Field(..., description="Fin del periodo de sustitución")
    motivo: Optional[str] = Field(None, max_length=200, description="Motivo de la sustitución")
    observacion: Optional[str] = Field(None, max_length=200, description="Observaciones adicionales")

    @model_validator(mode='after')
    def validar_fechas(self):
        if self.fecha_hasta < self.fecha_desde:
            raise ValueError('fecha_hasta debe ser mayor o igual a fecha_desde')
        return self


class DispositivoCreate(BaseModel):
    """Schema para registrar un dispositivo para push notifications"""
    codigo_trabajador: str = Field(..., max_length=8, description="Código del trabajador")
    token_fcm: str = Field(..., max_length=500, description="Token de Firebase Cloud Messaging")
    plataforma: str = Field(..., description="Plataforma: A=Android, I=iOS")
    modelo_dispositivo: Optional[str] = Field(None, max_length=100, description="Modelo del dispositivo")
    version_app: Optional[str] = Field(None, max_length=20, description="Versión de la app")
    version_so: Optional[str] = Field(None, max_length=20, description="Versión del SO")

    @field_validator('plataforma')
    @classmethod
    def validar_plataforma(cls, v: str) -> str:
        if v.upper() not in ['A', 'I']:
            raise ValueError('plataforma debe ser A (Android) o I (iOS)')
        return v.upper()


class DispositivoRegistroToken(BaseModel):
    """Schema para registrar/actualizar token FCM"""
    token_fcm: str = Field(..., max_length=500, description="Token de Firebase Cloud Messaging")
    codigo_trabajador: str = Field(..., max_length=8, description="Código del trabajador")
    plataforma: str = Field(..., description="Plataforma: A=Android, I=iOS")
    modelo_dispositivo: Optional[str] = Field(None, max_length=100, description="Modelo del dispositivo")
    version_app: Optional[str] = Field(None, max_length=20, description="Versión de la app")
    version_so: Optional[str] = Field(None, max_length=20, description="Versión del SO")

    @field_validator('plataforma')
    @classmethod
    def validar_plataforma(cls, v: str) -> str:
        if v.upper() not in ['A', 'I']:
            raise ValueError('plataforma debe ser A (Android) o I (iOS)')
        return v.upper()


class DispositivoRegistroResponse(BaseModel):
    """Schema para respuesta de registro de token"""
    mensaje: str
    id_dispositivo: int


class ConfigFlujoCreate(BaseModel):
    """Schema para crear una configuración de flujo"""
    tipo_solicitud: str = Field(..., description="V=Vacaciones, P=Permiso")
    codigo_permiso: Optional[str] = Field(None, max_length=10, description="Código de permiso específico")
    codigo_area: Optional[str] = Field(None, max_length=4, description="Código de área")
    codigo_seccion: Optional[str] = Field(None, max_length=4, description="Código de sección")
    codigo_cargo: Optional[str] = Field(None, max_length=4, description="Código de cargo")
    dias_desde: Optional[int] = Field(None, description="Mínimo de días")
    dias_hasta: Optional[int] = Field(None, description="Máximo de días")
    niveles_requeridos: int = Field(2, description="Cantidad de niveles de aprobación requeridos")
    orden: int = Field(1, description="Orden de evaluación")
    activo: str = Field('S', description="S=Activo, N=Inactivo")
    fecha_desde: date = Field(default_factory=date.today, description="Fecha desde")
    fecha_hasta: Optional[date] = Field(None, description="Fecha hasta")
    descripcion: Optional[str] = Field(None, max_length=200, description="Descripción de la regla")


class JerarquiaCreate(BaseModel):
    """Schema para crear una jerarquía de aprobación"""
    codigo_area: Optional[str] = Field(None, max_length=4, description="Código de área")
    codigo_seccion: Optional[str] = Field(None, max_length=4, description="Código de sección")
    codigo_cargo: Optional[str] = Field(None, max_length=4, description="Código de cargo")
    codigo_trabajador_aprobador: str = Field(..., max_length=8, description="Código del aprobador")
    tipo_relacion: str = Field(..., description="J=Jefe, G=Gerente, D=Director")
    nivel_jerarquico: int = Field(..., description="Nivel jerárquico (1, 2, 3...)")
    activo: str = Field('S', description="S=Activo, N=Inactivo")
    fecha_desde: date = Field(default_factory=date.today, description="Fecha desde")
    fecha_hasta: Optional[date] = Field(None, description="Fecha hasta")
    descripcion: Optional[str] = Field(None, max_length=200, description="Descripción")


# ============================================
# SCHEMAS DE ACTUALIZACIÓN
# ============================================

class SolicitudUpdate(BaseModel):
    """Schema para actualizar una solicitud (solo pendientes)"""
    fecha_inicio: Optional[date] = Field(None, description="Fecha inicio")
    fecha_fin: Optional[date] = Field(None, description="Fecha fin")
    observacion: Optional[str] = Field(None, max_length=500, description="Observaciones")
    motivo: Optional[str] = Field(None, max_length=2, description="Código de motivo")


class SolicitudAnular(BaseModel):
    """Schema para anular una solicitud"""
    motivo_anulacion: str = Field(..., max_length=200, description="Motivo de la anulación")


class AprobacionUpdate(BaseModel):
    """Schema para actualizar una aprobación"""
    observacion: Optional[str] = Field(None, max_length=500, description="Comentarios")
    ip_dispositivo: Optional[str] = Field(None, max_length=50, description="IP del dispositivo")


# ============================================
# SCHEMAS DE LECTURA
# ============================================

class AprobacionRead(BaseModel):
    """Schema para leer una aprobación"""
    id_aprobacion: int
    id_solicitud: int
    nivel: int
    codigo_trabajador_aprueba: str
    estado: str
    observacion: Optional[str]
    fecha: Optional[datetime]
    usuario: Optional[str]
    ip_dispositivo: Optional[str]
    fecha_notificado: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SolicitudRead(BaseModel):
    """Schema básico para leer una solicitud"""
    id_solicitud: int
    tipo_solicitud: str
    codigo_permiso: Optional[str]
    codigo_trabajador: str
    fecha_inicio: date
    fecha_fin: date
    dias_solicitados: Optional[Decimal]
    observacion: Optional[str]
    motivo: Optional[str]
    estado: str
    fecha_registro: datetime
    usuario_registro: Optional[str]
    fecha_modificacion: Optional[datetime]
    usuario_modificacion: Optional[str]
    fecha_anulacion: Optional[datetime]
    usuario_anulacion: Optional[str]
    motivo_anulacion: Optional[str]
    sregdi: Optional[str]
    fecha_registro_planilla: Optional[datetime]
    descripcion_permiso: Optional[str] = Field(None, description="Descripción del tipo de permiso")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
            Decimal: lambda v: float(v) if v else None
        }


class SolicitudReadFull(SolicitudRead):
    """Schema completo con aprobaciones y detalles adicionales"""
    aprobaciones: List[AprobacionRead] = Field(default_factory=list, description="Lista de aprobaciones")
    nombre_trabajador: Optional[str] = Field(None, description="Nombre completo del trabajador")
    descripcion_permiso: Optional[str] = Field(None, description="Descripción del tipo de permiso")


class NotificacionRead(BaseModel):
    """Schema para leer una notificación"""
    id_notificacion: int
    codigo_trabajador: str
    id_solicitud: int
    tipo_notificacion: str
    titulo: str
    mensaje: str
    leido: str
    fecha_creacion: datetime
    fecha_leido: Optional[datetime]
    accion_url: Optional[str]
    prioridad: Optional[str]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ConfigFlujoRead(BaseModel):
    """Schema para leer una configuración de flujo"""
    id_config: int
    tipo_solicitud: str
    codigo_permiso: Optional[str]
    codigo_area: Optional[str]
    codigo_seccion: Optional[str]
    codigo_cargo: Optional[str]
    dias_desde: Optional[int]
    dias_hasta: Optional[int]
    niveles_requeridos: int
    orden: int
    activo: str
    fecha_desde: date
    fecha_hasta: Optional[date]
    usuario_registro: Optional[str]
    fecha_registro: datetime
    descripcion: Optional[str]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None
        }


class JerarquiaRead(BaseModel):
    """Schema para leer una jerarquía"""
    id_jerarquia: int
    codigo_area: Optional[str]
    codigo_seccion: Optional[str]
    codigo_cargo: Optional[str]
    codigo_trabajador_aprobador: str
    tipo_relacion: str
    nivel_jerarquico: int
    activo: str
    fecha_desde: date
    fecha_hasta: Optional[date]
    usuario_registro: Optional[str]
    fecha_registro: datetime
    descripcion: Optional[str]
    nombre_aprobador: Optional[str] = Field(None, description="Nombre del aprobador")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None
        }


class SustitutoRead(BaseModel):
    """Schema para leer un sustituto"""
    id_sustituto: int
    codigo_trabajador_titular: str
    codigo_trabajador_sustituto: str
    fecha_desde: date
    fecha_hasta: date
    motivo: Optional[str]
    observacion: Optional[str]
    activo: str
    usuario_registro: Optional[str]
    fecha_registro: datetime
    nombre_titular: Optional[str] = Field(None, description="Nombre del titular")
    nombre_sustituto: Optional[str] = Field(None, description="Nombre del sustituto")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None
        }


class DispositivoRead(BaseModel):
    """Schema para leer un dispositivo"""
    id_dispositivo: int
    codigo_trabajador: str
    token_fcm: str
    plataforma: str
    modelo_dispositivo: Optional[str]
    version_app: Optional[str]
    version_so: Optional[str]
    fecha_registro: datetime
    fecha_ultimo_acceso: Optional[datetime]
    activo: str
    notif_nuevas: Optional[str]
    notif_aprobadas: Optional[str]
    notif_rechazadas: Optional[str]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SaldoVacacionesRead(BaseModel):
    """Schema para leer el saldo de vacaciones"""
    codigo_trabajador: str
    dias_asignados_totales: Decimal
    dias_usados: Decimal
    dias_pendientes: Decimal
    saldo_disponible: Decimal
    nombre_trabajador: Optional[str] = Field(None, description="Nombre del trabajador")

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v else None
        }


# ============================================
# SCHEMAS DE RESPUESTA Y PAGINACIÓN
# ============================================

class PaginatedSolicitudResponse(BaseModel):
    """Schema para respuesta paginada de solicitudes"""
    items: List[SolicitudRead]
    total: int
    page: int
    limit: int
    pages: int


class PaginatedNotificacionResponse(BaseModel):
    """Schema para respuesta paginada de notificaciones"""
    items: List[NotificacionRead]
    total: int
    page: int
    limit: int
    pages: int
    no_leidas: int = Field(0, description="Cantidad de notificaciones no leídas")


class CatalogoItem(BaseModel):
    """Schema para items de catálogos"""
    codigo: str
    descripcion: str


class CatalogosResponse(BaseModel):
    """Schema para respuesta de catálogos"""
    areas: List[CatalogoItem]
    secciones: List[CatalogoItem]
    cargos: List[CatalogoItem]
    tipos_permiso: List[CatalogoItem]


class AprobacionResponse(BaseModel):
    """Schema para respuesta de aprobación/rechazo"""
    message: str
    id_solicitud: int
    id_aprobacion: int
    nivel: int
    estado: str
    solicitud_completa: bool = Field(False, description="Indica si la solicitud está completamente aprobada")


class EstadisticasResponse(BaseModel):
    """Schema para estadísticas del dashboard"""
    total_solicitudes: int
    solicitudes_pendientes: int
    solicitudes_aprobadas: int
    solicitudes_rechazadas: int
    solicitudes_por_tipo: dict
    solicitudes_por_mes: List[dict]


class TrabajadorRead(BaseModel):
    """Schema para leer información de trabajador"""
    codigo_trabajador: str
    nombre_completo: str
    codigo_area: Optional[str]
    codigo_seccion: Optional[str]
    codigo_cargo: Optional[str]
    descripcion_area: Optional[str] = Field(None, description="Descripción del área")
    descripcion_seccion: Optional[str] = Field(None, description="Descripción de la sección")
    descripcion_cargo: Optional[str] = Field(None, description="Descripción del cargo")
    dni: Optional[str]
    fecha_nacimiento: Optional[date] = Field(None, description="Fecha de nacimiento")
    fecha_ingreso: Optional[date] = Field(None, description="Fecha de ingreso")
    fecha_fin_contrato: Optional[date] = Field(None, description="Fecha de fin de contrato")

    class Config:
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat() if v else None
        }


class PaginatedTrabajadorResponse(BaseModel):
    """Schema para respuesta paginada de trabajadores"""
    items: List[TrabajadorRead]
    total: int
    page: int
    limit: int
    pages: int


# ============================================
# SCHEMAS PARA BOLETAS Y CERTIFICADOS CTS
# ============================================

class BoletaPagoResponse(BaseModel):
    """Schema para un ítem de boleta de pago"""
    codigo_trabajador: str = Field(..., description="Código del trabajador")
    anio: str = Field(..., description="Año de la boleta")
    mes: str = Field(..., description="Mes de la boleta")
    nseman: Optional[str] = Field(None, description="Número de semana (nseman)")
    semana: Optional[int] = Field(None, description="Número de semana dentro del mes (1, 2, 3...)")
    archivo_pdf_base64: str = Field(..., description="Archivo PDF en formato base64")
    nombre_archivo: str = Field(..., description="Nombre sugerido para el archivo")
    
    class Config:
        from_attributes = True


class BoletasPagoResponse(BaseModel):
    """Schema para respuesta de lista de boletas de pago (año completo o un mes)"""
    items: List[BoletaPagoResponse] = Field(..., description="Lista de boletas de pago")


class CertificadoCTSResponse(BaseModel):
    """Schema para un ítem de certificado CTS"""
    codigo_trabajador: str = Field(..., description="Código del trabajador")
    anio: str = Field(..., description="Año del certificado")
    mes: Optional[str] = Field(None, description="Mes del certificado (ej. 05, 11)")
    nseman: Optional[str] = Field(None, description="Número de semana (nseman)")
    archivo_pdf_base64: str = Field(..., description="Archivo PDF en formato base64")
    nombre_archivo: str = Field(..., description="Nombre sugerido para el archivo")
    
    class Config:
        from_attributes = True


class CertificadosCTSResponse(BaseModel):
    """Schema para respuesta de lista de certificados CTS (normalmente 2 por año)"""
    items: List[CertificadoCTSResponse] = Field(..., description="Lista de certificados CTS del año")
