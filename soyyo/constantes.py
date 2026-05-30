"""
Definición de clases y costantes auxiliares (estados, errores, etc)
"""

from enum import Enum

from PySide6.QtCore import Qt


class EstadoApp(Enum):
    """
    Enumera los estados en los que puede encontrarse el sistema
    """

    SIN_KEYRING = 'Sin keyring'  # No hay keyring disponible
    PRIMER_ARRANQUE = 'Primer arranque'  # No hay fichero de datos
    SIN_PEPPER = 'Sin pepper'  # No hay pepper en el keyring
    FICHERO_CORRUPTO = 'Fichero corrupto'  # JSON inválido o ilegible
    FIRMA_INVALIDA = 'Firma invalida'  # El fichero ha sido manipulado
    INICIALIZACION_CORRECTA = 'Programa iniciado correctamente'
    SALIENDO_OK = 'Saliendo OK'  # El programa termina normalmente
    SALIENDO_ERROR = 'Saliendo con error'  # El porgrama termina en error

    def __str__(self):
        return self.value


class Zona(Enum):
    """
    Enumera las zonas que tiene una ventana de captura de QR
    """

    ESQUINA_SUPERIOR_IZQUIERDA = 'esquina_superior_izquierda'
    ESQUINA_SUPERIOR_DERECHA = 'esquina_superior_derecha'
    ESQUINA_INFERIOR_IZQUIERDA = 'esquina_inferior_izquierda'
    ESQUINA_INFERIOR_DERECHA = 'esquina_inferior_derecha'
    BORDE_SUPERIOR = 'borde_superior'
    BORDE_INFERIOR = 'borde_inferior'
    BORDE_IZQUIERDO = 'borde_izquierdo'
    BORDE_DERECHO = 'borde_derecho'
    BARRA = 'barra'
    INTERIOR = 'interior'


class ErrorApp(Exception):
    """
    Error de la aplicación
    """

    pass


class PepperNotFoundError(ErrorApp):
    """
    get_password no devuelve el pepper
    """

    pass


class FirmaInvalidaError(ErrorApp):
    """
    La firma del fichero no es válida. El fichero ha sido manipulado.
    """


class CapturaError(Exception):
    """
    Error durante la captura de imagen
    """

    def __init__(self, mensaje, area=None, causa=None):
        super().__init__(mensaje)
        self.area = area
        self.causa = causa  # excepción original


CURSORES = {Zona.BORDE_SUPERIOR: Qt.CursorShape.SizeVerCursor,
            Zona.BORDE_INFERIOR: Qt.CursorShape.SizeVerCursor,
            Zona.BORDE_IZQUIERDO: Qt.CursorShape.SizeHorCursor,
            Zona.BORDE_DERECHO: Qt.CursorShape.SizeHorCursor,
            Zona.ESQUINA_SUPERIOR_IZQUIERDA: Qt.CursorShape.SizeFDiagCursor,
            Zona.ESQUINA_INFERIOR_DERECHA: Qt.CursorShape.SizeFDiagCursor,
            Zona.ESQUINA_SUPERIOR_DERECHA: Qt.CursorShape.SizeBDiagCursor,
            Zona.ESQUINA_INFERIOR_IZQUIERDA: Qt.CursorShape.SizeBDiagCursor,
            Zona.BARRA: Qt.CursorShape.SizeAllCursor, Zona.INTERIOR: Qt.CursorShape.ArrowCursor, }

TIEMPO_DE_BLOQUEO = {0: 0, 1: 1, 2: 5, 3: 15, 4: 30, 5: 60, 6: 4 * 60, 7: 12 * 60, 8: 24 * 60, 9: 48 * 60}
