# app/db/connection.py
import pyodbc
from app.core.config import settings
from contextlib import contextmanager
import logging
from app.core.exceptions import DatabaseError
from enum import Enum

logger = logging.getLogger(__name__)

class DatabaseConnection(Enum):
    DEFAULT = "default"
    ADMIN = "admin"

def get_connection_string(connection_type: DatabaseConnection = DatabaseConnection.DEFAULT) -> str:
    """
    Obtiene la cadena de conexión según el tipo de conexión requerida.
    """
    if connection_type == DatabaseConnection.ADMIN:
        # Conexión para administración
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={settings.DB_ADMIN_SERVER},{settings.DB_ADMIN_PORT};"
            f"DATABASE={settings.DB_ADMIN_DATABASE};"
            f"UID={settings.DB_ADMIN_USER};"
            f"PWD={settings.DB_ADMIN_PASSWORD};"
            "TrustServerCertificate=yes;"
        )
    else:
        # Conexión default (la que ya tenías)
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={settings.DB_SERVER},{settings.DB_PORT};"
            f"DATABASE={settings.DB_DATABASE};"
            f"UID={settings.DB_USER};"
            f"PWD={settings.DB_PASSWORD};"
            "TrustServerCertificate=yes;"
        )

@contextmanager
def get_db_connection(connection_type: DatabaseConnection = DatabaseConnection.DEFAULT):
    """
    Context manager para obtener y cerrar una conexión a BD.
    Permite especificar el tipo de conexión requerida.
    """
    conn = None
    try:
        conn_str = get_connection_string(connection_type)
        conn = pyodbc.connect(conn_str)
        logger.debug(f"Conexión a BD ({connection_type.value}) establecida.")
        yield conn

    except pyodbc.Error as e:
        logger.error(f"Error de conexión a la base de datos ({connection_type.value}): {str(e)}")
        raise DatabaseError(detail=f"Error de conexión: {str(e)}")

    finally:
        if conn:
            conn.close()
            logger.debug(f"Conexión a BD ({connection_type.value}) cerrada.")