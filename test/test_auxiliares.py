"""
Tests del módulo auxiliares.py
"""

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import keyring.errors as keyring_errors
import pytest

from soyyo.auxiliares import (_cargar_y_verificar_almacen, chek_almacen, chek_keyring, comprobar_seguridad,
                              guarda_json, obtener_pin, validar_pin)
from soyyo.constantes import EstadoApp, FirmaInvalidaError, PepperNotFoundError


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


def test_chek_keyring_devuelve_cadena_incorrecta():
    """Keyring escribe, pero devuelve un valor inesperado"""
    with (patch('soyyo.auxiliares.set_password'), patch('soyyo.auxiliares.get_password',
                                                        return_value='otra_cosa')):
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


def test_comprobar_seguridad_OK(almacen_valido):
    fichero, pepper = almacen_valido()
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        assert comprobar_seguridad(fichero) == EstadoApp.INICIALIZACION_CORRECTA


def test_comprobar_seguridad_no_hay_firma(almacen_valido):
    fichero, pepper = almacen_valido(firmar='NO')
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        assert comprobar_seguridad(fichero) == EstadoApp.FIRMA_INVALIDA


def test_comprobar_seguridad_firma_invalida(almacen_valido):
    fichero, pepper = almacen_valido(firmar='fake')
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        assert comprobar_seguridad(fichero) == EstadoApp.FIRMA_INVALIDA


def test_comprobar_seguridad_no_hay_pepper(almacen_valido):
    fichero, pepper = almacen_valido()
    with patch('soyyo.auxiliares.get_password', return_value=None):
        assert comprobar_seguridad(fichero) == EstadoApp.SIN_PEPPER


def test_comprobar_seguridad_joson_corrupto(almacen_valido):
    fichero, pepper = almacen_valido()
    with patch('soyyo.auxiliares.json.load', side_effect=json.JSONDecodeError('msg', 'doc', 0)):
        assert comprobar_seguridad(fichero) == EstadoApp.FICHERO_CORRUPTO


def test_comprobar_seguridad_error_lectura_fichero():
    assert comprobar_seguridad(Path('/noexiste')) == EstadoApp.FICHERO_CORRUPTO


def test_obtener_pin_pin_valido_salto_de_linea():
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\n']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', False)
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_valido_retorno_de_carro():
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', False)
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_valido_backspace():
    teclas = [b'1', b'2', b'3', b'3', b'\x7f', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', False)
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_valido_backspace_inicio():
    teclas = [b'\x7f', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', False)
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_valido_caracter_no_ascii():
    teclas = [b'\xc3', b'\xa9',  # primer byte de 'é' y segundo byte de 'é'
              b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', False)
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_corto(capsys):
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'\r', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8',
              b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', False)
        captured = capsys.readouterr()
    assert '\nEl PIN debe tener entre 8 y 20 cifras.\n' in captured.out
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_vacio(capsys):
    teclas = [b'\r', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', False)
        captured = capsys.readouterr()
    assert '\nEl PIN debe tener entre 8 y 20 cifras.\n' in captured.out
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_pin_largo(capsys):
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'9', b'0', b'1', b'2', b'3', b'4', b'5', b'6',
              b'7', b'8', b'9', b'0', b'1', b'2', b'3', b'4', b'\r', b'1', b'2', b'3', b'4', b'5', b'6', b'7',
              b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', False)
        captured = capsys.readouterr()
    assert '\nEl PIN debe tener entre 8 y 20 cifras.\n' in captured.out
    assert resultado == bytearray(b'12345678')


def test_obtener_pin_keyboard_interrupt():
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=KeyboardInterrupt),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        with pytest.raises(KeyboardInterrupt):
            obtener_pin('PIN: ', False)


def test_obtener_pin_keyboard_interrupt_caracter():
    teclas = [b'\x03']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        with pytest.raises(KeyboardInterrupt):
            obtener_pin('PIN: ', False)


def test_caracter_invalido_genera_bell():
    teclas = [b'z', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0),
          patch('sys.stdout.write') as mock_write):
        # @formatter:on
        obtener_pin('PIN: ', False)
        llamadas = [args[0] for args, kwargs in mock_write.call_args_list]
        assert '\x07' in llamadas


def test_validar_pin(almacen_valido):
    fichero, pepper = almacen_valido()
    pin = bytearray(b'12345678')
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        assert validar_pin(fichero, pin) is True


def test_validar_pin_erroneo(almacen_valido):
    fichero, pepper = almacen_valido()
    pin = bytearray(b'123456789')
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        assert validar_pin(fichero, pin) is False


def test_validar_pin_sin_pepper(almacen_valido):
    fichero, pepper = almacen_valido()
    pin = bytearray(b'12345678')
    with patch('soyyo.auxiliares.get_password', return_value=None):
        with pytest.raises(PepperNotFoundError):
            validar_pin(fichero, pin)


def test_guarda_json(almacen_valido):
    fichero, pepper = almacen_valido()
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        guarda_json(fichero, {})


def test_guarda_json_sin_pepper(almacen_valido):
    fichero, pepper = almacen_valido()
    with patch('soyyo.auxiliares.get_password', return_value=None):
        with pytest.raises(PepperNotFoundError):
            guarda_json(fichero, {})


def test_guarda_json_falla_escritura(almacen_valido):
    fichero, pepper = almacen_valido()
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        with pytest.raises(OSError):
            guarda_json(Path('/noexiste'), {})


def test__cargar_y_verificar_almacen(almacen_valido):
    fichero, pepper = almacen_valido()
    datos = json.loads(fichero.read_text(encoding='utf8'))
    del datos['firma']
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        assert _cargar_y_verificar_almacen(fichero) == datos


def test__cargar_y_verificar_almacen_no_hay_firma(almacen_valido):
    fichero, pepper = almacen_valido(firmar='NO')
    with pytest.raises(FirmaInvalidaError):
        _cargar_y_verificar_almacen(fichero)


def test__cargar_y_verificar_almacen_error_en_firma(almacen_valido):
    fichero, pepper = almacen_valido(firmar='fake')
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        with pytest.raises(FirmaInvalidaError):
            _cargar_y_verificar_almacen(fichero)


def test__cargar_y_verificar_almacen_firma_manipulada(almacen_valido):
    fichero, pepper = almacen_valido(manipulado=True)
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        with pytest.raises(FirmaInvalidaError):
            _cargar_y_verificar_almacen(fichero)


def test__cargar_y_verificar_almacen_firma_sin_pepper(almacen_valido):
    fichero, pepper = almacen_valido()
    with patch('soyyo.auxiliares.get_password', return_value=None):
        with pytest.raises(PepperNotFoundError):
            _cargar_y_verificar_almacen(fichero)


def test__cargar_y_verificar_almacen_no_hay_fichero():
    with pytest.raises(OSError):
        _cargar_y_verificar_almacen(Path('/no_existe'))
