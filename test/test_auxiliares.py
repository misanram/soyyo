"""
Tests del módulo auxiliares.py
"""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import keyring.errors as keyring_errors
import pytest

from soyyo.auxiliares import (autorizame, cargar_y_verificar_almacen, check_almacen, check_keyring,
                              guardar_json, obtener_pin, reintentar_keyring, validar_pin)
from soyyo.constantes import EstadoApp, FirmaInvalidaError, PepperNotFoundError
from .fixtures import almacen_valido


def test_reintentar_keyring_funciona():
    mock_func = MagicMock(return_value='password123')
    func_decorada = reintentar_keyring()(mock_func)

    resultado = func_decorada('servicio', 'usuario')

    assert resultado == 'password123'
    assert mock_func.call_count == 1


def test_reintentar_keyring_falla():
    mock_func = MagicMock(side_effect=[
            Exception("InvalidObjectPath session error"),
            Exception("InvalidObjectPath session error"),
            Exception("InvalidObjectPath session error"),
            ])
    func_decorada = reintentar_keyring(intentos=3, espera=0)(mock_func)

    with pytest.raises(Exception, match="InvalidObjectPath"):
        func_decorada('servicio', 'usuario')

    assert mock_func.call_count == 3


def test_reintentar_keyring_fala_y_recupera():
    mock_func = MagicMock(side_effect=[
            Exception("InvalidObjectPath session error"),
            'password123',
            ])
    func_decorada = reintentar_keyring(intentos=3, espera=0)(mock_func)

    resultado = func_decorada('servicio', 'usuario')

    assert resultado == 'password123'
    assert mock_func.call_count == 2


def test_reintentar_keyring_error_desconocido():
    mock_func = MagicMock(side_effect=Exception("error desconocido"))
    func_decorada = reintentar_keyring(intentos=3, espera=0)(mock_func)

    with pytest.raises(Exception, match="error desconocido"):
        func_decorada('servicio', 'usuario')

    assert mock_func.call_count == 1  # no reintenta


def test_chek_keyring_funciona_bien():
    pepper_almacenado = {}  # actúa como keyring en memoria

    def _fake_set_password(servicio, usuario, valor):
        pepper_almacenado[(servicio, usuario)] = valor

    def _fake_get_password(servicio, usuario):
        return pepper_almacenado.get((servicio, usuario))

    with (patch('soyyo.auxiliares.keyring.set_password', side_effect=_fake_set_password),
          patch('soyyo.auxiliares.keyring.get_password', side_effect=_fake_get_password)):
        assert check_keyring() is True


def test_chek_keyring_devuelve_cadena_incorrecta():
    """Keyring escribe, pero devuelve un valor inesperado"""
    # @formatter:off
    with (patch('soyyo.auxiliares.keyring.set_password'),
          patch('soyyo.auxiliares.keyring.get_password', return_value='otra_cosa')):
        # @formatter:on
        assert check_keyring() is False


def test_chek_keyring_devuelve_none():
    """Keyring escribe, pero devuelve otro valor inesperado"""
    # @formatter:off
    with (patch('soyyo.auxiliares.keyring.set_password'),
          patch('soyyo.auxiliares.keyring.get_password', return_value=None)):
        # @formatter:on
        assert check_keyring() is False


def test_chek_keyring_devuelve_cadena_vacia():
    """Keyring escribe, pero devuelve otro valor inesperado"""
    # @formatter:off
    with (patch('soyyo.auxiliares.keyring.set_password'),
          patch('soyyo.auxiliares.keyring.get_password', return_value='')):
        # @formatter:on
        assert check_keyring() is False


def test_chek_keyring_no_disponible():
    """No hay keyring en el sistema"""
    with patch('soyyo.auxiliares.keyring.set_password', side_effect=keyring_errors.NoKeyringError):
        assert check_keyring() is False


def test_chek_almacen_existe(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    assert check_almacen(fichero) is True


def test_chek_almacen_no_existe(tmp_path):
    fichero = tmp_path / 'datos.json'
    assert check_almacen(fichero) is False


@pytest.mark.parametrize('setup', [True, False])
def test_obtener_pin_pin_valido_salto_de_linea(setup):
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\n']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', setup)
    assert resultado == bytearray(b'12345678')


@pytest.mark.parametrize('setup', [True, False])
def test_obtener_pin_pin_valido_retorno_de_carro(setup):
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', setup)
    assert resultado == bytearray(b'12345678')


