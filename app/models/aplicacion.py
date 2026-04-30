from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AplicacionModel(BaseModel):
    aplicacion_id: int
    nombre: str
    codigo: str
    descripcion: Optional[str] = None
    es_activo: bool = True
    fecha_creacion: datetime

    class Config:
        from_attributes = True

