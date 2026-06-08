from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class Usable:
    codigo: str
    ruta: str
    capacidad: str

    def _campos_requeridos(self) -> list: ...


def reintentar_keyring(intentos: int, espera: float) -> Callable: ...


def check_keyring() -> bool: ...


def check_almacen(data_path: Path) -> bool: ...


def obtener_pin(prompt_head: str, setup: bool) -> bytearray: ...


def validar_pin(data_path: Path, pin: bytearray) -> bool: ...


def guardar_json(data_path: Path, datos: dict[Any, Any]) -> None: ...


def cargar_y_verificar_almacen(data_path: Path) -> dict: ...


def autorizame(data_path: Path) -> tuple: ...


def muestra_tabla(lista_datos: list) -> None: ...
