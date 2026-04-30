from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ClienteConexionModel(BaseModel):
    conexion_id: int
    cliente_id: int
    aplicacion_id: int
    nombre: str
    entorno: str
    base_url: str
    descripcion: Optional[str] = None
    es_principal: bool = False
    es_activo: bool = True
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None

    class Config:
        from_attributes = True

