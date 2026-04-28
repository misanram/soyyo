"""
Funciones auxiliares del programa
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import time
from enum import Enum
from getpass import getpass

import keyring.errors as keyring_errors
from keyring import delete_password, get_password, set_password

log = logging.getLogger('__name__')


class ErrorApp(Exception):
    """
    Error de la aplicación
    """
    pass


class EstadoSistema(Enum):
    """
    Define los estados en los que puede encontrrse el sistema
    """
    SIN_KEYRING = 'sin_keyring'  # No hay keyring disponible
    PRIMER_ARRANQUE = 'primer_arranque'  # No hay fichero de datos
    SIN_PEPPER = 'sin_pepper'  # No hay pepper en el keyring
    FICHERO_CORRUPTO = 'fichero_corrupto'  # JSON inválido o ilegible
    FIRMA_INVALIDA = 'firma_invalida'  # El fichero ha sido manipulado
    OK = 'ok'  # Todo correcto


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


def chek_integrity_json(data_path):
    """
    Comprueba que la firma del json es válida (que el .json no ha sido manipulado)
    """

    try:
        try:
            with open(data_path, 'r', encoding='utf8') as fin:
                datos = json.load(fin)
        except json.JSONDecodeError:
            return EstadoSistema.FICHERO_CORRUPTO

        firma = datos.get('firma')
        del datos['firma']

        cadena_json = json.dumps(datos, sort_keys=True, separators=(',', ':')).encode()
        pepper = get_password('soyyo', 'pepper')
        nueva_firma = hmac.new(base64.b64decode(pepper), cadena_json, 'sha512').hexdigest()  # type: ignore

        if hmac.compare_digest(firma, nueva_firma):
            return EstadoSistema.OK
        return EstadoSistema.FIRMA_INVALIDA

    except Exception as error:
        log.exception(error)
        print(error)
        print('La aplicación no puede continuar.')
        sys.exit(1)


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


def setup(data_path):
    """
    Pide el PIN y lo guarda.
    """

    while True:
        if sys.stdout.isatty():
            print('\033[2J\033[H', end='')  # pragma: no cover
        print("""
    Debe crear un PIN para usar la aplicación.
    Manténgalo en secreto y no lo comparta.

    MUY IMPORTANTE: El PIN no puede recuperarse. Si lo olvida,
    no podrá acceder a los datos de la aplicación.
    
    - Use solamente caracteres numéricos.
    - Longitud: 8-20 caracteres.""")

        preguntas = ['PIN', 'Repita el PIN']
        pines = []

        try:
            pines = [validate_pin(arg) for arg in preguntas]
        except KeyboardInterrupt:
            print('\n\nCancelado por el usuario.')
            sys.exit(1)

        if len(set(pines)) != 1:
            print('\nAmbos valores deben ser iguales.\n\n')
            time.sleep(1)
            continue
        break

    pin = str(set(pines).pop())
    salt = os.urandom(32)
    pepper = os.urandom(32)

    dk = hashlib.pbkdf2_hmac('sha256', pin.encode(), salt, 500_000)

    hash_64 = base64.b64encode(dk).decode('utf-8')
    salt_64 = base64.b64encode(salt).decode('utf-8')
    pepper_64 = base64.b64encode(pepper).decode('utf-8')

    autorizacion = {'hash': hash_64, 'salt': salt_64}
    semillas = {}

    datos = {'version': 1, 'autorizacion': autorizacion, 'intentos': 0, 'semillas': semillas}
    cadena_json = json.dumps(datos, sort_keys=True, separators=(',', ':')).encode()
    firma = hmac.new(pepper, cadena_json, 'sha512').hexdigest()

    try:
        set_password('soyyo', 'pepper', pepper_64)
    except keyring_errors.PasswordSetError as error:
        log.error(error)
        print(error)
        print('La aplicación no puede continuar.')
        sys.exit(1)

    try:
        datos = {'version': 1, 'autorizacion': autorizacion, 'intentos': 0, 'semillas': semillas,
                 'firma': firma}
        with open(data_path, 'w', encoding='utf8') as fout:
            json.dump(datos, fout, sort_keys=True, separators=(',', ':'))
        return EstadoSistema.OK
    except Exception as error:
        log.error(error)
        delete_password('soyyo', 'pepper')
        print(error)
        print('La aplicación no puede continuar.')
        sys.exit(1)


def reset(data_path):
    """
    Elimina (si existen) el almacen de datos y la clave pepper del keyring
    """

    prompt = """
        ¡¡¡ATENCIÓN!!!
        
        Ha solicitado eliminar por completo toda la configuración.
        
        Ello eliminará todas sus secreto TOTP almacenados
        
        Este paso es irreversible.
        Si/No/Cancelar: """

    if sys.stdout.isatty():
        print('\033[2J\033[H', end='')  # pragma: no cover

    while True:
        if sys.stdout.isatty():
            print('\033[2J\033[H', end='')  # pragma: no cover

        try:
            data = input(prompt).upper().strip()
        except KeyboardInterrupt:
            data = 'C'

        if len(data) != 1 or data not in 'NSC':
            continue

        if data == 'S':
            data_path.unlink(missing_ok=True)
            try:
                delete_password('soyyo', 'pepper')
            except keyring_errors.PasswordDeleteError:
                pass
            sys.exit(0)
        else:
            print('\n\n        Abortando reset...')
            sys.exit(0)
