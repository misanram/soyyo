"""
Funciones auxiliares del programa
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import readline  # noqa: F401
import subprocess
import sys
import termios
import time
import tty
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from functools import wraps
from string import digits
from typing import Any, ClassVar

import keyring
import keyring.errors as keyring_errors

from .constantes import BaseTabla, EstadoApp, TIEMPO_DE_BLOQUEO
from .errores import AppError, FirmaInvalidaError, PepperNotFoundError
from .mensajes import (MSG_CABECERA, MSG_ERROR_APP_BLOQUEADA_TEMPORAL, MSG_ERROR_APP_BLOQUEDA,
                       MSG_ERROR_LECTURA_ESCRITURA_ALMACEN_DATOS, MSG_FIRMA_INVALIDA, MSG_SIN_DISPOSITIVO,
                       MSG_SIN_PEPPER)

log = logging.getLogger(__name__)


@dataclass
class Usable(BaseTabla):
    """
    Rutas usables
    Esta clase se usa para almacenar las rutas en las que se peude grabar el fichero con la clave maestra
    para poder resetear la aplicación

    max_len es un diccionario que contiene la longitud máxima del valor los atributos:
        la clave es el nombre del atributo (ruta y longitud en este caso)
        el valor es la longitud máxima del valor del atributo (es un literal) siendo el mínimo la longitud
        del nombre del atributo (4 y 9 en este caso)
    Este diccionario se usa para calcular las dimensiones de la tabla que se muestra en la selección de la
    unidad a grabar la clave maestra.
    """

    max_len: ClassVar[dict] = {}
    instancias: ClassVar[int] = 0
    ruta: str = ''
    capacidad: str = ''

    def _campos_especificios(self):
        return ['ruta', 'capacidad']


def reintentar_keyring(intentos=3, espera=0.2):
    """
    Decorador para reintentar los accesos al keyring que se "desconecta" de vez en cuendo.
    El decorardor lo hizo en gran parte Claude Sonnet 4.6
    """

    def _decorador(func):
        @wraps(func)
        def _wrapper(*args, **kwargs):
            for _ in range(intentos):
                try:
                    return func(*args, **kwargs)
                except Exception as error:
                    if 'session' in str(error).lower() or 'InvalidObjectPath' in str(error):
                        if _ < intentos - 1:
                            time.sleep(espera)
                        else:
                            raise
                    else:
                        raise

            return None  # pragma: no cover # satisface al IDE, nunca se alcanza

        return _wrapper

    return _decorador


keyring.get_password = reintentar_keyring()(keyring.get_password)


def check_keyring():
    """
    Comprueba si keyring es usable en este sistema
    """

    try:
        keyring.set_password('test_service_name', 'test_username_', 'test_password')
        dato = keyring.get_password('test_service_name', 'test_username_')
        keyring.delete_password('test_service_name', 'test_username_')
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


def captura_teclado(prompt='', una_tecla=False, setup=False, pin=False, dispara=''):
    """
    Esta función está diseñada para capturar datos para la app es una sustitución vitaminada del input()
    Puede recibir varios parámetros:
        prompt: hace las veces del promp del input
        una_tecla: Si True solo recoge una pulsación y return (en plan pulse una tecla para continuar...)
        setup: Si True configura para la acción setup
        pin: Si True configura para pedir un PIN
        dispara: Hace que la función espere a que alguna de las teclas de string sea pulsada y la devuelve.

        Salvo prompt, los demás paraámetros son incompatibles entre sí. Si se recibe más de un parámetro se
        levanta una exception

    Pasos:
        Crea una cadena de texto que usa como prompt
        Pide los datos (byte a byte)
        Valida el dato recibido
        Devuelve el dato validado
    La captura puede detenerse con Ctrl+C

    Return
        La entrada validada o KeyboardInterrupt
    """

    if sum(bool(_) for _ in [una_tecla, setup, pin, dispara]) > 1:
        raise TypeError('Parámetros incompatibles en la llamada a la función')

    if setup or pin or una_tecla:
        oculto = True
        dispara = ''
    else:
        oculto = False

    aceptables = digits + dispara

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
                    if una_tecla:  # Una unica pulsación termina el bucle
                        break
                    if ch[0] not in (3, 10, 13, 127) and chr(ch[0]) not in aceptables:
                        sys.stdout.write('✗')
                        sys.stdout.flush()
                        time.sleep(0.1)
                        sys.stdout.write('\b \b')  # retrocede, sobreescribe con espacio, retrocede
                        sys.stdout.flush()
                        sys.stdout.write('\x07')  # campana
                        sys.stdout.flush()
                        continue
                    if ch[0] in (10, 13):  # Retorno de carro y salto de linea
                        break
                    elif chr(ch[0]) in dispara:  # Un único carácter (en dispara) termina el bucle
                        data = ch
                        break
                    elif ch[0] == 127:  # retroceso
                        if data:
                            data.pop()
                            sys.stdout.write('\b \b')  # retrocede, sobreescribe con espacio, retrocede
                            sys.stdout.flush()
                    elif ch[0] == 3:  # ^C en modo raw
                        raise KeyboardInterrupt
                    else:
                        data += ch
                        if oculto:
                            sys.stdout.write('*')
                        else:
                            sys.stdout.write(ch.decode())
                        sys.stdout.flush()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except KeyboardInterrupt:
            raise

        if setup and not (8 <= len(data) <= 20):
            print('\nEl PIN debe tener entre 8 y 20 cifras.\n')
            time.sleep(1)
            continue
        return data


def validar_pin(data_path, pin):
    """
    Se comprueba que el PIN recibido es correcto
    """

    pepper: Any = None
    try:
        with open(data_path, 'r', encoding='utf8') as fin:
            datos = json.load(fin)
            _hash = base64.b64decode(datos['autorizacion']['hash'])
            salt = base64.b64decode(datos['autorizacion']['salt'])
        pepper64 = keyring.get_password('soyyo', 'pepper')
        if pepper64:
            pepper = bytearray(base64.b64decode(pepper64))
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
        log.warning("Fallo al leer '%s': %s", data_path, error)
        raise
    finally:
        for i in range(len(pin)):
            pin[i] = 0
        del pin
        if pepper:
            for i in range(len(pepper)):
                pepper[i] = 0
            del pepper


def guardar_json(data_path, datos):
    """
    Guarda los datos recibos como fichero JSON
    """

    try:
        pepper = keyring.get_password('soyyo', 'pepper')
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
        log.warning("Fallo al escribir '%s': %s", data_path, error)
        raise


def cargar_y_verificar_almacen(data_path):
    """
    Lee, verifica y parsea el fichero almacen. Nunca devuelve datos no verificados.
    """

    try:
        with open(data_path, 'rb') as fin:
            datos = json.load(fin)
            firma = datos.pop('firma', None)
            if firma is None:
                log.warning(FirmaInvalidaError.__doc__)
                raise FirmaInvalidaError
        cadena_json = json.dumps(datos, sort_keys=True, separators=(',', ':')).encode()
        pepper = keyring.get_password('soyyo', 'pepper')
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
        log.warning("Fallo al leer '%s': %s", data_path, error)
        raise


def autorizame(data_path):
    """
    Se solicita el PIN y se comprueba. Dos posibiliades:
    Se autoriza: devuelve el almacén para que lo pueda utilizar la acción que ha pedido autorización
    No autoriza: gestiona el bloqueo actualizando el fichero JSON con el número de intentos y en caso
    necesario con el tiempo de bloqueo y el contador de bloqueos. Se devuelve un estado para que la acción
    que ha pedido autorización lo devuelva al programa.
    """

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

        while intento < 3:
            try:
                pin = captura_teclado(prompt='\n\rIntroduzca el PIN: ', pin=True)
                print('\r')
            except KeyboardInterrupt:
                log.info('Cancelado por el usuario.')
                bloqueado_hasta = (
                        datetime.now(timezone.utc) + timedelta(
                        minutes=TIEMPO_DE_BLOQUEO[num_bloqueos])).isoformat()
                datos.update(
                        dict(intentos=intento, num_bloqueos=num_bloqueos, bloqueado_hasta=bloqueado_hasta))
                guardar_json(data_path, datos)
                return False, None, EstadoApp.SALIENDO_OK

            if validar_pin(data_path, pin):
                log.debug('PIN correcto')
                datos.update(dict(intentos=0, num_bloqueos=0, bloqueado_hasta=None))
                guardar_json(data_path, datos)
                return True, (datos, pin), None
            else:
                intento += 1
                log.debug('PIN erróneo, intento: %s bloqueo: %s', intento, num_bloqueos)
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
        log.exception("Fallo al escribir '%s': %s", data_path, error)
        print(MSG_ERROR_LECTURA_ESCRITURA_ALMACEN_DATOS)
        return False, None, EstadoApp.FICHERO_CORRUPTO


def detectar_usb():
    """
    Crea una lista con los puntos de montaje disponibles para usar.
    """

    result = subprocess.run(['/usr/bin/lsblk', '-J', '-o', 'NAME,TRAN,MOUNTPOINT,LABEL,SIZE,RM'],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr)

    Usable.reset()

    usables = []
    for _ in json.loads(result.stdout)["blockdevices"]:
        particiones = _.get('children', [{}])
        for particion in particiones:
            punto_montaje = particion.get('mountpoint')
            if punto_montaje and os.access(punto_montaje, os.W_OK):
                usables.append(Usable(ruta=punto_montaje, capacidad=particion.get('size')))  # type: ignore
    return usables


def muestra_tabla(lista_datos, primer_elemento=0, ultimo_elemento=5):
    """
    Muestra una bonita tabla con los campos del dataclass (derivado de BaseTabla) que se le pasa.
    """

    try:
        if not lista_datos:
            log.warning('Lista vacia')
            raise AppError

        clase = lista_datos[0].__class__
        if not is_dataclass(clase):
            log.warning('Lista sin dataclass')
            raise AppError

        def _linea_tabla(columnas: int, inicio: str, medio: str, fin: str, max_len: dict) -> str:
            return inicio + ''.join(f'{"═" * (ancho + 2)}{medio if orden < columnas else fin}'
                                    for orden, ancho in enumerate(max_len.values()))

        def _linea_texto(columnas: int, inicio: str, medio: str, fin: str, datos: dict, formatear) -> str:
            return inicio + ''.join(f'{formatear(clave, valor)}{medio if valor[0] < columnas else fin}'
                                    for clave, valor in datos.items())

        tb0 = _linea_tabla(len(fields(clase)) - 1, '╔', '╤', '╗', clase.max_len)
        tb1 = _linea_tabla(len(fields(clase)) - 1, '╠', '╪', '╢', clase.max_len)
        tb2 = _linea_tabla(len(fields(clase)) - 1, '╚', '╧', '╝', clase.max_len)
        tmp = dict(zip((campo.name for campo in fields(clase)),
                       enumerate(clase.max_len.values())))
        formato = lambda clave, valor: f'{clave.capitalize():^{valor[1] + 2}}'
        tit = _linea_texto(len(fields(clase)) - 1, '║', '|', '║', tmp, formato)

        print(tb0)
        print(tit)
        print(tb1)
        formato = lambda clave, valor: f' {clave:<{valor[1]}} '
        for instancia in lista_datos[primer_elemento:ultimo_elemento]:
            tmp = dict(zip((getattr(instancia, campo.name) for campo in fields(clase)),
                           enumerate(clase.max_len.values())))
            txt = _linea_texto(len(fields(clase)) - 1, '║', '|', '║', tmp, formato)
            print(txt)
        print(tb2)

    except Exception:
        raise


def selecciona_ruta():
    """
    Muestra una pantalla para seleccionar una ruta.
    """

    inicio = 0
    rutas = detectar_usb()
    while True:
        if sys.stdout.isatty():
            print('\033c', end='')  # pragma: no cover
        print(MSG_CABECERA)
        if not rutas:
            print(MSG_SIN_DISPOSITIVO)
            return ''
        fin = min(inicio + 5, len(rutas))
        print(f'\nMostrando los dispositivos del {inicio + 1} al {fin}')
        muestra_tabla(rutas, inicio, inicio + 5)
        print(f'Hay {len(rutas)} dispositivo{'s' if len(rutas) > 1 else ''}\n'
              f'[S] Página Siguiente [A] Página Anterior\n[C] Cancelar\n'
              f'[{fin if inicio + 1 == fin else f"{inicio + 1}-{fin}"}] Elegir dispositivo ', end='')
        entrada = captura_teclado(dispara='acsACS').decode()
        if entrada in 'aA':
            inicio -= 5
            inicio = max(inicio, 0)
        elif entrada in 'sS':
            if inicio + 5 < len(rutas):
                inicio += 5
        elif entrada in 'cC':
            raise KeyboardInterrupt
        elif entrada.isdigit():
            if inicio + 1 <= int(entrada) <= fin:
                return rutas[int(entrada) - 1]
