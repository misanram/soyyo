"""
Acciones que reliza el programa

"""

import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import time

import keyring.errors as keyring_errors
from keyring import delete_password, set_password

from soyyo.auxiliares import validate_pin
from soyyo.estados import EstadoSistema
from soyyo.mensajes import MSG_PROMPT_RESET, MSG_SETUP

log = logging.getLogger(__name__)


def setup(data_path):
    """
    Pide el PIN y lo guarda.
    """

    while True:
        if sys.stdout.isatty():
            print('\033[2J\033[H', end='')  # pragma: no cover

        print(MSG_SETUP)
        preguntas = ['PIN', 'Repita el PIN']
        pines = []

        try:
            pines = [validate_pin(arg) for arg in preguntas]
        except KeyboardInterrupt:
            return EstadoSistema.SALIENDO_OK

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
        return EstadoSistema.SALIENDO_ERROR

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
        return EstadoSistema.SALIENDO_ERROR


def reset(data_path):
    """
    Elimina (si existen) el almacen de datos y la clave pepper del keyring
    """

    if sys.stdout.isatty():
        print('\033[2J\033[H', end='')  # pragma: no cover

    while True:
        if sys.stdout.isatty():
            print('\033[2J\033[H', end='')  # pragma: no cover

        try:
            data = input(MSG_PROMPT_RESET).upper().strip()
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
            return EstadoSistema.PRIMER_ARRANQUE
        else:
            return EstadoSistema.SALIENDO_OK
