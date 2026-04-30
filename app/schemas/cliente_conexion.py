"""
Esquemas Pydantic para la gestión de conexiones por cliente.

Incluye schemas de administración (CRUD) y un schema público reducido para
consumo por apps móviles/desktop.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ConexionBase(BaseModel):
    aplicacion_id: int = Field(..., ge=1, description="ID de la aplicación asociada")
    nombre: str = Field(..., min_length=1, max_length=100, description="Nombre de la conexión")
    entorno: str = Field(
        "produccion",
        min_length=1,
        max_length=20,
        description="Entorno de la conexión (ej: produccion, qa, dev)"
    )
    base_url: str = Field(..., min_length=1, max_length=500, description="Base URL del servicio")
    descripcion: Optional[str] = Field(None, max_length=255, description="Descripción opcional")
    es_principal: bool = Field(False, description="Indica si es la conexión principal del cliente/app")
    es_activo: bool = Field(True, description="Indica si la conexión está activa")

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        valor = (valor or "").strip()
        if not valor:
            raise ValueError("El nombre de la conexión es requerido")
        return valor

    @field_validator("entorno")
    @classmethod
    def validar_entorno(cls, valor: str) -> str:
        valor = (valor or "").strip()
        if not valor:
            raise ValueError("El entorno es requerido")
        return valor

    @field_validator("base_url")
    @classmethod
    def validar_base_url(cls, valor: str) -> str:
        valor = (valor or "").strip()
        if not valor:
            raise ValueError("La base_url es requerida")
        return valor


class ConexionCreate(ConexionBase):
    """Payload para crear conexiones (admin)."""


class ConexionUpdate(BaseModel):
    aplicacion_id: Optional[int] = Field(None, ge=1)
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    entorno: Optional[str] = Field(None, min_length=1, max_length=20)
    base_url: Optional[str] = Field(None, min_length=1, max_length=500)
    descripcion: Optional[str] = Field(None, max_length=255)
    es_principal: Optional[bool] = Field(None)
    es_activo: Optional[bool] = Field(None)

    _validar_nombre = field_validator("nombre")(ConexionBase.validar_nombre.__func__)
    _validar_entorno = field_validator("entorno")(ConexionBase.validar_entorno.__func__)
    _validar_base_url = field_validator("base_url")(ConexionBase.validar_base_url.__func__)


class ConexionResponse(BaseModel):
    conexion_id: int
    cliente_id: int
    aplicacion_id: int
    aplicacion_codigo: Optional[str] = Field(None, description="Código de la aplicación (cuando se usa JOIN)")
    nombre: str
    entorno: str
    base_url: str
    descripcion: Optional[str] = None
    es_principal: bool
    es_activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConexionPublicaResponse(BaseModel):
    """
    Schema público reducido para consumo por apps.
    """

    nombre: str
    entorno: str
    base_url: str
    es_principal: bool
    aplicacion_codigo: str

    class Config:
        from_attributes = True

