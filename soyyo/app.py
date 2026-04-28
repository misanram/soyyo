"""
Módulo prinicpal
"""

import argparse
import sys

from utils import chek_keyring, setup

def get_options():
    """
    Lee las opciones con las que se arranca el programa.
    """
    parser = argparse.ArgumentParser(prog='soyyo', usage='%(prog)s [opción]',
                                     description='Programa para hacer TOTP', epilog='', )
    grupo = parser.add_mutually_exclusive_group()
    # grupo.add_argument('-h', '--help', action='store_true', help='Muestra este mensaje de ayuda.')
    grupo.add_argument('--setup', action='store_true', help='Configuración del programa.')
    grupo.add_argument('--coso', action='store_true', help='Configuración del programa.')
    args = parser.parse_args()
    if args.setup:
        setup()


class Aplicacion:
    """
    Clase principal del programa
    """

    def __init__(self):
        pass

    def run(self):
        """
        Inicia el programa
        """
        1 / 0

        if not chek_keyring():
            print("""No hay un sistema de almacenamiento seguro disponible en este sistema.
    La aplicación no puede continuar.
    Para instalar uno consulte con el administrador de su sistema.""")
            sys.exit(1)

        # get_options()


def main():
    """
    Arranca el programa
    """

    bot = Aplicacion()
    bot.run()


if __name__ == '__main__':
    main()
