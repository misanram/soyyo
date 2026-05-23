from enum import Enum
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QMouseEvent, QPaintEvent
from PySide6.QtWidgets import QPushButton, QWidget

from soyyo.constantes import EstadoSistema


class VentanaCaptura(QWidget):
    _pantalla: QRect
    _clic_pos: QPoint | None
    _zona_activa: Enum | None
    _ancho_original: int
    _alto_original: int
    imagen: Image.Image | None
    _btn_capturar = QPushButton
    _btn_cancelar = QPushButton

    def __init__(self, ancho: int, alto: int) -> None: ...

    def _zona_actual(self, pos: QPoint | None) -> Enum: ...

    def _capturar(self) -> None: ...

    def mousePressEvent(self, event: QMouseEvent) -> None: ...

    def mouseMoveEvent(self, event: QMouseEvent) -> None: ...

    def mouseReleaseEvent(self, event: QMouseEvent) -> None: ...

    def paintEvent(self, event: QPaintEvent) -> None: ...


def reset(data_path: Path) -> EstadoSistema: ...


def setup(data_path: Path) -> EstadoSistema: ...


def captura() -> EstadoSistema: ...
