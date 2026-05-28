"""
Funciones auxiliares del programa
"""

import base64
import hashlib
import hmac
import json
import logging
import sys
import termios
import time
import tty
from datetime import datetime, timedelta, timezone

import keyring.errors as keyring_errors
from keyring import get_password, set_password

from soyyo.constantes import EstadoApp, FirmaInvalidaError, PepperNotFoundError, TIEMPO_DE_BLOQUEO
from soyyo.mensajes import (MSG_ERROR_APP_BLOQUEADA_TEMPORAL, MSG_ERROR_APP_BLOQUEDA,
                            MSG_ERROR_LECTURA_ESCRITURA_ALMACEN_DATOS, MSG_FIRMA_INVALIDA,
                            MSG_SIN_PEPPER)

log = logging.getLogger(__name__)


def check_keyring():
    """
    Comprueba si keyring es usable en este sistema
    """

    try:
        set_password('test_service_name', 'test_username_', 'test_password')
        dato = get_password('test_service_name', 'test_username_')
        return dato == 'test_password'
    except keyring_errors.NoKeyringError as error:
        log.exception('No hay keyring instalado en el sistema.')
        print(error)
        return False


def check_almacen(data_path):
    """
    Comprueba si hay un almacen de datos, si no lo hay o estamos inciando la app o se borró accidentalmente.
    """

    return data_path.exists()


def obtener_pin(prompt_head, login=False):
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

    prompt = f'\n\r{prompt_head}: '

    while True:
        try:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            data = bytearray()
            try:
                tty.setraw(fd)
                sys.stdout.write(prompt)
                sys.stdout.flush()
                while True:
                    ch = sys.stdin.buffer.read(1)
                    if ch[0] not in (3, 10, 13, 127) and (ch[0] < 48 or ch[0] > 57):
                        sys.stdout.write('✗')
                        sys.stdout.flush()
                        time.sleep(0.1)
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                        sys.stdout.write('\x07')
                        sys.stdout.flush()
                        continue
                    if ch in (b'\n', b'\r'):
                        break
                    elif ch == b'\x7f':  # backspace
                        if data:
                            data.pop()
                            sys.stdout.write('\b \b')  # retrocede, sobreescribe con espacio, retrocede
                            sys.stdout.flush()
                    elif ch[0] == 3:  # ^C en modo raw
                        raise KeyboardInterrupt
                    else:
                        data += ch
                        sys.stdout.write('*')
                        sys.stdout.flush()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except KeyboardInterrupt:
            raise

        if not login and not (8 <= len(data) <= 20):
            print('\nEl PIN debe tener entre 8 y 20 cifras.\n')
            time.sleep(1)
            continue

        return data


def validar_pin(data_path, pin):
    """
    Se comprueba que el PIN recibido es correcto
    """

    try:
        with open(data_path, 'r', encoding='utf8') as fin:
            datos = json.load(fin)
            _hash = base64.b64decode(datos['autorizacion']['hash'])
            salt = base64.b64decode(datos['autorizacion']['salt'])
        pepper64 = get_password('soyyo', 'pepper')
        if pepper64:
            pepper = base64.b64decode(pepper64)
            dk = hashlib.pbkdf2_hmac('sha256', bytes(pin) + pepper, salt, 500_000, dklen=64)
            return hmac.compare_digest(dk[:32], _hash)
        raise PepperNotFoundError
    except PepperNotFoundError:
        log.warning(PepperNotFoundError.__doc__)
        raise PepperNotFoundError
    except json.JSONDecodeError:
        log.warning('Error decodificando fichero JSON.')
        raise
    except OSError as error:
        log.warning("Fallo al abrir '%s': %s", data_path, error)
        raise


def guardar_json(data_path, datos):
    """
    Guarda los datos recibos como fichero JSON
    """

    try:
        pepper = get_password('soyyo', 'pepper')
        datos.pop('firma', None)
        cadena_json = json.dumps(datos, sort_keys=True, separators=(',', ':')).encode()
        if pepper:
            pepper64 = base64.b64decode(pepper)
            firma = hmac.new(pepper64, cadena_json, hashlib.sha512).hexdigest()
            datos.update(dict(firma=firma))
        else:
            raise PepperNotFoundError
        with open(data_path, 'w', encoding='utf8') as fout:
            json.dump(datos, fout, sort_keys=True, separators=(',', ':'))
    except json.JSONDecodeError:
        log.warning('Error serializando JSON.')
        raise
    except PepperNotFoundError:
        log.warning(PepperNotFoundError.__doc__)
        raise
    except OSError as error:
        log.warning("Fallo al abrir '%s': %s", data_path, error)
        raise


