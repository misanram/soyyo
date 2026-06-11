from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, ClassVar

from .constantes import BaseTabla


@dataclass
class Usable(BaseTabla):
    max_len: ClassVar[dict]
    instancias: ClassVar[int]
    ruta: str
    capacidad: str

    def _campos_especificios(self) -> list: ...


def reintentar_keyring(intentos: int, espera: float) -> Callable: ...


def check_sistema() -> bool: ...


def check_keyring() -> bool: ...


def check_almacen(data_path: Path) -> bool: ...


def captura_teclado(prompt: str = ...,
                    una_tecla: bool = ...,
                    setup: bool = ...,
                    pin: bool = ...,
                    dispara: str = ...) -> bytearray: ...


def validar_pin(data_path: Path, pin: bytearray) -> bool: ...


def guardar_json(data_path: Path, datos: dict[Any, Any]) -> None: ...


def cargar_y_verificar_almacen(data_path: Path) -> dict: ...


def autorizame(data_path: Path) -> tuple: ...


def detectar_usb() -> list[Usable]: ...


def muestra_tabla(lista_datos: list, primer_elemento: int | None = ..., ultimo_elemento: int | None = ...) \
        -> None: ...


def selecciona_ruta() -> str: ...
