from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class ClienteModel(BaseModel):
    cliente_id: int
    razon_social: str
    ruc: str
    representante: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[EmailStr] = None
    logo_url: Optional[str] = None
    es_activo: bool = True
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
    es_eliminado: bool = False

    class Config:
        from_attributes = True