def cargar_y_verificar_almacen(data_path):
    """
    Lee, verifica y parsea el fichero almacen. Nunca devuelve datos no verificados.
    """

    try:
        with open(data_path, 'r', encoding='utf8') as fin:
            datos = json.load(fin)
            firma = datos.pop('firma', None)
            if firma is None:
                log.warning(FirmaInvalidaError.__doc__)
                raise FirmaInvalidaError
        cadena_json = json.dumps(datos, sort_keys=True, separators=(',', ':')).encode()
        pepper = get_password('soyyo', 'pepper')
        if pepper:
            pepper64 = base64.b64decode(pepper)
            nueva_firma = hmac.new(pepper64, cadena_json, 'sha512').hexdigest()
            if hmac.compare_digest(firma, nueva_firma):
                return datos
            else:
                raise FirmaInvalidaError
        else:
            raise PepperNotFoundError
    except json.JSONDecodeError:
        log.warning('Error serializando JSON.')
        raise
    except PepperNotFoundError:
        log.warning(PepperNotFoundError.__doc__)
        raise
    except FirmaInvalidaError:
        log.warning(FirmaInvalidaError.__doc__)
        raise
    except OSError as error:
        log.warning("Fallo al abrir '%s': %s", data_path, error)
        raise


def autorizame(data_path):
    """
    Se solicita el PIN y se comprueba. Dos posibiliades:
    Se autoriza: devuelve el almacén para que lo pueda utilizar la acción que ha pedido autorización
    No autoriza: gestiona el bloqueo actualizando el fichero JSON con el número de intentos y en caso
    necesario con el tiempo de bloqueo y el contador de bloqueos. Se devuelve un estado para que la acción
    que ha pedido autorización lo devuelva al programa.
    """

    if sys.stdout.isatty():
        print('\033[2J\033[H', end='')  # pragma: no cover

    try:
        datos = cargar_y_verificar_almacen(data_path)
        intento = datos['intentos']
        num_bloqueos = datos['num_bloqueos']
        if datos['bloqueado_hasta']:
            bloqueado_hasta = datetime.fromisoformat(datos['bloqueado_hasta'])
            if datetime.now(timezone.utc) < bloqueado_hasta:
                log.info('Aplicación en bloqueo temporal.')
                print(MSG_ERROR_APP_BLOQUEADA_TEMPORAL % bloqueado_hasta.astimezone().isoformat())
                return False, None, EstadoApp.SALIENDO_OK
        if num_bloqueos >= 10:
            log.info('Aplicación bloqueada.')
            print(MSG_ERROR_APP_BLOQUEDA)
            return False, None, EstadoApp.SALIENDO_OK

        while intento <= 3:
            try:
                pin = obtener_pin('Introduzca el PIN', login=True)
                print('\r')
            except KeyboardInterrupt:
                log.info('Cancelado por el usuario.')
                return False, None, EstadoApp.SALIENDO_OK

            if validar_pin(data_path, pin):
                log.info('PIN correcto')
                datos.update(dict(intentos=0, num_bloqueos=0, bloqueado_hasta=None))
                guardar_json(data_path, datos)
                return True, (datos, pin), None
            else:
                log.info('PIN erróneo, intento %s', intento)
                intento += 1
                datos.update(dict(intentos=intento))
                guardar_json(data_path, datos)

        num_bloqueos += 1
        bloqueado_hasta = (
                datetime.now(timezone.utc) + timedelta(minutes=TIEMPO_DE_BLOQUEO[num_bloqueos])).isoformat()
        datos.update(dict(intentos=0, num_bloqueos=num_bloqueos, bloqueado_hasta=bloqueado_hasta))
        guardar_json(data_path, datos)
        return False, None, EstadoApp.SALIENDO_OK
    except FirmaInvalidaError:
        log.exception(FirmaInvalidaError.__doc__)
        print(MSG_FIRMA_INVALIDA)
        return False, None, EstadoApp.FIRMA_INVALIDA
    except PepperNotFoundError:
        log.exception(PepperNotFoundError.__doc__)
        print(MSG_SIN_PEPPER)
        return False, None, EstadoApp.SIN_PEPPER
    except OSError as error:
        log.exception("Fallo al abrir '%s': %s", data_path, error)
        print(MSG_ERROR_LECTURA_ESCRITURA_ALMACEN_DATOS)
        return False, None, EstadoApp.FICHERO_CORRUPTO
