"""
Módulo prinicpal
"""

import argparse
import gettext
import locale
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .acciones import captura, comprobar_estado, lista, reset, setup
from .constantes import EstadoApp
from .mensajes import (MSG_ERROR_NO_CONTROLADO, MSG_FICHERO_CORRUPTO, MSG_FIRMA_INVALIDA,
                       MSG_SALIENDO_ERROR, MSG_SALIENDO_OK, MSG_SIN_KEYRING, MSG_SIN_PEPPER, )

locale.setlocale(locale.LC_ALL, '')

file_handler = RotatingFileHandler(Path(sys.prefix) / '../soyyo.log', maxBytes=1_000_000, backupCount=5)
logging.basicConfig(level=logging.WARNING,
                    handlers=[file_handler],
                    force=True,
                    format='%(asctime)s %(levelname)-5.5s [%(name)s:%(lineno)s][%(threadName)s] %(message)s')
logging.getLogger('soyyo').setLevel(logging.DEBUG)
log = logging.getLogger(__name__)

ruta_locales = Path(os.path.dirname(__file__)) / 'locales'
traduccion = gettext.translation('messages', localedir=ruta_locales, languages=['es'], fallback=True)
argparse._ = traduccion.gettext
argparse.ngettext = traduccion.ngettext


def get_options():
    """
    Lee las opciones con las que se arranca el programa.
    """

    parser = argparse.ArgumentParser(prog='soyyo',
                                     usage='%(prog)s [opción]',
                                     description="Programa para gestionar TOTP's",
                                     epilog='', )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument('--test', action='store_true', help=argparse.SUPPRESS)  # para test con pytest
    grupo.add_argument('--reset', action='store_true', help='Reinicia el programa a su estado de fábrica')
    grupo.add_argument('--captura', action='store_true', help='Captura un QR')
    grupo.add_argument('--lista', action='store_true', help='Lista los TOTP almacenados')
    return parser


class Aplicacion:
    """
    Clase principal del programa
    """

    def __init__(self, args):
        root_path = (Path(sys.prefix) / '../').resolve()
        # bin_path = Path(sys.executable).parent
        # self.app_executable = bin_path / 'soyyo'
        self.data_path = root_path / 'soyyo_data.json'
        self.args = args

    def run(self):
        """
        Inicia el programa
        """

        try:
            estado = comprobar_estado(self.data_path)
            log.debug('Estado inicial: %s', estado)

            if self.args.reset and estado not in (EstadoApp.SIN_KEYRING,):
                log.debug('Acción solicitada: reset')
                estado = reset(self.data_path)
                log.debug('Estado postreset: %s', estado)

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
                    log.debug('Acción solicitada: setup')
                    estado = setup(self.data_path)

                elif estado == EstadoApp.INICIALIZACION_CORRECTA:
                    if self.args.captura:
                        log.debug('Acción solicitada: captura')
                        estado = captura(self.data_path)
                    elif self.args.lista:
                        log.debug('Acción solicitada: lista')
                        estado = lista(self.data_path)
                    else:
                        print(not all(vars(self.args).values()))
                        break
                else:
                    log.error('La aplicación ha caido en un estado imposible: %s', estado)
                    sys.exit(1)
            log.debug('Estado final: %s', estado)

        except Exception as error:
            log.exception('Error no controlado.')
            print(error)
            print(MSG_ERROR_NO_CONTROLADO)
            sys.exit(1)


def main():
    """
    Arranca el programa
    """

    parser = get_options()
    argumentos = parser.parse_args()
    if not any(vars(argumentos).values()):
        parser.print_help()
        log.debug('Aplicación llamada sin argumentos.')
        sys.exit(0)
    aplicacion = Aplicacion(argumentos)
    aplicacion.run()


if __name__ == '__main__':  # pragma: no cover
    main()
