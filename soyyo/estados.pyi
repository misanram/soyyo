from enum import Enum


class EstadoSistema(Enum):
    SIN_KEYRING: str
    PRIMER_ARRANQUE: str
    SIN_PEPPER: str
    FICHERO_CORRUPTO: str
    FIRMA_INVALIDA: str
    OK: str
    SALIENDO_OK: str
    SALIENDO_ERROR: str


class ErrorApp(Exception): ...