@pytest.mark.parametrize('setup', [True, False])
def test_obtener_pin_pin_valido_backspace(setup):
    teclas = [b'1', b'2', b'3', b'3', b'\x7f', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', setup)
    assert resultado == bytearray(b'12345678')


@pytest.mark.parametrize('setup', [True, False])
def test_obtener_pin_pin_valido_backspace_inicio(setup):
    teclas = [b'\x7f', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', setup)
    assert resultado == bytearray(b'12345678')


@pytest.mark.parametrize('setup', [True, False])
def test_obtener_pin_pin_valido_caracter_no_ascii(setup):
    teclas = [b'\xc3', b'\xa9',  # primer byte de 'é' y segundo byte de 'é'
              b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', setup)
    assert resultado == bytearray(b'12345678')


@pytest.mark.parametrize('setup, respuesta',
                         [(True, '\nEl PIN debe tener entre 8 y 20 cifras.\n'),
                          (False, '')])
def test_obtener_pin_pin_corto(capsys, setup, respuesta):
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'\r', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8',
              b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', setup)
        captured = capsys.readouterr()
    assert respuesta in captured.out
    assert resultado == bytearray(b'12345678')


@pytest.mark.parametrize('setup, respuesta',
                         [(True, '\nEl PIN debe tener entre 8 y 20 cifras.\n'),
                          (False, '')])
def test_obtener_pin_pin_vacio(capsys, setup, respuesta):
    teclas = [b'\r', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = obtener_pin('PIN: ', setup)
        captured = capsys.readouterr()
    assert respuesta in captured.out
    assert resultado == bytearray(b'12345678')


@pytest.mark.parametrize('setup, respuesta',
                         [(True, '\nEl PIN debe tener entre 8 y 20 cifras.\n'),
                          (False, '')])
def test_obtener_pin_pin_largo(capsys, setup, respuesta):
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
        resultado = obtener_pin('PIN: ', setup)
        captured = capsys.readouterr()
    assert respuesta in captured.out
    assert resultado == bytearray(b'12345678')


@pytest.mark.parametrize('setup', [True, False])
def test_obtener_pin_keyboard_interrupt(setup):
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=KeyboardInterrupt),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        with pytest.raises(KeyboardInterrupt):
            obtener_pin('PIN: ', setup)


@pytest.mark.parametrize('setup', [True, False])
def test_obtener_pin_keyboard_interrupt_caracter(setup):
    teclas = [b'\x03']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        with pytest.raises(KeyboardInterrupt):
            obtener_pin('PIN: ', setup)


@pytest.mark.parametrize('setup', [True, False])
def test_caracter_invalido_genera_bell(setup):
    teclas = [b'z', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0),
          patch('sys.stdout.write') as mock_write):
        # @formatter:on
        obtener_pin('PIN: ', setup)
        llamadas = [args[0] for args, kwargs in mock_write.call_args_list]
        assert '\x07' in llamadas


def test_validar_pin(almacen_valido):
    fichero, pepper = almacen_valido()
    pin = bytearray(b'12345678')
    with patch('soyyo.auxiliares.keyring.get_password', return_value=pepper):
        assert validar_pin(fichero, pin) is True


def test_validar_pin_erroneo(almacen_valido):
    fichero, pepper = almacen_valido()
    pin = bytearray(b'123456789')
    with patch('soyyo.auxiliares.keyring.get_password', return_value=pepper):
        assert validar_pin(fichero, pin) is False


def test_validar_pin_sin_pepper(almacen_valido):
    fichero, pepper = almacen_valido()
    pin = bytearray(b'12345678')
    with patch('soyyo.auxiliares.keyring.get_password', return_value=None):
        with pytest.raises(PepperNotFoundError):
            validar_pin(fichero, pin)


def test_validar_pin_error_JSON(almacen_valido):
    fichero, pepper = almacen_valido()
    pin = bytearray(b'12345678')
    # @formatter:off
    with (patch('soyyo.auxiliares.json.load', side_effect=json.JSONDecodeError('msg', 'doc', 0)),
          patch('soyyo.auxiliares.keyring.get_password', return_value=pepper)):
        # @formatter:on
        with pytest.raises(json.JSONDecodeError):
            validar_pin(fichero, pin)


def test_validar_pin_error_lectura_disco(almacen_valido):
    fichero, pepper = almacen_valido()
    pin = bytearray(b'12345678')
    with patch('soyyo.auxiliares.keyring.get_password', return_value=pepper):
        with pytest.raises(OSError):
            validar_pin(Path('/noexiste'), pin)


def test_guarda_json(almacen_valido):
    fichero, pepper = almacen_valido()
    with patch('soyyo.auxiliares.keyring.get_password', return_value=pepper):
        guardar_json(fichero, {})


def test_guarda_json_sin_pepper(almacen_valido):
    fichero, pepper = almacen_valido()
    with patch('soyyo.auxiliares.keyring.get_password', return_value=None):
        with pytest.raises(PepperNotFoundError):
            guardar_json(fichero, {})


def test_guarda_json_error_JSON(almacen_valido):
    fichero, pepper = almacen_valido()
    with (patch('soyyo.auxiliares.json.dumps', side_effect=json.JSONDecodeError('msg', 'doc', 0)),
          patch('soyyo.auxiliares.keyring.get_password', return_value=pepper)):
        with pytest.raises(json.JSONDecodeError):
            guardar_json(fichero, {})


def test_guarda_json_falla_escritura(almacen_valido):
    fichero, pepper = almacen_valido()
    with patch('soyyo.auxiliares.keyring.get_password', return_value=pepper):
        with pytest.raises(OSError):
            guardar_json(Path('/noexiste'), {})


def test_cargar_y_verificar_almacen(almacen_valido):
    fichero, pepper = almacen_valido()
    datos = json.loads(fichero.read_text(encoding='utf8'))
    del datos['firma']
    with patch('soyyo.auxiliares.keyring.get_password', return_value=pepper):
        assert cargar_y_verificar_almacen(fichero) == datos


def test_cargar_y_verificar_almacen_error_JSON(almacen_valido):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.auxiliares.json.dumps', side_effect=json.JSONDecodeError('msg', 'doc', 0)),
          patch('soyyo.auxiliares.keyring.get_password', return_value=pepper)):
        # @formatter:on
        with pytest.raises(json.JSONDecodeError):
            cargar_y_verificar_almacen(fichero)


def test_cargar_y_verificar_almacen_no_hay_firma(almacen_valido):
    fichero, pepper = almacen_valido(firmar='NO')
    with pytest.raises(FirmaInvalidaError):
        cargar_y_verificar_almacen(fichero)


def test_cargar_y_verificar_almacen_error_en_firma(almacen_valido):
    fichero, pepper = almacen_valido(firmar='fake')
    with patch('soyyo.auxiliares.keyring.get_password', return_value=pepper):
        with pytest.raises(FirmaInvalidaError):
            cargar_y_verificar_almacen(fichero)


def test_cargar_y_verificar_almacen_firma_manipulada(almacen_valido):
    fichero, pepper = almacen_valido(manipulado=True)
    with patch('soyyo.auxiliares.keyring.get_password', return_value=pepper):
        with pytest.raises(FirmaInvalidaError):
            cargar_y_verificar_almacen(fichero)


def test_cargar_y_verificar_almacen_firma_sin_pepper(almacen_valido):
    fichero, pepper = almacen_valido()
    with patch('soyyo.auxiliares.keyring.get_password', return_value=None):
        with pytest.raises(PepperNotFoundError):
            cargar_y_verificar_almacen(fichero)


def test_cargar_y_verificar_almacen_no_hay_fichero():
    with pytest.raises(OSError):
        cargar_y_verificar_almacen(Path('/no_existe'))


def test_autorizame_ok(almacen_valido):
    fichero, pepper = almacen_valido()
    pin = bytearray(b'12345678')
    # @formatter:off
    with (patch('soyyo.auxiliares.obtener_pin', return_value=pin),
          patch('soyyo.auxiliares.keyring.get_password',return_value=pepper)):
        # @formatter:on
        resultado = autorizame(fichero)
        assert resultado[0] is True
        assert resultado[1][1] == pin
        assert resultado[2] is None


def test_autorizame_bloqueo_temporal_finalizado(almacen_valido):
    fichero, pepper = almacen_valido(minutos_bloqueo=-10000)
    pin = bytearray(b'12345678')
    # @formatter:off
    with (patch('soyyo.auxiliares.obtener_pin', return_value=pin),
          patch('soyyo.auxiliares.keyring.get_password',return_value=pepper)):
        # @formatter:on
        resultado = autorizame(fichero)
        assert resultado[0] is True
        assert resultado[1][1] == pin
        assert resultado[2] is None


def test_autorizame_bloqueo_temporal(almacen_valido, caplog):
    fichero, pepper = almacen_valido(minutos_bloqueo=10000)
    pin = bytearray(b'12345678')
    # @formatter:off
    with (patch('soyyo.auxiliares.obtener_pin', return_value=pin),
          patch('soyyo.auxiliares.keyring.get_password',return_value=pepper),
          caplog.at_level(logging.INFO)):
        # @formatter:onº
        resultado = autorizame(fichero)
        mensajes = [r.message for r in caplog.records]
        assert resultado[0] is False
        assert resultado[1] is None
        assert resultado[2] == EstadoApp.SALIENDO_OK
        assert 'Aplicación en bloqueo temporal.' in mensajes[0]


def test_autorizame_bloqueo_permanente(almacen_valido, caplog):
    fichero, pepper = almacen_valido(num_bloqueos=10)
    pin = bytearray(b'12345678')
    # @formatter:off
    with (patch('soyyo.auxiliares.obtener_pin', return_value=pin),
          patch('soyyo.auxiliares.keyring.get_password',return_value=pepper),
          caplog.at_level(logging.INFO)):
        # @formatter:on
        resultado = autorizame(fichero)
        mensajes = [r.message for r in caplog.records]
        assert resultado[0] is False
        assert resultado[1] is None
        assert resultado[2] == EstadoApp.SALIENDO_OK
        assert 'Aplicación bloqueada.' in mensajes[0]


def test_autorizame_KeyboardInterrupt(almacen_valido, caplog):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.auxiliares.obtener_pin', side_effect=KeyboardInterrupt),
          patch('soyyo.auxiliares.keyring.get_password',return_value=pepper),
          caplog.at_level(logging.INFO)):
        # @formatter:on
        resultado = autorizame(fichero)
        mensajes = [r.message for r in caplog.records]
        assert resultado[0] is False
        assert resultado[1] is None
        assert resultado[2] == EstadoApp.SALIENDO_OK
        assert 'Cancelado por el usuario.' in mensajes[0]


