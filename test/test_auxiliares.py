"""
Tests del módulo auxiliares.py
"""

import base64
import hmac
import json
import os
from unittest.mock import patch

import keyring.errors as keyring_errors
import pytest

from soyyo.auxiliares import (chek_almacen, chek_integrity_json, chek_keyring, chek_pepper, EstadoSistema,
                              validate_pin)


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


def test_chek_keyring_devuelve_cadena_incorrecta():
    """Keyring escribe, pero devuelve un valor inesperado"""
    with (patch('soyyo.auxiliares.set_password'),
          patch('soyyo.auxiliares.get_password', return_value='otra_cosa')):
        assert chek_keyring() is False


def test_chek_keyring_devuelve_none():
    """Keyring escribe, pero devuelve otro valor inesperado"""
    with patch('soyyo.auxiliares.set_password'), patch('soyyo.auxiliares.get_password', return_value=None):
        assert chek_keyring() is False


def test_chek_keyring_devuelve_cadena_vacia():
    """Keyring escribe, pero devuelve otro valor inesperado"""
    with patch('soyyo.auxiliares.set_password'), patch('soyyo.auxiliares.get_password', return_value=''):
        assert chek_keyring() is False


def test_chek_keyring_no_disponible():
    """No hay keyring en el sistema"""
    with patch('soyyo.auxiliares.set_password', side_effect=keyring_errors.NoKeyringError):
        assert chek_keyring() is False


def test_chek_almacen_existe(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    assert chek_almacen(fichero) is True


def test_chek_almacen_no_existe(tmp_path):
    fichero = tmp_path / 'datos.json'
    assert chek_almacen(fichero) is False


def test_chek_pepper_no_hay_pepper():
    with patch('soyyo.auxiliares.get_password', return_value=None):
        assert chek_pepper() is False


def test_chek_pepper_hay_pepper():
    with patch('soyyo.auxiliares.get_password', return_value='datos'):
        assert chek_pepper() is True


def test_chek_integrity_sin_pepper(almacen_valido, capsys):
    fichero, pepper_64 = almacen_valido
    with patch('soyyo.auxiliares.get_password', return_value=None):
        with pytest.raises(SystemExit):
            chek_integrity_json(fichero)
        captured = capsys.readouterr()
        assert 'La aplicación no puede continuar.' in captured.out


def test_chek_integrity_fichero_no_existe(tmp_path, capsys):
    """El fichero de datos no existe"""
    fichero = tmp_path / 'datos.json'
    with pytest.raises(SystemExit):
        chek_integrity_json(fichero)
    captured = capsys.readouterr()
    assert 'La aplicación no puede continuar.' in captured.out


def test_chek_integrity_json_corrupto(tmp_path, capsys):
    """El fichero no es JSON válido"""
    fichero = tmp_path / 'datos.json'
    fichero.write_text('esto no es json', encoding='utf8')
    with patch('soyyo.auxiliares.get_password', return_value='cGVwcGVy'):
        assert chek_integrity_json(fichero) == EstadoSistema.FICHERO_CORRUPTO


def test_chek_integrity_todo_OK(almacen_valido, capsys):
    fichero, pepper_64 = almacen_valido
    with patch('soyyo.auxiliares.get_password', return_value=pepper_64):
        assert chek_integrity_json(fichero) == EstadoSistema.OK


def test_chek_integrity_firma_manipulada(almacen_valido, capsys):
    fichero, pepper_64 = almacen_valido
    datos = json.loads(fichero.read_text(encoding='utf8'))
    datos['intentos'] = 99
    with open(fichero, 'w', encoding='utf8') as fout:
        json.dump(datos, fout, sort_keys=True, separators=(',', ':'))
    with patch('soyyo.auxiliares.get_password', return_value=pepper_64):
        assert chek_integrity_json(fichero) == EstadoSistema.FIRMA_INVALIDA


def test_validate_pin_pin_valido():
    with patch('soyyo.auxiliares.getpass', return_value='012345678'):
        resultado = validate_pin('')
    assert resultado == '012345678'


def test_validate_pin_pin_valido_no_ascii():
    with patch('soyyo.auxiliares.getpass', return_value='١٢٣٤٥٦٧٨'):
        resultado = validate_pin('')
    assert resultado == '١٢٣٤٥٦٧٨'


def test_validate_pin_pin_corto(capsys):
    with patch('soyyo.auxiliares.getpass', side_effect=['1', '12345678']):
        resultado = validate_pin('')
        captured = capsys.readouterr()
    assert '\nEl PIN debe tener entre 8 y 20 cifras.\n' in captured.out
    assert resultado == '12345678'


def test_validate_pin_pin_vacio(capsys):
    with patch('soyyo.auxiliares.getpass', side_effect=['', '12345678']):
        resultado = validate_pin('')
        captured = capsys.readouterr()
    assert '\nEl PIN debe tener entre 8 y 20 cifras.\n' in captured.out
    assert resultado == '12345678'


def test_validate_pin_pin_largo(capsys):
    with patch('soyyo.auxiliares.getpass', side_effect=['123456789012345678901', '12345678']):
        resultado = validate_pin('')
        captured = capsys.readouterr()
    assert '\nEl PIN debe tener entre 8 y 20 cifras.\n' in captured.out
    assert resultado == '12345678'


def test_validate_pin_pin_no_numerico(capsys):
    with patch('soyyo.auxiliares.getpass', side_effect=['12345678O', '12345678']):
        resultado = validate_pin('')
        captured = capsys.readouterr()
    assert '\nTodos los caracteres deben ser numéricos.' in captured.out
    assert resultado == '12345678'


def test_validate_pin_keyboard_interrupt():
    with patch('soyyo.auxiliares.getpass', side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            validate_pin('')
