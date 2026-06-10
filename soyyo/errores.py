"""
Definición de errores
"""


class AppError(Exception):
    """
    Error de la aplicación
    """

    pass


class PepperNotFoundError(AppError):
    """
    get_password no devuelve el pepper
    """

    pass


class FirmaInvalidaError(AppError):
    """
    La firma del fichero no es válida. El fichero ha sido manipulado.
    """


class CapturaError(AppError):
    """
    Error durante la captura de imagen
    """

    def __init__(self, mensaje, area=None, causa=None):
        super().__init__(mensaje)
        self.area = area
        self.causa = causa  # excepción original


class SinRutaLlaveError(AppError):
    """
    No hay ruta para guardar el fichero llave
    """

    pass
