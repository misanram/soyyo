"""
Fixtures usadas en los test.
"""

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture
def almacen_valido(tmp_path):
    """Crea un fichero de datos con firma válida"""

    def _factory(minutos_bloqueo=0, num_bloqueos=0, firmar='SI', manipulado=False):
        pin = bytearray(b'12345678')
        salt = os.urandom(32)
        pepper = os.urandom(32)

        dk = hashlib.pbkdf2_hmac('sha256', bytes(pin) + pepper, salt, 500_000, dklen=64)

        hash_64 = base64.b64encode(dk[:32]).decode('utf-8')
        salt_64 = base64.b64encode(salt).decode('utf-8')
        pepper_64 = base64.b64encode(pepper).decode('utf-8')

        autorizacion = {'hash': hash_64, 'salt': salt_64}
        if minutos_bloqueo == 0:
            momento = None
        else:
            momento = (datetime.now(timezone.utc) + timedelta(minutes=minutos_bloqueo)).isoformat()
        datos = {'version': 1, 'autorizacion': autorizacion, 'intentos': 1, 'bloqueado_hasta': momento,
                 'num_bloqueos': num_bloqueos, 'totp': {}}
        cadena_json = json.dumps(datos, sort_keys=True, separators=(',', ':')).encode()

        if firmar == 'NO':
            firma = None
        elif firmar == 'fake':
            firma = 'firma_fake'
        else:
            firma = hmac.new(pepper, cadena_json, 'sha512').hexdigest()
        if manipulado:
            num_bloqueos -= 1
        datos = {'version': 1, 'autorizacion': autorizacion, 'intentos': 1, 'bloqueado_hasta': momento,
                 'num_bloqueos': num_bloqueos, 'totp': {}, 'firma': firma}
        fichero = tmp_path / 'datos.json'
        with open(fichero, 'w', encoding='utf8') as fout:
            json.dump(datos, fout, sort_keys=True, separators=(',', ':'))

        return fichero, pepper_64

    return _factory
