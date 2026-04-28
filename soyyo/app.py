"""
Módulo prinicpal
"""

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from soyyo.acciones import reset, setup
from soyyo.auxiliares import (chek_almacen, chek_integrity_json, chek_keyring, chek_pepper)
from soyyo.estados import EstadoSistema
from soyyo.mensajes import MSG_FICHERO_CORRUPTO, MSG_FIRMA_INVALIDA, MSG_SIN_KEYRING

log = logging.getLogger(__name__)
file_handler = RotatingFileHandler('soyyo.log', maxBytes=1_000_000, backupCount=5)
logging.basicConfig(level=logging.WARNING,
                    handlers=[file_handler],
                    force=True,
                    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
                    )
log.setLevel(logging.DEBUG)


def get_options():
    """
    Lee las opciones con las que se arranca el programa.
    """

    parser = argparse.ArgumentParser(prog='soyyo', usage='%(prog)s [opción]',
                                     description='Programa para hacer TOTP', epilog='', )
    grupo = parser.add_mutually_exclusive_group()
    # grupo.add_argument('--setup', action='store_true', help='Configuración del programa.')
    grupo.add_argument('--reset', action='store_true', help='Reinicia el programa a su estado de fábrica.')
    args = parser.parse_args()
    return args


class Aplicacion:
    """
    Clase principal del programa
    """

    def __init__(self):
        root_path = Path(sys.prefix)
        bin_path = Path(sys.executable).parent
        self.app_executable = bin_path / 'soyyo'
        self.data_path = root_path / 'soyyo_data.json'
        self.args = get_options()

    def _comprueba_estado(self):
        if not chek_keyring():
            return EstadoSistema.SIN_KEYRING
        if not chek_almacen(self.data_path):
            return EstadoSistema.PRIMER_ARRANQUE
        if not chek_pepper():
            return EstadoSistema.SIN_PEPPER
        return chek_integrity_json(self.data_path)

    def run(self):
        """
        Inicia el programa
        """

        estado = self._comprueba_estado()
        log.debug(estado)

        if self.args.reset and estado not in (EstadoSistema.SIN_KEYRING, EstadoSistema.PRIMER_ARRANQUE):
            estado = reset(self.data_path)

        while True:
            if estado == EstadoSistema.SIN_KEYRING:
                print(MSG_SIN_KEYRING)
                sys.exit(1)

            elif estado == EstadoSistema.PRIMER_ARRANQUE:
                estado = setup(self.data_path)

            elif estado == EstadoSistema.FICHERO_CORRUPTO:
                print(MSG_FICHERO_CORRUPTO)
                sys.exit(1)

            elif estado == EstadoSistema.FIRMA_INVALIDA:
                print(MSG_FIRMA_INVALIDA)
                sys.exit(1)

            elif estado == EstadoSistema.OK:
                print(not all(vars(self.args).values()))
                break


def main():
    """
    Arranca el programa
    """

    aplicacion = Aplicacion()
    aplicacion.run()


if __name__ == '__main__':  # pragma: no cover
    main()
