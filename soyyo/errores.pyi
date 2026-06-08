class ErrorApp(Exception): ...


class PepperNotFoundError(ErrorApp): ...


class FirmaInvalidaError(ErrorApp): ...


class CapturaError(ErrorApp):
    area: tuple | None
    error: Exception | None

    def __init__(self, mensaje: str, area: tuple | None, causa: Exception | None) -> None: ...
