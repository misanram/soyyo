from enum import Enum


class EstadoSistema(Enum):
    SIN_KEYRING = 'sin_keyring'
    PRIMER_ARRANQUE = 'primer_arranque'
    SIN_PEPPER = 'sin_pepper'
    FICHERO_CORRUPTO = 'fichero_corrupto'
    FIRMA_INVALIDA = 'firma_invalida'
    OK = 'ok'
    SALIENDO_OK = 'saliendo_ok'
    SALIENDO_ERROR = 'saliendo_error'


class ErrorApp(Exception): ...
