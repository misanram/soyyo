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

from soyyo.auxiliares import (chek_almacen, chek_firma, chek_integridad_json, chek_keyring, chek_pepper,
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


def test_chek_integridad_json_existe_es_valido(almacen_valido):
    """El fichero de datos no existe"""
    fichero, pepper = almacen_valido
    assert chek_integridad_json(fichero) is True


def test_chek_integridad_json_no_existe(tmp_path):
    """El fichero de datos no existe"""
    fichero = tmp_path / 'datos.json'
    with pytest.raises(FileNotFoundError):
        chek_integridad_json(fichero)


def test_chek_integridad_json_existe_es_corrupto(tmp_path):
    """El fichero no es JSON válido"""
    fichero = tmp_path / 'datos.json'
    fichero.write_text('esto no es json', encoding='utf8')
    assert chek_integridad_json(fichero) is False


def test_chek_firma_OK(almacen_valido, capsys):
    fichero, pepper = almacen_valido
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        assert chek_firma(fichero) is True


def test_chek_firma_manipulada(almacen_valido, capsys):
    fichero, pepper = almacen_valido
    datos = json.loads(fichero.read_text(encoding='utf8'))
    datos['intentos'] = 99
    with open(fichero, 'w', encoding='utf8') as fout:
        json.dump(datos, fout, sort_keys=True, separators=(',', ':'))
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        assert chek_firma(fichero) is False


def test_chek_firma_sin_pepper(almacen_valido, capsys):
    fichero, pepper = almacen_valido
    with patch('soyyo.auxiliares.get_password', return_value=None):
        with pytest.raises(TypeError):
            chek_firma(fichero)


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
