from pathlib import Path
from typing import Any

from soyyo.constantes import EstadoApp


def check_keyring() -> bool: ...


def check_almacen(data_path: Path) -> bool: ...


def comprobar_seguridad(data_path: Path) -> EstadoApp: ...


def obtener_pin(prompt_head: str, login: bool) -> bytearray: ...


def validar_pin(data_path: Path, pin: bytearray) -> bool: ...


def guardar_json(data_path: Path, datos: dict[Any, Any]) -> None: ...


def cargar_y_verificar_almacen(data_path: Path) -> dict: ...


def autorizame(data_path: Path) -> tuple: ...