# @formatter:off
@pytest.mark.parametrize('pins, intentos_fallidos',
                         [([bytearray(b'00000000'), bytearray(b'12345678')], 1), # falla 1, acierta
                          ([bytearray(b'00000000'), bytearray(b'00000000'), bytearray(b'12345678')], 2),  # falla 2, acierta
                          ([bytearray(b'00000000'), bytearray(b'00000000'), bytearray(b'00000000')], 3),  # falla 3 veces
                          ])
# @formatter:on
def test_autorizame_intentos(almacen_valido, caplog, pins, intentos_fallidos):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.auxiliares.obtener_pin', side_effect=pins),
          patch('soyyo.auxiliares.keyring.get_password', return_value=pepper),
          caplog.at_level(logging.INFO)):
        # @formatter:on
        autoriza, datos, estado = autorizame(fichero)
    assert caplog.text.count('PIN erróneo') == intentos_fallidos
    if intentos_fallidos == 3:
        assert autoriza is False
        assert estado == EstadoApp.SALIENDO_OK
    else:
        assert autoriza is True
        assert estado is None


def test_autorizame_firma_invalida(almacen_valido):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with patch('soyyo.auxiliares.cargar_y_verificar_almacen', side_effect=FirmaInvalidaError):
        # @formatter:on
        resultado = autorizame(fichero)
        assert resultado[0] is False
        assert resultado[1] is None
        assert resultado[2] == EstadoApp.FIRMA_INVALIDA


def test_autorizame_pepper_not_found(almacen_valido):
    fichero, pepper = almacen_valido()
    pin = bytearray(b'12345678')
    # @formatter:off
    with (patch('soyyo.auxiliares.obtener_pin', return_value=pin),
          patch('soyyo.auxiliares.keyring.get_password',return_value=None)):
        # @formatter:on
        resultado = autorizame(fichero)
        assert resultado[0] is False
        assert resultado[1] is None
        assert resultado[2] == EstadoApp.SIN_PEPPER


def test_autorizame_error_lectura_fichero_almacen(almacen_valido):
    fichero, pepper = almacen_valido()
    pin = bytearray(b'12345678')
    fichero = Path('/noexiste')
    # @formatter:off
    with (patch('soyyo.auxiliares.obtener_pin', return_value=pin),
          patch('soyyo.auxiliares.keyring.get_password',return_value=pepper)):
        # @formatter:on
        resultado = autorizame(fichero)
        assert resultado[0] is False
        assert resultado[1] is None
        assert resultado[2] == EstadoApp.FICHERO_CORRUPTO
