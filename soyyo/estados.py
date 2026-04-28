"""
Definición de clases auxiliares (estados, errores, etc)
"""

from enum import Enum


class EstadoSistema(Enum):
    """
    Define los estados en los que puede encontrrse el sistema
    """
    SIN_KEYRING = 'sin_keyring'  # No hay keyring disponible
    PRIMER_ARRANQUE = 'primer_arranque'  # No hay fichero de datos
    SIN_PEPPER = 'sin_pepper'  # No hay pepper en el keyring
    FICHERO_CORRUPTO = 'fichero_corrupto'  # JSON inválido o ilegible
    FIRMA_INVALIDA = 'firma_invalida'  # El fichero ha sido manipulado
    OK = 'ok'  # Todo correcto


class ErrorApp(Exception):
    """
    Error de la aplicación
    """
    pass
