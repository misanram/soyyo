class AppError(Exception): ...


class PepperNotFoundError(AppError): ...


class FirmaInvalidaError(AppError): ...


class CapturaError(AppError):
    area: tuple | None
    error: Exception | None

    def __init__(self, mensaje: str, area: tuple | None, causa: Exception | None) -> None: ...


class SinRutaLlaveError(AppError): ...
