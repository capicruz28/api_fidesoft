"""
Esquemas Pydantic para la gestión de aplicaciones.

Define los payloads de creación/actualización y el schema de respuesta para
la entidad Aplicación.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AplicacionBase(BaseModel):
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Nombre de la aplicación",
        examples=["Mobile", "Web", "Desktop"]
    )
    codigo: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Código único de la aplicación",
        examples=["MOB", "WEB"]
    )
    descripcion: Optional[str] = Field(
        None,
        max_length=255,
        description="Descripción opcional"
    )
    es_activo: bool = Field(True, description="Indica si la aplicación está activa")

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        valor = (valor or "").strip()
        if not valor:
            raise ValueError("El nombre es requerido")
        return valor

    @field_validator("codigo")
    @classmethod
    def validar_codigo(cls, valor: str) -> str:
        valor = (valor or "").strip()
        if not valor:
            raise ValueError("El código es requerido")
        return valor


class AplicacionCreate(AplicacionBase):
    """Payload para crear aplicaciones."""


class AplicacionUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=50)
    codigo: Optional[str] = Field(None, min_length=1, max_length=20)
    descripcion: Optional[str] = Field(None, max_length=255)
    es_activo: Optional[bool] = Field(None)

    _validar_nombre = field_validator("nombre")(AplicacionBase.validar_nombre.__func__)
    _validar_codigo = field_validator("codigo")(AplicacionBase.validar_codigo.__func__)


class AplicacionResponse(AplicacionBase):
    aplicacion_id: int = Field(..., ge=1, description="Identificador único de la aplicación")
    fecha_creacion: datetime = Field(..., description="Fecha de creación del registro")

    class Config:
        from_attributes = True

