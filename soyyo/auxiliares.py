"""
Funciones auxiliares del programa
"""

import base64
import hmac
import json
import logging
import time
from getpass import getpass

import keyring.errors as keyring_errors
from keyring import get_password, set_password

log = logging.getLogger(__name__)


def chek_keyring():
    """
    Comprueba si keyring es usable en este sistema
    """

    try:
        set_password('test_service_name', 'test_username_', 'test_password')
        dato = get_password('test_service_name', 'test_username_')
        return dato == 'test_password'
    except keyring_errors.NoKeyringError:
        return False


def chek_almacen(data_path):
    """
    Comprueba si hay un almacen de datos
    """

    return data_path.exists()


def chek_pepper():
    """
    Chequea que existe un pepper usable en el keyring
    """

    return get_password('soyyo', 'pepper') is not None


def chek_integridad_json(data_path):
    """
    Comprueba que el fichero de datos es json es válido
    """

    try:
        with open(data_path, 'r', encoding='utf8') as fin:
            json.load(fin)
            return True
    except json.JSONDecodeError:
        return False


def chek_firma(data_path):
    """
    Comprueba que la firma del json es válida (que el .json no ha sido manipulado)
    """

    with open(data_path, 'r', encoding='utf8') as fin:
        datos = json.load(fin)
    firma = datos.get('firma')
    del datos['firma']

    cadena_json = json.dumps(datos, sort_keys=True, separators=(',', ':')).encode()
    pepper = get_password('soyyo', 'pepper')
    nueva_firma = hmac.new(base64.b64decode(pepper), cadena_json, 'sha512').hexdigest()  # type: ignore

    return hmac.compare_digest(firma, nueva_firma)


def validate_pin(prompt_head):
    """
    This function is designed to capture the parameters for app.
    It captures input and validates the data obtained.
    Steps:
        Create a text string to use as a prompt.
        Request the input.
        Validate the received data.
        Return the validated data or None.
    Parameter capture can be interrupted with Ctrl+C

    Arguments
        prompt_head (str): Start of the message to be displayed to the user.

    Return
        The data validated or KeyboardInterrupt
    """

    prompt = f'\n{prompt_head}: '

    while True:
        try:
            data = getpass(prompt, echo_char='*').strip()
        except KeyboardInterrupt:
            raise

        if not (8 <= len(data) <= 20):
            print('\nEl PIN debe tener entre 8 y 20 cifras.\n')
            time.sleep(1)
            continue

        try:
            int(data)
        except ValueError:
            print('\nTodos los caracteres deben ser numéricos.')
            continue

        return data
