from pathlib import Path
from typing import Any

from constantes import EstadoApp


def chek_keyring() -> bool: ...


def chek_almacen(data_path: Path) -> bool: ...


def comprobar_seguridad(data_path: Path) -> EstadoApp: ...


def obtener_pin(prompt_head: str, login: bool) -> bytearray: ...


def validar_pin(data_path: Path, pin: bytearray) -> bool: ...


def guarda_json(data_path: Path, datos: dict[Any, Any]) -> bool: ...


def _cargar_y_verificar_almacen(data_path: Path) -> dict: ...
