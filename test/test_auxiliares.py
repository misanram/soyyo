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
                              obtener_pin)


@pytest.fixture
def almacen_valido(tmp_path):
    """Crea un fichero de datos con firma válida"""
    pepper = os.urandom(32)
    pepper_64 = base64.b64encode(pepper).decode('utf-8')

    datos = {'version': 1, 'autorizacion': {}, 'intentos': 0, 'totp': {}}
    cadena_json = json.dumps(datos, sort_keys=True, separators=(',', ':')).encode()
    firma = hmac.new(pepper, cadena_json, 'sha512').hexdigest()

    datos = {'version': 1, 'autorizacion': {}, 'intentos': 0, 'totp': {}, 'firma': firma}
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


def test_chek_firma_OK(almacen_valido):
    fichero, pepper = almacen_valido
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        assert chek_firma(fichero) is True


def test_chek_firma_manipulada(almacen_valido):
    fichero, pepper = almacen_valido
    datos = json.loads(fichero.read_text(encoding='utf8'))
    datos['intentos'] = 99
    with open(fichero, 'w', encoding='utf8') as fout:
        json.dump(datos, fout, sort_keys=True, separators=(',', ':'))
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        assert chek_firma(fichero) is False


def test_chek_firma_sin_pepper(almacen_valido):
    fichero, pepper = almacen_valido
    with patch('soyyo.auxiliares.get_password', return_value=None):
        with pytest.raises(TypeError):
            chek_firma(fichero)


def test_obtener_pin_pin_valido_salto_de_linea():
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\n']
    with patch('termios.tcgetattr', return_value=[]):
        with patch('termios.tcsetattr'):
            with patch('tty.setraw'):
                with patch('sys.stdin.buffer.read', side_effect=teclas):
                    with patch('sys.stdin.fileno', return_value=0):
                        resultado = obtener_pin('PIN: ')
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_valido_retorno_de_carro():
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    with patch('termios.tcgetattr', return_value=[]):
        with patch('termios.tcsetattr'):
            with patch('tty.setraw'):
                with patch('sys.stdin.buffer.read', side_effect=teclas):
                    with patch('sys.stdin.fileno', return_value=0):
                        resultado = obtener_pin('PIN: ')
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_valido_backspace():
    teclas = [b'1', b'2', b'3', b'3', b'\x7f', b'4', b'5', b'6', b'7', b'8', b'\r']
    with patch('termios.tcgetattr', return_value=[]):
        with patch('termios.tcsetattr'):
            with patch('tty.setraw'):
                with patch('sys.stdin.buffer.read', side_effect=teclas):
                    with patch('sys.stdin.fileno', return_value=0):
                        resultado = obtener_pin('PIN: ')
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_valido_backspace_inicio():
    teclas = [b'\x7f', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    with patch('termios.tcgetattr', return_value=[]):
        with patch('termios.tcsetattr'):
            with patch('tty.setraw'):
                with patch('sys.stdin.buffer.read', side_effect=teclas):
                    with patch('sys.stdin.fileno', return_value=0):
                        resultado = obtener_pin('PIN: ')
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_valido_caracter_no_ascii():
    teclas = [b'\xc3', b'\xa9',  # primer byte de 'é' y segundo byte de 'é'
              b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']

    with patch('termios.tcgetattr', return_value=[]):
        with patch('termios.tcsetattr'):
            with patch('tty.setraw'):
                with patch('sys.stdin.buffer.read', side_effect=teclas):
                    with patch('sys.stdin.fileno', return_value=0):
                        resultado = obtener_pin('PIN: ')
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_corto(capsys):
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'\r', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8',
              b'\r']
    with patch('termios.tcgetattr', return_value=[]):
        with patch('termios.tcsetattr'):
            with patch('tty.setraw'):
                with patch('sys.stdin.buffer.read', side_effect=teclas):
                    with patch('sys.stdin.fileno', return_value=0):
                        resultado = obtener_pin('PIN: ')
                        captured = capsys.readouterr()
    assert '\nEl PIN debe tener entre 8 y 20 cifras.\n' in captured.out
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_vacio(capsys):
    teclas = [b'\r', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    with patch('termios.tcgetattr', return_value=[]):
        with patch('termios.tcsetattr'):
            with patch('tty.setraw'):
                with patch('sys.stdin.buffer.read', side_effect=teclas):
                    with patch('sys.stdin.fileno', return_value=0):
                        resultado = obtener_pin('PIN: ')
                        captured = capsys.readouterr()
    assert '\nEl PIN debe tener entre 8 y 20 cifras.\n' in captured.out
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_largo(capsys):
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'9', b'0', b'1', b'2', b'3', b'4', b'5', b'6',
              b'7', b'8', b'9', b'0', b'1', b'2', b'3', b'4', b'\r', b'1', b'2', b'3', b'4', b'5', b'6', b'7',
              b'8', b'\r']
    with patch('termios.tcgetattr', return_value=[]):
        with patch('termios.tcsetattr'):
            with patch('tty.setraw'):
                with patch('sys.stdin.buffer.read', side_effect=teclas):
                    with patch('sys.stdin.fileno', return_value=0):
                        resultado = obtener_pin('PIN: ')
                        captured = capsys.readouterr()
    assert '\nEl PIN debe tener entre 8 y 20 cifras.\n' in captured.out
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_keyboard_interrupt():
    with patch('termios.tcgetattr', return_value=[]):
        with patch('termios.tcsetattr'):
            with patch('tty.setraw'):
                with patch('sys.stdin.buffer.read', side_effect=KeyboardInterrupt):
                    with patch('sys.stdin.fileno', return_value=0):
                        with pytest.raises(KeyboardInterrupt):
                            obtener_pin('')


def test_obtener_pin_keyboard_interrupt_caracter():
    teclas = [b'\x03']
    with patch('termios.tcgetattr', return_value=[]):
        with patch('termios.tcsetattr'):
            with patch('tty.setraw'):
                with patch('sys.stdin.buffer.read', side_effect=teclas):
                    with patch('sys.stdin.fileno', return_value=0):
                        with pytest.raises(KeyboardInterrupt):
                            obtener_pin('')


def test_caracter_invalido_genera_bell():
    teclas = [b'z', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    with patch('termios.tcgetattr', return_value=[]):
        with patch('termios.tcsetattr'):
            with patch('tty.setraw'):
                with patch('sys.stdin.buffer.read', side_effect=teclas):
                    with patch('sys.stdin.fileno', return_value=0):
                        with patch('sys.stdout.write') as mock_write:
                            obtener_pin('PIN: ')
                            llamadas = [args[0] for args, kwargs in mock_write.call_args_list]
                            assert '\x07' in llamadas
