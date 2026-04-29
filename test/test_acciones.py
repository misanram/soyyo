"""
Tests del módulo acciones.py
"""

import base64
import hmac
import json
import os
from unittest.mock import patch

import keyring.errors as keyring_errors
import pytest

from soyyo.acciones import reset, setup
from soyyo.estados import EstadoSistema


@pytest.fixture
def almacen_valido(tmp_path):
    """Crea un fichero de datos con firma válida"""
    pepper = os.urandom(32)
    pepper_64 = base64.b64encode(pepper).decode('utf-8')

    datos = {'version': 1, 'autorizacion': {}, 'intentos': 0, 'semillas': {}}
    cadena_json = json.dumps(datos, sort_keys=True, separators=(',', ':')).encode()
    firma = hmac.new(pepper, cadena_json, 'sha512').hexdigest()

    datos = {'version': 1, 'autorizacion': {}, 'intentos': 0, 'semillas': {}, 'firma': firma}
    fichero = tmp_path / 'datos.json'
    with open(fichero, 'w', encoding='utf8') as fout:
        json.dump(datos, fout, sort_keys=True, separators=(',', ':'))

    return fichero, pepper_64


def test_reset_keyboard_interrupt(tmp_path, capsys):
    fichero = tmp_path / 'datos.json'
    with patch('soyyo.acciones.input', side_effect=KeyboardInterrupt):
        assert reset(fichero) == EstadoSistema.SALIENDO_OK


@pytest.mark.parametrize('respuesta', ['N', 'C'])
def test_reset_NC(tmp_path, respuesta):
    fichero = tmp_path / 'datos.json'
    with patch('soyyo.acciones.input', return_value=respuesta):
        assert reset(fichero) == EstadoSistema.SALIENDO_OK


def test_reset_otro_caracter(tmp_path, capsys):
    fichero = tmp_path / 'datos.json'
    with patch('soyyo.acciones.input', side_effect=['^', 'C']):
        assert reset(fichero) == EstadoSistema.SALIENDO_OK


def test_reset_S(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    with (patch('soyyo.acciones.input', return_value='S'),
          patch('soyyo.acciones.delete_password', return_value=None)):
        respuesta = reset(fichero)
    assert respuesta == EstadoSistema.PRIMER_ARRANQUE


def test_reset_S_keyring_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    with (patch('soyyo.acciones.input', return_value='S'),
          patch('soyyo.acciones.delete_password', side_effect=keyring_errors.PasswordDeleteError)):
        respuesta = reset(fichero)
    assert respuesta == EstadoSistema.PRIMER_ARRANQUE


def test_setup_sin_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    with (patch('soyyo.acciones.set_password'),
          patch('soyyo.acciones.validate_pin', return_value='12345678')):
        setup(fichero)
    assert fichero.exists()


def test_setup_sin_error_pin_no_ascii(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    with (patch('soyyo.acciones.set_password'),
          patch('soyyo.acciones.validate_pin', return_value='١٢٣٤٥٦٧٨')):
        setup(fichero)
    assert fichero.exists()


def test_setup_keyboard_interrupt(tmp_path, capsys):
    fichero = tmp_path / 'datos.json'
    with patch('soyyo.acciones.validate_pin', side_effect=KeyboardInterrupt):
        assert setup(fichero) == EstadoSistema.SALIENDO_OK


def test_setup_pines_distintos(tmp_path, capsys):
    fichero = tmp_path / 'datos.json'
    with (patch('soyyo.acciones.set_password'),
          patch('soyyo.acciones.validate_pin', side_effect=[0, 1, '12345678', '12345678'])):
        setup(fichero)
        captured = capsys.readouterr()
    assert '\nAmbos valores deben ser iguales.\n\n' in captured.out


def test_setup_set_keyring_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    with (patch('soyyo.acciones.validate_pin', return_value='12345678'),
          patch('soyyo.acciones.set_password', side_effect=keyring_errors.PasswordSetError)):
        assert setup(fichero) == EstadoSistema.SALIENDO_ERROR


def test_setup_file_write_error(tmp_path, capsys):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    fichero.chmod(0o444)
    with (patch('soyyo.acciones.set_password'),
          patch('soyyo.acciones.delete_password'),
          patch('soyyo.acciones.validate_pin', return_value='12345678')):
        assert setup(fichero) == EstadoSistema.SALIENDO_ERROR


def test_setup_delete_password_keyring_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    fichero.chmod(0o444)
    with (patch('soyyo.acciones.set_password'),
          patch('soyyo.acciones.validate_pin', return_value='12345678'),
          patch('soyyo.acciones.delete_password', side_effect=keyring_errors.PasswordDeleteError)):
        with pytest.raises(keyring_errors.PasswordDeleteError):
            setup(fichero)
