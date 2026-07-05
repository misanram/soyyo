import argparse
from pathlib import Path


def configurar_locale() -> None: ...


def configurar_logging() -> None: ...


def configurar_i18n() -> None: ...


def configura_argparser() -> argparse.Namespace: ...


class Aplicacion:
    data_path: Path
    args: argparse.Namespace

    def __init__(self, args: argparse.Namespace) -> None: ...

    def _comprobar_estado(self) -> str: ...

    def run(self) -> None: ...


def main() -> None: ...
