"""
Definición de clases y costantes auxiliares (estados, errores, etc)
"""
from dataclasses import dataclass, fields
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


@dataclass
class BaseTabla:
    """
    Esta clase se usa para almacenar los datos que se van a emplear en algunas tablas que se muestran en la
    app.

    max_len es un diccionario que contiene la longitud máxima del valor los atributos:
        la clave es el nombre del atributo (ruta y longitud en este caso)
        el valor es la longitud máxima del valor del atributo (es un literal) siendo el mínimo la longitud
        del nombre del atributo (4 y 9 en este caso)
    Este diccionario se usa para calcular las dimensiones de la tabla que se muestra en la selección de la
    unidad a grabar la clave maestra.
    El método _campos_requeridos debe ser sobreescrito para que la clase funcione.
    """

    codigo: str = ''

    def __post_init__(self):
        clase = type(self)
        if all(getattr(self, c) for c in self._campos_especificios()):
            clase.instancias += 1  # instancias de la subclase, no de la base
            self.codigo = str(clase.instancias)
            for campo in fields(self):
                valor = getattr(self, campo.name)
                clase.max_len[campo.name] = max(clase.max_len.get(campo.name, len(campo.name)), len(valor))

    @classmethod
    def reset(cls):
        """
        Reinicia los atributos de clase.
        """

        cls.instancias = 0
        cls.max_len = {}

    def _campos_especificios(self) -> list:
        """
        Cada subclase debe sobreescribir este método y definir qué campos deben tener valor.
        """

        raise NotImplementedError


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
