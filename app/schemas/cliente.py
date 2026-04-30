"""
Esquemas Pydantic para la gestión de clientes y sus conexiones.

Este módulo define los esquemas para creación, actualización y lectura de clientes.
Incluye un schema de respuesta paginada para listados administrativos.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class ClienteBase(BaseModel):
    """
    Schema base para Cliente con validaciones de dominio.
    """

    razon_social: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Razón social del cliente",
        examples=["FideSoft S.A.C."]
    )
    ruc: str = Field(
        ...,
        min_length=8,
        max_length=20,
        description="RUC o documento tributario (único)",
        examples=["20123456789"]
    )
    representante: Optional[str] = Field(
        None,
        max_length=100,
        description="Nombre del representante legal o contacto principal"
    )
    direccion: Optional[str] = Field(
        None,
        max_length=255,
        description="Dirección fiscal o de contacto"
    )
    telefono: Optional[str] = Field(
        None,
        max_length=20,
        description="Teléfono de contacto"
    )
    correo: Optional[EmailStr] = Field(
        None,
        description="Correo de contacto"
    )
    logo_url: Optional[str] = Field(
        None,
        max_length=500,
        description="URL del logo del cliente"
    )
    es_activo: bool = Field(
        True,
        description="Indica si el cliente está activo"
    )

    @field_validator("razon_social")
    @classmethod
    def validar_razon_social(cls, valor: str) -> str:
        valor = (valor or "").strip()
        if not valor:
            raise ValueError("La razón social es requerida")
        return valor

    @field_validator("ruc")
    @classmethod
    def validar_ruc(cls, valor: str) -> str:
        valor = (valor or "").strip()
        if not valor:
            raise ValueError("El RUC es requerido")
        return valor


class ClienteCreate(ClienteBase):
    """Payload para creación de clientes."""


class ClienteUpdate(BaseModel):
    """
    Payload para actualización parcial de clientes.
    """

    razon_social: Optional[str] = Field(None, min_length=1, max_length=150)
    ruc: Optional[str] = Field(None, min_length=8, max_length=20)
    representante: Optional[str] = Field(None, max_length=100)
    direccion: Optional[str] = Field(None, max_length=255)
    telefono: Optional[str] = Field(None, max_length=20)
    correo: Optional[EmailStr] = Field(None)
    logo_url: Optional[str] = Field(None, max_length=500)
    es_activo: Optional[bool] = Field(None)

    _validar_razon_social = field_validator("razon_social")(ClienteBase.validar_razon_social.__func__)
    _validar_ruc = field_validator("ruc")(ClienteBase.validar_ruc.__func__)


class ClienteResponse(ClienteBase):
    """
    Respuesta para lectura de clientes.

    Nota: `conexiones` se incluye en el detalle del cliente.
    """

    cliente_id: int = Field(..., ge=1, description="Identificador único del cliente")
    fecha_creacion: datetime = Field(..., description="Fecha de creación del registro")
    fecha_actualizacion: Optional[datetime] = Field(None, description="Última fecha de actualización")
    es_eliminado: bool = Field(False, description="Borrado lógico del cliente")
    conexiones: List["ConexionResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ClienteListResponse(BaseModel):
    """
    Respuesta paginada para listados de clientes.
    """

    clientes: List[ClienteResponse]
    total_clientes: int
    pagina_actual: int
    total_paginas: int

    class Config:
        from_attributes = True


# Importación diferida para evitar ciclos
from app.schemas.cliente_conexion import ConexionResponse  # noqa: E402  (import al final)

# Resolver forward refs (Pydantic v2)
ClienteResponse.model_rebuild()

