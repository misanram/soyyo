import argparse
from pathlib import Path


def get_options() -> argparse.Namespace: ...


class Aplicacion:
    data_path: Path
    args: argparse.Namespace

    def __init__(self, args: argparse.Namespace) -> None: ...

    def _comprueba_estado(self) -> str: ...

    def run(self) -> None: ...


def main() -> None: ...
