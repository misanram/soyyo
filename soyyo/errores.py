"""
Definición de errores
"""


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


class CapturaError(ErrorApp):
    """
    Error durante la captura de imagen
    """

    def __init__(self, mensaje, area=None, causa=None):
        super().__init__(mensaje)
        self.area = area
        self.causa = causa  # excepción original
