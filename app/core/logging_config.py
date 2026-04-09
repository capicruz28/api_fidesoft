import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    """Configura el logging global de la aplicación"""
    # Crear el directorio logs si no existe
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # En Windows, la consola suele usar cp1252 y falla con emojis/Unicode.
    # Forzamos UTF-8 (y fallback seguro) para evitar UnicodeEncodeError.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except Exception:
                # Si el stream no permite reconfigurar, seguimos con el default.
                pass

    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=1024*1024,  # 1MB
        backupCount=5,
        encoding="utf-8",
        errors="backslashreplace",
    )

    console_handler = logging.StreamHandler(sys.stdout)

    # Configuración básica del logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Handler para archivo rotativo
            file_handler,
            # Handler para consola
            console_handler
        ]
    )

def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado para el módulo especificado

    Args:
        name: Nombre del módulo (generalmente __name__)

    Returns:
        logging.Logger: Logger configurado
    """
    return logging.getLogger(name)