from enum import Enum

from PySide6.QtCore import Qt


class EstadoSistema(Enum):
    SIN_KEYRING: str
    PRIMER_ARRANQUE: str
    SIN_PEPPER: str
    FICHERO_CORRUPTO: str
    FIRMA_INVALIDA: str
    OK: str
    SALIENDO_OK: str
    SALIENDO_ERROR: str

    def __str__(self) -> str: ...


CURSORES: dict[str, Qt.CursorShape]


class Zona(Enum):
    ESQUINA_SUPERIOR_IZQUIERDA: str
    ESQUINA_SUPERIOR_DERECHA: str
    ESQUINA_INFERIOR_IZQUIERDA: str
    ESQUINA_INFERIOR_DERECHA: str
    BORDE_SUPERIOR: str
    BORDE_INFERIOR: str
    BORDE_IZQUIERDO: str
    BORDE_DERECHO: str
    BARRA: str
    INTERIOR: str


class ErrorApp(Exception): ...
