# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List, Literal
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

class Settings(BaseSettings):
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Service API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API FastAPI para Service"

    # Database Principal
    DB_SERVER: str = os.getenv("DB_SERVER", "")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_DATABASE: str = os.getenv("DB_DATABASE", "")
    DB_PORT: int = int(os.getenv("DB_PORT", "1433"))

    # Database Administración
    DB_ADMIN_SERVER: str = os.getenv("DB_ADMIN_SERVER", "")
    DB_ADMIN_USER: str = os.getenv("DB_ADMIN_USER", "")
    DB_ADMIN_PASSWORD: str = os.getenv("DB_ADMIN_PASSWORD", "")
    DB_ADMIN_DATABASE: str = os.getenv("DB_ADMIN_DATABASE", "")
    DB_ADMIN_PORT: int = int(os.getenv("DB_ADMIN_PORT", "1433"))

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")

    # Environment
    ENVIRONMENT: Literal["development", "production"] = os.getenv("ENVIRONMENT", "development")

    # CORS - sin "*" cuando allow_credentials=True
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173",
        "https://api-service-cunb.onrender.com",
    ]

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Cookies
    REFRESH_COOKIE_NAME: str = "refresh_token"
    REFRESH_COOKIE_MAX_AGE: int = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # segundos

    @property
    def COOKIE_SECURE(self) -> bool:
        """
        Secure=True solo en producción (HTTPS)
        En desarrollo (HTTP) debe ser False
        """
        return self.ENVIRONMENT == "production"
    
    @property
    def COOKIE_SAMESITE(self) -> Literal["lax", "none", "strict"]:
        """
        SameSite='lax' funciona en desarrollo local (mismo dominio, diferentes puertos)
        Chrome/Edge bloquean SameSite='none' sin Secure=True (HTTPS)
        """
        return "lax"  # ✅ CORREGIDO: Usar "lax" en todos los entornos

    def get_database_url(self, is_admin: bool = False) -> str:
        """
        Construye y retorna la URL de conexión a la base de datos
        Args:
            is_admin: Si es True, devuelve la conexión de administración
        """
        if is_admin:
            return (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.DB_ADMIN_SERVER},{self.DB_ADMIN_PORT};"
                f"DATABASE={self.DB_ADMIN_DATABASE};"
                f"UID={self.DB_ADMIN_USER};"
                f"PWD={self.DB_ADMIN_PASSWORD};"
                "TrustServerCertificate=yes;"
            )
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.DB_SERVER},{self.DB_PORT};"
            f"DATABASE={self.DB_DATABASE};"
            f"UID={self.DB_USER};"
            f"PWD={self.DB_PASSWORD};"
            "TrustServerCertificate=yes;"
        )

    class Config:
        case_sensitive = True

    def validate_security_settings(self):
        """Valida que las configuraciones de seguridad estén presentes"""
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY no está configurada en las variables de entorno")
        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY debe tener al menos 32 caracteres")
        if not self.ALGORITHM:
            raise ValueError("ALGORITHM no está configurado")

# Instancia de configuración
settings = Settings()

# Validación al iniciar
try:
    settings.validate_security_settings()
except ValueError as e:
    import logging
    logging.error(f"Error de configuración: {e}")
    raise