import tkinter as tk
from pathlib import Path
from tkinter import ttk

from soyyo.estados import EstadoSistema


class VentanaCaptura(ttk.Frame):
    s: ttk.Style
    canvas: ttk.Frame
    etiqueta = bytes
    uri = str

    def __init__(self, master: tk.Tk) -> None: ...

    def trasparencia(self) -> None: ...

    def _cerrar(self) -> None: ...

    def _capturar(self) -> None: ...

    def _crearWidgets(self) -> None: ...


def reset(data_path: Path) -> EstadoSistema: ...


def setup(data_path: Path) -> EstadoSistema: ...


def captura(data_path: Path) -> EstadoSistema: ...
