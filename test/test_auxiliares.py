"""
Tests del módulo auxiliares.py
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from unittest.mock import call, MagicMock, patch

import keyring.errors as keyring_errors
import pytest  # noqa

from soyyo.auxiliares import (autorizame, captura_teclado, cargar_y_verificar_almacen, check_almacen,
                              check_keyring, check_sistema, detectar_usb, guardar_json, muestra_tabla,
                              PuntoMontaje, reintentar_keyring, selecciona_ruta, validar_pin)
from soyyo.constantes import BaseTabla, EstadoApp
from soyyo.errores import AppError, FirmaInvalidaError, PepperNotFoundError
from .conftest import almacen_valido


def test_BaseTabla_OK_con_parametros():
    @dataclass
    class MiClass(BaseTabla):
        max_len: ClassVar[dict] = {}
        instancias: ClassVar[int] = 0
        campo1: str = ''
        campo2: str = ''
        campooo3: str = ''

    for _ in range(5):
        test = MiClass(campo1='valor_muy_largo', campo2='campo2', campooo3='campo3')

    assert MiClass.instancias == 5
    assert MiClass.max_len['campo1'] == len('valor_muy_largo')
    assert MiClass.max_len['campo2'] == len('campo2')
    assert MiClass.max_len['campooo3'] == len('campooo3')
    assert test.campo1 == 'valor_muy_largo'
    assert test.codigo == '5'


def test_BaseTabla_OK_sin_parametros():
    @dataclass
    class MiClass(BaseTabla):
        max_len: ClassVar[dict] = {}
        instancias: ClassVar[int] = 0
        campo1: str = ''
        campo2: str = ''

    test = MiClass()  # type: ignore

    assert test.campo1 == ''
    assert MiClass.instancias == 1


def test_usable_max_len():
    PuntoMontaje.instancias = 0
    PuntoMontaje.max_len = {}
    for _ in range(100):
        PuntoMontaje(ruta='/ruta/test', capacidad='100G')  # type: ignore
    assert PuntoMontaje.max_len['ruta'] == len('/ruta/test')
    assert PuntoMontaje.max_len['capacidad'] == len('capacidad')
    assert PuntoMontaje.instancias == 100


def test_usable_sin_parametros():
    PuntoMontaje.instancias = 0
    PuntoMontaje.max_len = {}
    PuntoMontaje()  # type: ignore
    assert PuntoMontaje.max_len.get('ruta') == 4
    assert PuntoMontaje.max_len.get('capacidad') == 9
    assert PuntoMontaje.instancias == 1


def test_usable_parametros_malos():
    with pytest.raises(TypeError):
        PuntoMontaje(parametro='malo')  # type: ignore


def test_reintentar_keyring_funciona():
    mock_func = MagicMock(return_value='password123')
    func_decorada = reintentar_keyring()(mock_func)  # type: ignore

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
    mock_func = MagicMock(side_effect=[Exception("InvalidObjectPath session error"), 'password123', ])
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


def test_check_sistema_todo_OK():
    with (patch('soyyo.auxiliares.sys.platform', new='linux'),
          patch('soyyo.auxiliares.sys.stdout.isatty', return_value=True)):
        assert check_sistema() is True


def test_check_sistema_error_SO():
    with (patch('soyyo.auxiliares.sys.platform', new='win32'),
          patch('soyyo.auxiliares.sys.stdout.isatty', return_value=True) as mock_funcion):
        assert check_sistema() is False
        mock_funcion.assert_not_called()


def test_check_sistema_error_terminal():
    with (patch('soyyo.auxiliares.sys.platform', new='linux'),
          patch('soyyo.auxiliares.sys.stdout.isatty', return_value=False) as mock_funcion,
          patch('soyyo.auxiliares.os.environ.get', return_value=None)):
        assert check_sistema() is False
        mock_funcion.assert_called_with()


def test_chek_keyring_funciona_bien():
    pepper_almacenado = {}  # actúa como keyring en memoria

    def _fake_set_password(servicio, usuario, valor):
        pepper_almacenado[(servicio, usuario)] = valor

    def _fake_get_password(servicio, usuario):
        return pepper_almacenado.get((servicio, usuario))

    with (patch('soyyo.auxiliares.keyring.set_password', side_effect=_fake_set_password),
          patch('soyyo.auxiliares.keyring.get_password', side_effect=_fake_get_password),
          patch('soyyo.auxiliares.keyring.delete_password')):
        assert check_keyring() is True


def test_chek_keyring_devuelve_cadena_incorrecta():
    """Keyring escribe, pero devuelve un valor inesperado"""
    # @formatter:off
    with (patch('soyyo.auxiliares.keyring.set_password'),
          patch('soyyo.auxiliares.keyring.get_password', return_value='otra_cosa'),
          patch('soyyo.auxiliares.keyring.delete_password')):
        # @formatter:on
        assert check_keyring() is False


def test_chek_keyring_devuelve_none():
    """Keyring escribe, pero devuelve otro valor inesperado"""
    # @formatter:off
    with (patch('soyyo.auxiliares.keyring.set_password'),
          patch('soyyo.auxiliares.keyring.get_password', return_value=None),
          patch('soyyo.auxiliares.keyring.delete_password')):
        # @formatter:on
        assert check_keyring() is False


def test_chek_keyring_devuelve_cadena_vacia():
    """Keyring escribe, pero devuelve otro valor inesperado"""
    # @formatter:off
    with (patch('soyyo.auxiliares.keyring.set_password'),
          patch('soyyo.auxiliares.keyring.get_password', return_value=''),
          patch('soyyo.auxiliares.keyring.delete_password')):
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


@pytest.mark.parametrize('una_tecla, setup, pin, dispara',
                         [(True, False, False, 'x'),
                          (False, True, False, 'x'),
                          (True, True, False, 'x'),
                          (False, False, True, 'x'),
                          (True, False, True, 'x'),
                          (False, True, True, 'x'),
                          (True, True, True, 'x'),
                          (True, True, False, ''),
                          (True, False, True, ''),
                          (False, True, True, ''),
                          (True, True, True, '')])
def test_captura_teclado_muchos_parametros(una_tecla, setup, pin, dispara):
    with pytest.raises(TypeError):
        captura_teclado(una_tecla=una_tecla, setup=setup, pin=pin, dispara=dispara)


def test_captura_teclado_dispara():
    teclas = [b'x', b'a']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = captura_teclado(dispara='x')
    assert resultado == bytearray(b'x')


@pytest.mark.parametrize('setup, pin',
                         [(False, False),
                          (True, False),
                          (False, True),
                          (False, False)])
def test_captura_teclado_pin_valido_salto_de_linea(setup, pin):
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\n']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = captura_teclado(setup=setup, pin=pin)
    assert resultado == bytearray(b'12345678')


@pytest.mark.parametrize('setup, pin',
                         [(False, False),
                          (True, False),
                          (False, True),
                          (False, False)])
def test_captura_teclado_pin_valido_retorno_de_carro(setup, pin):
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = captura_teclado(setup=setup, pin=pin)
    assert resultado == bytearray(b'12345678')


@pytest.mark.parametrize('una_tecla, setup, pin',
                         [(True, False, False),
                          (False, True, False),
                          (False, False, True),
                          (False, False, False)])
def test_captura_teclado_pin_valido_backspace(una_tecla, setup, pin):
    teclas = [b'1', b'2', b'3', b'3', b'\x7f', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = captura_teclado(una_tecla=una_tecla, setup=setup, pin=pin)
    if not una_tecla:
        assert resultado == bytearray(b'12345678')
    else:
        assert resultado == bytearray()


@pytest.mark.parametrize('una_tecla, setup, pin',
                         [(True, False, False),
                          (False, True, False),
                          (False, False, True),
                          (False, False, False)])
def test_captura_teclado_pin_valido_backspace_inicio(una_tecla, setup, pin):
    teclas = [b'\x7f', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = captura_teclado(una_tecla=una_tecla, setup=setup, pin=pin)
    if not una_tecla:
        assert resultado == bytearray(b'12345678')
    else:
        assert resultado == bytearray()


@pytest.mark.parametrize('una_tecla, setup, pin',
                         [(True, False, False),
                          (False, True, False),
                          (False, False, True),
                          (False, False, False)])
def test_captura_teclado_pin_valido_caracter_no_ascii(una_tecla, setup, pin):
    teclas = [b'\xc3', b'\xa9',  # primer byte de 'é' y segundo byte de 'é'
              b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = captura_teclado(una_tecla=una_tecla, setup=setup, pin=pin)
    if not una_tecla:
        assert resultado == bytearray(b'12345678')
    else:
        assert resultado == bytearray()


@pytest.mark.parametrize('setup, pin, respuesta',
                         [(True, False, 'El PIN debe tener entre 8 y 20 cifras'),
                          (False, True, ''),
                          (False, False, '')])
def test_captura_teclado_pin_corto(capsys, setup, pin, respuesta):
    teclas = [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'\r', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8',
              b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = captura_teclado(setup=setup, pin=pin)
        captured = capsys.readouterr()
    assert respuesta in captured.out
    if setup:
        assert resultado == bytearray(b'12345678')
    else:
        assert resultado == bytearray(b'1234567')


@pytest.mark.parametrize('setup, pin, respuesta',
                         [(True, False, 'El PIN debe tener entre 8 y 20 cifras'),
                          (False, True, ''),
                          (False, False, '')])
def test_captura_teclado_pin_vacio(capsys, setup, pin, respuesta):
    teclas = [b'\r', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        resultado = captura_teclado(setup=setup, pin=pin)
        captured = capsys.readouterr()
    assert respuesta in captured.out
    if setup:
        assert resultado == bytearray(b'12345678')
    else:
        assert resultado == bytearray(b'')


@pytest.mark.parametrize('setup, pin, respuesta',
                         [(True, False, 'El PIN debe tener entre 8 y 20 cifras'),
                          (False, False, ''), (False, False, '')])
def test_captura_teclado_pin_largo(capsys, setup, pin, respuesta):
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
        resultado = captura_teclado(setup=setup, pin=pin)
        captured = capsys.readouterr()
    assert respuesta in captured.out
    if setup:
        assert resultado == bytearray(b'12345678')
    else:
        assert resultado == bytearray(b'123456789012345678901234')


@pytest.mark.parametrize('una_tecla, setup, pin',
                         [(True, False, False),
                          (False, True, False),
                          (False, False, True),
                          (False, False, False)])
def test_captura_teclado_keyboard_interrupt(una_tecla, setup, pin):
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=KeyboardInterrupt),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        with pytest.raises(KeyboardInterrupt):
            captura_teclado(una_tecla=una_tecla, setup=setup, pin=pin)


@pytest.mark.parametrize('una_tecla, setup, pin',
                         [(True, False, False), (False, True, False), (False, False, True),
                          (False, False, False)])
def test_captura_teclado_keyboard_interrupt_caracter(una_tecla, setup, pin):
    teclas = [b'\x03']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0)):
        # @formatter:on
        if not una_tecla:
            with pytest.raises(KeyboardInterrupt):
                captura_teclado(una_tecla=una_tecla, setup=setup, pin=pin)
        else:
            data = captura_teclado(una_tecla=una_tecla, setup=setup, pin=pin)
            assert data == bytearray()


@pytest.mark.parametrize(',una_tecla, setup, pin',
                         [(True, False, False), (False, True, False), (False, False, True),
                          (False, False, False)])
def test_caracter_invalido_genera_bell(una_tecla, setup, pin):
    teclas = [b'z', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'\r']
    # @formatter:off
    with (patch('termios.tcgetattr', return_value=[]),
          patch('termios.tcsetattr'),
          patch('tty.setraw'),
          patch('sys.stdin.buffer.read', side_effect=teclas),
          patch('sys.stdin.fileno', return_value=0),
          patch('sys.stdout.write') as mock_write):
        # @formatter:on
        data = captura_teclado(una_tecla=una_tecla, setup=setup, pin=pin)
        llamadas = [args[0] for args, kwargs in mock_write.call_args_list]
        if not una_tecla:
            assert '\x07' in llamadas
        else:
            assert data == bytearray()


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
    with (patch('soyyo.auxiliares.captura_teclado', return_value=pin),
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
    with (patch('soyyo.auxiliares.captura_teclado', return_value=pin),
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
    with (patch('soyyo.auxiliares.captura_teclado', return_value=pin),
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
    with (patch('soyyo.auxiliares.captura_teclado', return_value=pin),
          patch('soyyo.auxiliares.keyring.get_password',return_value=pepper),
          caplog.at_level(logging.INFO)):
        # @formatter:on
        resultado = autorizame(fichero)
        mensajes = [r.message for r in caplog.records]
        assert resultado[0] is False
        assert resultado[1] is None
        assert resultado[2] == EstadoApp.SALIENDO_OK
        assert 'Aplicación bloqueada.' in mensajes[0]


# @formatter:off
@pytest.mark.parametrize('pins, intentos_fallidos',
                         [([KeyboardInterrupt], 0), # cancela,
                          ([bytearray(b'00000000'), KeyboardInterrupt], 1), # falla 1, cancela
                          ([bytearray(b'00000000'), bytearray(b'00000000'), KeyboardInterrupt], 2), # falla 2, cancela
                          ])
# @formatter:on
def test_autorizame_KeyboardInterrupt(almacen_valido, caplog, pins, intentos_fallidos):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.auxiliares.captura_teclado', side_effect=pins),
          patch('soyyo.auxiliares.keyring.get_password',return_value=pepper),
          caplog.at_level(logging.DEBUG)):
        # @formatter:on
        resultado = autorizame(fichero)
        with open(fichero, 'rb') as fin:
            datos = json.load(fin)
            mensajes = [r.message for r in caplog.records]
        if intentos_fallidos == 0:
            assert datos['intentos'] == 0
            assert datos['num_bloqueos'] == 0
            assert 'Cancelado por el usuario.' in mensajes[0]
        elif intentos_fallidos == 1:
            assert datos['intentos'] == 1
            assert datos['num_bloqueos'] == 0
            assert 'PIN erróneo, intento: 1 bloqueo: 0' in mensajes[0]
            assert 'Cancelado por el usuario.' in mensajes[1]
        elif intentos_fallidos == 2:
            assert datos['intentos'] == 2
            assert datos['num_bloqueos'] == 0
            assert resultado[0] is False
            assert resultado[1] is None
            assert resultado[2] == EstadoApp.SALIENDO_OK
            assert 'PIN erróneo, intento: 1 bloqueo: 0' in mensajes[0]
            assert 'PIN erróneo, intento: 2 bloqueo: 0' in mensajes[1]
            assert 'Cancelado por el usuario.' in mensajes[2]


# @formatter:off
@pytest.mark.parametrize('pins, intentos_fallidos',
                         [([bytearray(b'00000000'), bytearray(b'12345678')], 1), # falla 1, acierta
                          ([bytearray(b'00000000'), bytearray(b'00000000'), bytearray(b'12345678')], 2),  # falla 2, acierta
                          ([bytearray(b'00000000'), bytearray(b'00000000'), bytearray(b'00000000')], 3),  # falla 3 veces
                          ])
# @formatter:on
def test_autorizame_varios_intentos(almacen_valido, caplog, pins, intentos_fallidos):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.auxiliares.captura_teclado', side_effect=pins),
          patch('soyyo.auxiliares.keyring.get_password', return_value=pepper),
          caplog.at_level(logging.DEBUG)):
        # @formatter:on
        autoriza, datos, estado = autorizame(fichero)
    assert caplog.text.count('PIN erróneo') == intentos_fallidos
    if intentos_fallidos == 3:
        assert autoriza is False
        assert estado == EstadoApp.SALIENDO_OK
        with open(fichero, 'rb') as fin:
            datos = json.load(fin)
        assert datos['intentos'] == 0
        assert datos['num_bloqueos'] == 1
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
    with (patch('soyyo.auxiliares.captura_teclado', return_value=pin),
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
    with (patch('soyyo.auxiliares.captura_teclado', return_value=pin),
          patch('soyyo.auxiliares.keyring.get_password',return_value=pepper)):
        # @formatter:on
        resultado = autorizame(fichero)
        assert resultado[0] is False
        assert resultado[1] is None
        assert resultado[2] == EstadoApp.FICHERO_CORRUPTO


@pytest.mark.parametrize('inicio, fin, longitud',
                         [(0, 5, 1),
                          (0, 0, 1),
                          (5, 0, 1),
                          (None, None, 1),
                          (0, 5, 10),
                          (0, 0, 10),
                          (5, 0, 10),
                          (None, None, 10)])
def test_muestra_tabla(capsys, inicio, fin, longitud):
    lista = []
    for _ in range(longitud):
        lista.append(PuntoMontaje(ruta='/ruta/test', capacidad='100'))  # type: ignore
    muestra_tabla(lista, inicio, fin)
    captured = capsys.readouterr()

    lineas = captured.out.strip().split('\n')
    longitud_lineas = [len(l) for l in lineas]

    assert len(set(longitud_lineas)) == 1
    assert len(lineas) == len(lista[inicio: fin]) + 4
    assert 'Codigo' in captured.out
    assert 'Ruta' in captured.out
    assert 'Capacidad' in captured.out


def test_detectar_usb():
    mock_resultado = MagicMock(returncode=0,
                               stdout='{"blockdevices":[{"tran":"sata","mountpoint":null,"size":"11,1G",'
                                      '"rm":false,"fstype":null,"type":"disk","children":[{"tran":null,'
                                      '"mountpoint":"/ruta/valida/","size":"11,1G","rm":false,'
                                      '"fstype":"ext4","type":"part"}]},{"tran":"usb","mountpoint":null,'
                                      '"size":"2,2G","rm":true,"fstype":null,"type":"disk","children":[{'
                                      '"tran":null,"mountpoint":"/ruta/tambien/valida","size":"2,2G",'
                                      '"rm":true,"fstype":"vfat","type":"part"}]}]}')
    with (patch('soyyo.auxiliares.subprocess.run', return_value=mock_resultado),
          patch('soyyo.auxiliares.os.access', return_value=True)):
        resultado = detectar_usb()
        assert PuntoMontaje.instancias == len(resultado)
        resultado = detectar_usb()
        assert PuntoMontaje.instancias == len(resultado)
        resultado = detectar_usb()
        assert PuntoMontaje.instancias == len(resultado)


def test_detectar_usb_sin_rutas():
    mock_resultado = MagicMock(returncode=0, stdout='{"blockdevices": [{"children": []}]}')
    with (patch('soyyo.auxiliares.subprocess.run', return_value=mock_resultado),
          patch('soyyo.auxiliares.os.access', return_value=True)):
        resultado = detectar_usb()
        assert len(resultado) == 0


def test_detectar_usb_sin_dispositivos():
    mock_resultado = MagicMock(returncode=0, stdout='{"blockdevices":[]}')
    with (patch('soyyo.auxiliares.subprocess.run', return_value=mock_resultado),
          patch('soyyo.auxiliares.os.access', return_value=True)):
        resultado = detectar_usb()
        assert len(resultado) == 0


def test_detectar_usb_error():
    mock_resultado = MagicMock(returncode=1)
    with patch('soyyo.auxiliares.subprocess.run', return_value=mock_resultado):
        with pytest.raises(Exception):
            detectar_usb()


def test_muestra_tabla_lista_sin_dataclass():
    lista = []
    for _ in range(10):
        lista.append(_)
    with pytest.raises(AppError):
        muestra_tabla(lista, 0, 5)


def test_muestra_tabla_lista_vacia():
    lista = []
    with pytest.raises(AppError):
        muestra_tabla(lista, 0, 5)


def test_selecciona_ruta_sin_dispositivo():
    with patch('soyyo.auxiliares.detectar_usb', return_value=[]):
        resultado = selecciona_ruta()
        assert resultado == ''


def test_selecciona_ruta_seleccion_OK():
    with (patch('soyyo.auxiliares.detectar_usb', return_value=[1, 2, 3, 4, 5, 6, 7, 8]),
          patch('soyyo.auxiliares.muestra_tabla'),
          patch('soyyo.auxiliares.captura_teclado', side_effect=[b'22', b'5'])):
        resultado = selecciona_ruta()
        assert resultado == 5


def test_selecciona_ruta_mueve_paginas():
    funcion_mockeada = MagicMock()
    rutas = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
    with (patch('soyyo.auxiliares.detectar_usb', return_value=rutas),
          patch('soyyo.auxiliares.muestra_tabla', side_effect=funcion_mockeada),
          patch('soyyo.auxiliares.captura_teclado', side_effect=[b'S', b's', b's', b'a', b'A', b'c']),
          pytest.raises(KeyboardInterrupt)):
        selecciona_ruta()
    calls = [call(rutas, 0, 5), call(rutas, 5, 10), call(rutas, 10, 15), call(rutas, 10, 15),
             call(rutas, 5, 10), call(rutas, 0, 5)]
    funcion_mockeada.assert_has_calls(calls, any_order=True)


def test_selecciona_ruta_caracter_que_no_debe():
    funcion_mockeada = MagicMock()
    rutas = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
    with (patch('soyyo.auxiliares.detectar_usb', return_value=rutas),
          patch('soyyo.auxiliares.muestra_tabla', side_effect=funcion_mockeada),
          patch('soyyo.auxiliares.captura_teclado', side_effect=[b'z', b'c']),
          pytest.raises(KeyboardInterrupt)):
        selecciona_ruta()
    calls = [call(rutas, 0, 5), call(rutas, 0, 5)]
    funcion_mockeada.assert_has_calls(calls, any_order=True)


@pytest.mark.parametrize('caracter', [b'c', b'C'])
def test_selecciona_ruta_KeyboardInterrupt(caracter):
    with (patch('soyyo.auxiliares.detectar_usb', return_value=[1]),
          patch('soyyo.auxiliares.muestra_tabla'),
          patch('soyyo.auxiliares.captura_teclado', return_value=caracter),
          pytest.raises(KeyboardInterrupt)):
        selecciona_ruta()
