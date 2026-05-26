"""
Módulo prinicpal
"""

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from soyyo.acciones import autorizar, captura, reset, setup
from soyyo.auxiliares import chek_almacen, chek_keyring, comprobar_seguridad
from soyyo.constantes import EstadoApp
from soyyo.mensajes import (MSG_FICHERO_CORRUPTO, MSG_FIRMA_INVALIDA, MSG_SALIENDO_ERROR, MSG_SALIENDO_OK,
                            MSG_SIN_KEYRING, MSG_SIN_PEPPER, )

log = logging.getLogger(__name__)
file_handler = RotatingFileHandler('soyyo.log', maxBytes=1_000_000, backupCount=5)
logging.basicConfig(level=logging.WARNING,
                    handlers=[file_handler],
                    force=True,
                    format='%(asctime)s %(levelname)-5.5s [%(name)s:%(lineno)s][%(threadName)s] %(message)s')
logging.getLogger('soyyo').setLevel(logging.DEBUG)


def get_options():
    """
    Lee las opciones con las que se arranca el programa.
    """

    parser = argparse.ArgumentParser(prog='soyyo',
                                     usage='%(prog)s [opción]',
                                     description='Programa para hacer TOTP',
                                     epilog='', )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument('--reset', action='store_true', help='Reinicia el programa a su estado de fábrica.')
    grupo.add_argument('--captura', action='store_true', help='Captura un QR.')
    args = parser.parse_args()
    return args


class Aplicacion:
    """
    Clase principal del programa
    """

    def __init__(self, args):
        root_path = Path(sys.prefix)
        # bin_path = Path(sys.executable).parent
        # self.app_executable = bin_path / 'soyyo'
        self.data_path = root_path / 'soyyo_data.json'
        self.args = args

    def _comprobar_estado(self):
        """
           Determina el estado inicial del sistema mediante comprobaciones secuenciales.
           El orden es estricto: cada comprobación asume que las anteriores han pasado.

           Secuencia:
               1. Keyring del sistema operativo (requisito de plataforma)
               2. Existencia del almacén (distingue primer arranque de ejecución normal)
               3. comprobar_seguridad: Esta función comprueba atómicamente almacen, pepper y firma

           Devuelve:
               Estados: uno de los siguientes valores:
                   - INICIALIZACION_CORRECTA → todo en orden
                   - PRIMER_ARRANQUE → no hay almacén (primera ejecución o datos perdidos)
                   - SIN_KEYRING → el SO no tiene keyring; el programa no puede funcionar
                   - SIN_PEPPER → almacén presente, pero pepper ausente; datos irrecuperables
                   - FICHERO_CORRUPTO → JSON inválido o error de lectura
                   - FIRMA_INVALIDA → JSON válido, pero la firma no coincide

           Nota:
               PRIMER_ARRANQUE cubre dos casos: 1) primera ejecución de la app y 2) pérdida accidental
               del almacén. La interfaz debe informar al usuario de esta ambigüedad.
           """

        if not chek_keyring():
            return EstadoApp.SIN_KEYRING
        elif not chek_almacen(self.data_path):
            return EstadoApp.PRIMER_ARRANQUE
        else:
            return comprobar_seguridad(self.data_path)

    def run(self):
        """
        Inicia el programa
        """

        estado = self._comprobar_estado()
        log.debug(f'Estado inicial: {estado}')

        if self.args.reset and estado not in (EstadoApp.SIN_KEYRING,):
            estado = reset(self.data_path)
            log.debug(estado)

        while True:
            if estado == EstadoApp.SIN_KEYRING:
                print(MSG_SIN_KEYRING)
                sys.exit(1)

            elif estado == EstadoApp.SIN_PEPPER:
                print(MSG_SIN_PEPPER)
                sys.exit(1)

            elif estado == EstadoApp.FICHERO_CORRUPTO:
                print(MSG_FICHERO_CORRUPTO)
                sys.exit(1)

            elif estado == EstadoApp.FIRMA_INVALIDA:
                print(MSG_FIRMA_INVALIDA)
                sys.exit(1)

            elif estado == EstadoApp.SALIENDO_ERROR:
                print(MSG_SALIENDO_ERROR)
                sys.exit(1)

            elif estado == EstadoApp.SALIENDO_OK:
                print(MSG_SALIENDO_OK)
                sys.exit(0)

            elif estado == EstadoApp.PRIMER_ARRANQUE:
                estado = setup(self.data_path)

            elif estado == EstadoApp.INICIALIZACION_CORRECTA:
                estado = autorizar(self.data_path)

            elif estado == EstadoApp.AUTORIZADO:
                if self.args.captura:
                    estado = captura()
                else:
                    print(not all(vars(self.args).values()))
                    break
            else:
                log.exception('La aplicación ha caido en un estado imposible.')
                sys.exit(1)
        log.debug(estado)


def main():
    """
    Arranca el programa
    """

    aplicacion = Aplicacion(get_options())
    aplicacion.run()


if __name__ == '__main__':  # pragma: no cover
    main()
