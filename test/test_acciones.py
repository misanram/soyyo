"""
Tests del módulo acciones.py
"""

import json
import locale
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import keyring.errors as keyring_errors
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent, QPaintEvent
from PySide6.QtWidgets import QApplication

from soyyo.acciones import captura, comprobar_estado, lista, reset, setup, VentanaCaptura
from soyyo.constantes import CURSORES, EstadoApp, Zona
from soyyo.errores import CapturaError
from .fixtures import almacen_valido

locale.setlocale(locale.LC_ALL, '')

ESTIRAR = 'estirar'
MAXIMO = 'maximo'
REDUCIR = 'reducir'
MINIMO = 'minimo'
SUBIR = 'subir'
BAJAR = 'bajar'
DERECHA = 'derecha'
IZQUIERDA = 'izquierda'


def test_comprobar_estado_llama_a_check_sistema(tmp_path):
    fichero = tmp_path / 'datos.json'
    with patch('soyyo.acciones.check_sistema', return_value=False) as mock_comprobar:
        respuesta = comprobar_estado(fichero)
        mock_comprobar.assert_called_with()
        assert respuesta == EstadoApp.SISTEMA_INCOMPATIBLE


def test_comprobar_estado_llama_a_check_keyring(tmp_path):
    fichero = tmp_path / 'datos.json'
    with (patch('soyyo.acciones.check_sistema', return_value=True),
          patch('soyyo.acciones.check_keyring', return_value=False) as mock_comprobar):
        respuesta = comprobar_estado(fichero)
        mock_comprobar.assert_called_with()
        assert respuesta == EstadoApp.SIN_KEYRING


def test_comprobar_estado_llama_a_check_almacen(tmp_path):
    fichero = tmp_path / 'datos.json'
    # @formatter:off
    with (patch('soyyo.acciones.check_sistema', return_value=True),
          patch('soyyo.acciones.check_keyring', return_value=True),
          patch('soyyo.acciones.check_almacen', return_value=False) as mock_comprobar):
        # @formatter:on
        respuesta = comprobar_estado(fichero)
        mock_comprobar.assert_called_with(fichero)
        assert respuesta == EstadoApp.PRIMER_ARRANQUE


def test_comprobar_estado_todo_ok(almacen_valido):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.acciones.check_sistema', return_value=True),
          patch('soyyo.acciones.check_keyring', return_value=True),
          patch('soyyo.acciones.check_almacen', return_value=True),
          patch('soyyo.acciones.keyring.get_password', return_value=pepper)):
        # @formatter:on
        respuesta = comprobar_estado(fichero)
    assert respuesta == EstadoApp.INICIALIZACION_CORRECTA


def test_comprobar_estado_sin_firma(almacen_valido):
    fichero, pepper = almacen_valido(firmar='NO')
    # @formatter:off
    with (patch('soyyo.acciones.check_sistema', return_value=True),
          patch('soyyo.acciones.check_keyring', return_value=True),
          patch('soyyo.acciones.check_almacen', return_value=True),
          patch('soyyo.acciones.keyring.get_password', return_value=pepper)):
        # @formatter:on
        respuesta = comprobar_estado(fichero)
    assert respuesta == EstadoApp.FIRMA_INVALIDA


def test_comprobar_estado_firma_mala(almacen_valido):
    fichero, pepper = almacen_valido(firmar='fake')
    # @formatter:off
    with (patch('soyyo.acciones.check_sistema', return_value=True),
          patch('soyyo.acciones.check_keyring', return_value=True),
          patch('soyyo.acciones.check_almacen', return_value=True),
          patch('soyyo.acciones.keyring.get_password', return_value=pepper)):
        # @formatter:on
        respuesta = comprobar_estado(fichero)
    assert respuesta == EstadoApp.FIRMA_INVALIDA


def test_comprobar_estado_bloqueo_temporal(almacen_valido, caplog):
    fichero, pepper = almacen_valido(minutos_bloqueo=10000)
    # @formatter:off
    with (patch('soyyo.acciones.check_sistema', return_value=True),
          patch('soyyo.acciones.check_keyring', return_value=True),
          patch('soyyo.acciones.check_almacen', return_value=True),
          patch('soyyo.acciones.keyring.get_password', return_value=pepper),
          caplog.at_level(logging.INFO)):
        # @formatter:on
        resultado = comprobar_estado(fichero)
    assert resultado == EstadoApp.SALIENDO_OK
    mensajes = [r.message for r in caplog.records]
    assert len(mensajes) == 1
    assert 'Aplicación bloqueada temporalmente.' in mensajes[0]


def test_comprobar_estado_bloqueo_temporal_solucionado(almacen_valido):
    fichero, pepper = almacen_valido(minutos_bloqueo=-10000)
    # @formatter:off
    with (patch('soyyo.acciones.check_sistema', return_value=True),
          patch('soyyo.acciones.check_keyring', return_value=True),
          patch('soyyo.acciones.check_almacen', return_value=True),
          patch('soyyo.acciones.keyring.get_password', return_value=pepper)):
        # @formatter:on
        resultado = comprobar_estado(fichero)
    assert resultado == EstadoApp.INICIALIZACION_CORRECTA


def test_comprobar_estado_bloqueo_permanente(almacen_valido, caplog):
    fichero, pepper = almacen_valido(num_bloqueos=10)
    # @formatter:off
    with (patch('soyyo.acciones.check_sistema', return_value=True),
          patch('soyyo.acciones.check_keyring', return_value=True),
          patch('soyyo.acciones.check_almacen', return_value=True),
          patch('soyyo.acciones.keyring.get_password', return_value=pepper),
          caplog.at_level(logging.INFO)):
        # @formatter:on
        resultado = comprobar_estado(fichero)
    assert resultado == EstadoApp.SALIENDO_OK
    mensajes = [r.message for r in caplog.records]
    assert len(mensajes) == 1
    assert 'Aplicación bloqueada permanentemente.' in mensajes[0]


def test_comprobar_estado_sin_pepper(almacen_valido):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.acciones.check_sistema', return_value=True),
          patch('soyyo.acciones.check_keyring', return_value=True),
          patch('soyyo.acciones.check_almacen', return_value=True),
          patch('soyyo.acciones.keyring.get_password', return_value=None)):
        # @formatter:on
        resultado = comprobar_estado(fichero)
    assert resultado == EstadoApp.SIN_PEPPER


def test_comprobar_estado_error_JSON(almacen_valido, caplog):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.acciones.check_sistema', return_value=True),
          patch('soyyo.acciones.check_keyring', return_value=True),
          patch('soyyo.acciones.check_almacen', return_value=True),
          patch('soyyo.acciones.keyring.get_password', return_value=pepper),
          patch('soyyo.auxiliares.json.load', side_effect=json.JSONDecodeError('msg', 'doc', 0)),
          caplog.at_level(logging.ERROR)):
        # @formatter:on
        resultado = comprobar_estado(fichero)
        mensajes = [r.message for r in caplog.records]
        assert len(mensajes) == 1
        assert 'Error al abrir el archivo JSON.' in mensajes[0]
    assert resultado == EstadoApp.FICHERO_CORRUPTO


def test_comprobar_estado_error_lectura_fichero(caplog):
    # @formatter:off
    with (patch('soyyo.acciones.check_sistema', return_value=True),
          patch('soyyo.acciones.check_keyring', return_value=True),
          patch('soyyo.acciones.check_almacen', return_value=True),
          patch('soyyo.acciones.check_almacen', return_value=True),
          caplog.at_level(logging.ERROR)):
        # @formatter:on
        resultado = comprobar_estado(Path('/noexiste'))
        mensajes = [r.message for r in caplog.records]
        assert len(mensajes) == 1
        assert 'Fallo al leer ' in mensajes[0]
    assert resultado == EstadoApp.FICHERO_CORRUPTO


def test_comprobar_estado_error_inesperado(almacen_valido, caplog):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.acciones.check_sistema', return_value=True),
          patch('soyyo.acciones.check_keyring', side_effect=Exception),
          caplog.at_level(logging.ERROR)):
        # @formatter:on
        with pytest.raises(Exception):
            comprobar_estado(fichero)
        mensajes = [r.message for r in caplog.records]
        assert len(mensajes) == 1
        assert 'Error indeterminado en el proceso de comprobar_estado.' in mensajes[0]


def test_reset_keyboard_interrupt(tmp_path):
    fichero = tmp_path / 'datos.json'
    with patch('soyyo.acciones.captura_teclado', side_effect=KeyboardInterrupt):
        assert reset(fichero) == EstadoApp.SALIENDO_OK


@pytest.mark.parametrize('respuesta', [b'N', b'n', b'C', b'c'])
def test_reset_NC(tmp_path, respuesta):
    fichero = tmp_path / 'datos.json'
    with patch('soyyo.acciones.captura_teclado', return_value=respuesta):
        assert reset(fichero) == EstadoApp.SALIENDO_OK


def test_reset_otro_caracter(tmp_path):
    fichero = tmp_path / 'datos.json'
    with patch('soyyo.acciones.captura_teclado', side_effect=[b'^', b'C']):
        assert reset(fichero) == EstadoApp.SALIENDO_OK


@pytest.mark.parametrize('respuesta', [b'S', b's'])
def test_reset_S(tmp_path, respuesta):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    # @formatter:off
    with (patch('soyyo.acciones.captura_teclado', return_value=respuesta),
          patch('soyyo.acciones.keyring.delete_password', return_value=None)):
        # @formatter:on
        respuesta = reset(fichero)
    assert respuesta == EstadoApp.SALIENDO_OK


def test_reset_S_keyring_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    # @formatter:off
    with (patch('soyyo.acciones.captura_teclado', return_value=b'S'),
          patch('soyyo.acciones.keyring.delete_password', side_effect=keyring_errors.PasswordDeleteError)):
        # @formatter:on
        respuesta = reset(fichero)
    assert respuesta == EstadoApp.SALIENDO_OK


def test_setup_sin_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    pepper_almacenado = {}  # actúa como keyring en memoria

    def _fake_set_password(servicio, usuario, valor):
        pepper_almacenado[(servicio, usuario)] = valor

    def _fake_get_password(servicio, usuario):
        return pepper_almacenado.get((servicio, usuario))

    with (patch('soyyo.acciones.keyring.set_password', side_effect=_fake_set_password),
          patch('soyyo.auxiliares.keyring.get_password', side_effect=_fake_get_password),
          patch('soyyo.acciones.selecciona_ruta', return_value='/unaruta/valida'),
          patch('soyyo.acciones.captura_teclado', return_value=bytearray(b'12345678'))):
        assert setup(fichero) == EstadoApp.SALIENDO_OK


def test_setup_sin_ruta(tmp_path):
    fichero = tmp_path / 'datos.json'
    with (patch('soyyo.acciones.captura_teclado', return_value=' '),
          patch('soyyo.acciones.selecciona_ruta', return_value=''), ):
        assert setup(fichero) == EstadoApp.SALIENDO_ERROR


def test_setup_ruta_KeyboardInterrupt(tmp_path):
    fichero = tmp_path / 'datos.json'
    with (patch('soyyo.acciones.captura_teclado', return_value=' '),
          patch('soyyo.acciones.selecciona_ruta', side_effect=KeyboardInterrupt), ):
        assert setup(fichero) == EstadoApp.SALIENDO_OK


def test_setup_kKeyboardInterrupt_pines_llave(tmp_path):
    fichero = tmp_path / 'datos.json'
    with (patch('soyyo.acciones.selecciona_ruta', return_value='/unaruta/valida'),
          patch('soyyo.acciones.captura_teclado',
                side_effect=[' ', KeyboardInterrupt, KeyboardInterrupt])):
        assert setup(fichero) == EstadoApp.SALIENDO_OK


def test_setup_kKeyboardInterrupt_pines(tmp_path):
    fichero = tmp_path / 'datos.json'
    with (patch('soyyo.acciones.selecciona_ruta', return_value='/unaruta/valida'),
          patch('soyyo.acciones.captura_teclado',
                side_effect=[' ', bytearray(b'12345678'), bytearray(b'12345678'), KeyboardInterrupt,
                             KeyboardInterrupt])):
        assert setup(fichero) == EstadoApp.SALIENDO_OK


def test_setup_pines_distintos(tmp_path, capsys):
    fichero = tmp_path / 'datos.json'
    pepper_almacenado = {}  # actúa como keyring en memoria

    def _fake_set_password(servicio, usuario, valor):
        pepper_almacenado[(servicio, usuario)] = valor

    def _fake_get_password(servicio, usuario):
        return pepper_almacenado.get((servicio, usuario))

    # @formatter:off
    with (patch('soyyo.acciones.keyring.set_password', side_effect=_fake_set_password),
          patch('soyyo.auxiliares.keyring.get_password', side_effect=_fake_get_password),
          patch('soyyo.acciones.selecciona_ruta', return_value='/unaruta/valida'),
          patch('soyyo.acciones.captura_teclado', side_effect=[bytearray(b'0'),
                                                               bytearray(b'12345678'), bytearray(b'12345679'),
                                                               bytearray(b'12345678'), bytearray(b'12345678'),
                                                               bytearray(b'12345678'), bytearray(b'12345679'),
                                                               bytearray(b'12345678'), bytearray(b'12345678'),
                                                               ])):
        # @formatter:on
        setup(fichero)
        captured = capsys.readouterr()
    assert 'Ambos valores deben ser iguales' in captured.out


def test_setup_set_keyring_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    # @formatter:off
    with (patch('soyyo.acciones.selecciona_ruta', return_value='/unaruta/valida'),
          patch('soyyo.acciones.captura_teclado', return_value=bytearray(b'12345678')),
          patch('soyyo.acciones.keyring.set_password', side_effect=keyring_errors.PasswordSetError)):
        # @formatter:on
        assert setup(fichero) == EstadoApp.SALIENDO_ERROR


def test_setup_file_write_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    # @formatter:off
    with (patch('soyyo.acciones.guardar_json', side_effect=OSError),
          patch('soyyo.acciones.captura_teclado', return_value=bytearray(b'12345678'))):
        # @formatter:on
        assert setup(fichero) == EstadoApp.SALIENDO_ERROR


def test_setup_delete_password_keyring_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    pepper_almacenado = {}  # actúa como keyring en memoria

    def _fake_set_password(servicio, usuario, valor):
        pepper_almacenado[(servicio, usuario)] = valor

    def _fake_get_password(servicio, usuario):
        return pepper_almacenado.get((servicio, usuario))

    # @formatter:off
    with (patch('soyyo.acciones.guardar_json', side_effect=OSError),
          patch('soyyo.acciones.keyring.set_password', side_effect=_fake_set_password),
          patch('soyyo.auxiliares.keyring.get_password', side_effect=_fake_get_password),
          patch('soyyo.acciones.captura_teclado', return_value=bytearray(b'12345678')),
          patch('soyyo.acciones.keyring.delete_password', side_effect=keyring_errors.PasswordDeleteError)):
        # @formatter:on
        assert setup(fichero) == EstadoApp.SALIENDO_ERROR


def test_setup_error_inesperado(almacen_valido, caplog):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.acciones.captura_teclado', side_effect=Exception),
          caplog.at_level(logging.ERROR)):
        # @formatter:on
        with pytest.raises(Exception):
            setup(fichero)
        mensajes = [r.message for r in caplog.records]
        assert len(mensajes) == 1
        assert 'Error indeterminado en el proceso de setup.' in mensajes[0]


def test_ventana_captura_inicial(qtbot):
    ventana = VentanaCaptura(300, 300)
    qtbot.addWidget(ventana)
    assert ventana.imagen is None
    assert ventana.width() == 300
    assert ventana.height() == 300


# @formatter:off
@pytest.mark.parametrize('pos, zona_esperada',
                         [(QPoint(4, 4), Zona.ESQUINA_SUPERIOR_IZQUIERDA),
                          (QPoint(296, 4), Zona.ESQUINA_SUPERIOR_DERECHA),
                          (QPoint(4, 296), Zona.ESQUINA_INFERIOR_IZQUIERDA),
                          (QPoint(296, 296), Zona.ESQUINA_INFERIOR_DERECHA),
                          (QPoint(150, 4), Zona.BORDE_SUPERIOR),
                          (QPoint(150, 296), Zona.BORDE_INFERIOR),
                          (QPoint(4, 150), Zona.BORDE_IZQUIERDO),
                          (QPoint(296, 150), Zona.BORDE_DERECHO),
                          (QPoint(150, 20), Zona.BARRA),
                          (QPoint(150, 150), Zona.INTERIOR),
                          ])
# @formatter:on
def test_ventana_captura_zona_actual(qtbot, pos, zona_esperada):
    ventana = VentanaCaptura(300, 300)
    qtbot.addWidget(ventana)
    assert ventana._zona_actual(pos) == zona_esperada


def test_ventana_captura_zona_actual_none(qtbot):
    ventana = VentanaCaptura(300, 300)
    qtbot.addWidget(ventana)
    with pytest.raises(ValueError):
        ventana._zona_actual(None)


def test_ventana_captura_capturar(qtbot):
    ventana = VentanaCaptura(300, 300)
    qtbot.addWidget(ventana)
    with patch('soyyo.acciones.ImageGrab.grab', return_value='imagen_falsa'):
        ventana._capturar()
    assert ventana.imagen == 'imagen_falsa'


def test_ventana_captura_capturar_error(qtbot):
    ventana = VentanaCaptura(300, 300)
    qtbot.addWidget(ventana)
    with patch('soyyo.acciones.ImageGrab.grab', side_effect=OSError('Falló la captura de imagen.')):
        ventana._capturar()
    assert ventana.error is not None
    assert isinstance(ventana.error, CapturaError)


def test_ventana_captura_mouse_press(qtbot):
    ventana = VentanaCaptura(300, 300)
    qtbot.addWidget(ventana)
    qtbot.mousePress(ventana, Qt.MouseButton.LeftButton, pos=QPoint(150, 150))
    assert ventana._clic_pos == QPoint(150, 150)
    assert ventana._zona_activa == Zona.INTERIOR
    assert ventana._ancho_original == 300
    assert ventana._alto_original == 300


# @formatter:off
@pytest.mark.parametrize('origen, arrastre, accion',
                         [(QPoint(4, 4), QPoint(-100, -100), (Zona.ESQUINA_SUPERIOR_IZQUIERDA, ESTIRAR)),
                          (QPoint(4, 4), QPoint(-10000, -10000), (Zona.ESQUINA_SUPERIOR_IZQUIERDA, MAXIMO)),
                          (QPoint(4, 4), QPoint(100, 100), (Zona.ESQUINA_SUPERIOR_IZQUIERDA, REDUCIR)),
                          (QPoint(4, 4), QPoint(10000, 10000), (Zona.ESQUINA_SUPERIOR_IZQUIERDA, MINIMO)),
                          (QPoint(396, 4), QPoint(100, -100), (Zona.ESQUINA_SUPERIOR_DERECHA, ESTIRAR)),
                          (QPoint(396, 4), QPoint(10000, -10000), (Zona.ESQUINA_SUPERIOR_DERECHA, MAXIMO)),
                          (QPoint(396, 4), QPoint(-100, 100), (Zona.ESQUINA_SUPERIOR_DERECHA, REDUCIR)),
                          (QPoint(396, 4), QPoint(-10000, 10000), (Zona.ESQUINA_SUPERIOR_DERECHA, MINIMO)),
                          (QPoint(4, 296), QPoint(-100, 100), (Zona.ESQUINA_INFERIOR_IZQUIERDA, ESTIRAR)),
                          (QPoint(4, 296), QPoint(-10000, 10000), (Zona.ESQUINA_INFERIOR_IZQUIERDA, MAXIMO)),
                          (QPoint(4, 296), QPoint(100, -100), (Zona.ESQUINA_INFERIOR_IZQUIERDA, REDUCIR)),
                          (QPoint(4, 296), QPoint(10000, -10000), (Zona.ESQUINA_INFERIOR_IZQUIERDA, MINIMO)),
                          (QPoint(396, 296), QPoint(100, 100), (Zona.ESQUINA_INFERIOR_DERECHA, ESTIRAR)),
                          (QPoint(396, 296), QPoint(10000, 10000), (Zona.ESQUINA_INFERIOR_DERECHA, MAXIMO)),
                          (QPoint(396, 296), QPoint(-100, -100), (Zona.ESQUINA_INFERIOR_DERECHA, REDUCIR)),
                          (QPoint(396, 296), QPoint(-10000, -10000), (Zona.ESQUINA_INFERIOR_DERECHA, MINIMO)),
                          (QPoint(150, 4), QPoint(0, -100), (Zona.BORDE_SUPERIOR, ESTIRAR)),
                          (QPoint(150, 4), QPoint(0, -10000), (Zona.BORDE_SUPERIOR, MAXIMO)),
                          (QPoint(150, 4), QPoint(0, 100), (Zona.BORDE_SUPERIOR, REDUCIR)),
                          (QPoint(150, 4), QPoint(0, 10000), (Zona.BORDE_SUPERIOR, MINIMO)),
                          (QPoint(150, 296), QPoint(0, 100), (Zona.BORDE_INFERIOR, ESTIRAR)),
                          (QPoint(150, 296), QPoint(0, 10000), (Zona.BORDE_INFERIOR, MAXIMO)),
                          (QPoint(150, 296), QPoint(0, -100), (Zona.BORDE_INFERIOR, REDUCIR)),
                          (QPoint(150, 296), QPoint(0, -10000), (Zona.BORDE_INFERIOR, MINIMO)),
                          (QPoint(4, 150), QPoint(-100, 0), (Zona.BORDE_IZQUIERDO, ESTIRAR)),
                          (QPoint(4, 150), QPoint(-10000, 0), (Zona.BORDE_IZQUIERDO, MAXIMO)),
                          (QPoint(4, 150), QPoint(100, 0), (Zona.BORDE_IZQUIERDO, REDUCIR)),
                          (QPoint(4, 150), QPoint(10000, 0), (Zona.BORDE_IZQUIERDO, MINIMO)),
                          (QPoint(396, 150), QPoint(100, 0), (Zona.BORDE_DERECHO, ESTIRAR)),
                          (QPoint(396, 150), QPoint(10000, 0), (Zona.BORDE_DERECHO, MAXIMO)),
                          (QPoint(396, 150), QPoint(-100, 0), (Zona.BORDE_DERECHO, REDUCIR)),
                          (QPoint(396, 150), QPoint(-10000, 0), (Zona.BORDE_DERECHO, MINIMO)),
                          (QPoint(200, 20), QPoint(0, -100), (Zona.BARRA, SUBIR)),
                          (QPoint(200, 20), QPoint(0, 100), (Zona.BARRA, BAJAR)),
                          (QPoint(200, 20), QPoint(-100, 0), (Zona.BARRA, IZQUIERDA)),
                          (QPoint(200, 20), QPoint(100, 0), (Zona.BARRA, DERECHA)),
                          (QPoint(200, 150), QPoint(4, 4), Zona.INTERIOR), ])
# @formatter:on
def test_ventana_captura_mouse_move(qtbot, origen, arrastre, accion):
    with patch.object(QApplication, 'primaryScreen') as mock_screen:
        ancho_pantalla = 1920
        alto_pantalla = 1080
        ancho_ventana = 400
        alto_ventana = 300
        posicion_ventana_x = 410
        posicion_ventana_y = 410

        mock_screen.return_value.availableGeometry.return_value = QRect(0, 0, ancho_pantalla, alto_pantalla)
        ventana = VentanaCaptura(ancho_ventana, alto_ventana)
        qtbot.addWidget(ventana)
        ventana.move(posicion_ventana_x, posicion_ventana_y)
        qtbot.mousePress(ventana, Qt.MouseButton.LeftButton, pos=origen)

        ventana._clic_pos = origen
        ventana._zona_activa = ventana._zona_actual(origen)
        ventana._ancho_original = ventana.width()
        ventana._alto_original = ventana.height()
        x_ventana = ventana.pos().x()
        y_ventana = ventana.pos().y()

        global_pos = QPointF(ventana.mapToGlobal(QPoint(origen + arrastre)))
        event = QMouseEvent(QEvent.Type.MouseMove,
                            QPointF(origen + arrastre),
                            QPointF(global_pos),
                            Qt.MouseButton.LeftButton,
                            Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier)
        ventana.mouseMoveEvent(event)

        if accion == (Zona.ESQUINA_SUPERIOR_IZQUIERDA, ESTIRAR):
            assert ventana.height() == alto_ventana - arrastre.y()
            assert ventana.width() == ancho_ventana - arrastre.x()
        elif accion == (Zona.ESQUINA_SUPERIOR_IZQUIERDA, MAXIMO):
            assert ventana.height() == y_ventana + alto_ventana
            assert ventana.width() == x_ventana + ancho_ventana
        elif accion == (Zona.ESQUINA_SUPERIOR_IZQUIERDA, REDUCIR):
            assert ventana.height() == alto_ventana - arrastre.y()
            assert ventana.width() == ancho_ventana - arrastre.x()
        elif accion == (Zona.ESQUINA_SUPERIOR_IZQUIERDA, MINIMO):
            assert ventana.height() == ventana.minimumHeight()
            assert ventana.width() == ventana.minimumWidth()
        elif accion == (Zona.ESQUINA_SUPERIOR_DERECHA, ESTIRAR):
            assert ventana.height() == alto_ventana - arrastre.y()
            assert ventana.width() == ancho_ventana + arrastre.x()
        elif accion == (Zona.ESQUINA_SUPERIOR_DERECHA, MAXIMO):
            assert ventana.height() == y_ventana + alto_ventana
            assert ventana.width() == ancho_pantalla - x_ventana
        elif accion == (Zona.ESQUINA_SUPERIOR_DERECHA, REDUCIR):
            assert ventana.height() == alto_ventana - arrastre.y()
            assert ventana.width() == ancho_ventana + arrastre.x()
        elif accion == (Zona.ESQUINA_SUPERIOR_DERECHA, MINIMO):
            assert ventana.height() == ventana.minimumHeight()
            assert ventana.width() == ventana.minimumWidth()
        elif accion == (Zona.ESQUINA_INFERIOR_IZQUIERDA, ESTIRAR):
            assert ventana.height() == alto_ventana + arrastre.y()
            assert ventana.width() == ancho_ventana - arrastre.x()
        elif accion == (Zona.ESQUINA_INFERIOR_IZQUIERDA, MAXIMO):
            assert ventana.height() == alto_pantalla - y_ventana
            assert ventana.width() == x_ventana + ancho_ventana
        elif accion == (Zona.ESQUINA_INFERIOR_IZQUIERDA, REDUCIR):
            assert ventana.height() == alto_ventana + arrastre.y()
            assert ventana.width() == ancho_ventana - arrastre.x()
        elif accion == (Zona.ESQUINA_INFERIOR_IZQUIERDA, MINIMO):
            assert ventana.height() == ventana.minimumHeight()
            assert ventana.width() == ventana.minimumWidth()
        elif accion == (Zona.ESQUINA_INFERIOR_DERECHA, ESTIRAR):
            assert ventana.height() == alto_ventana + arrastre.y()
            assert ventana.width() == ancho_ventana + arrastre.x()
        elif accion == (Zona.ESQUINA_INFERIOR_DERECHA, MAXIMO):
            assert ventana.height() == alto_pantalla - y_ventana
            assert ventana.width() == ancho_pantalla - x_ventana
        elif accion == (Zona.ESQUINA_INFERIOR_DERECHA, REDUCIR):
            assert ventana.height() == alto_ventana + arrastre.y()
            assert ventana.width() == ancho_ventana + arrastre.x()
        elif accion == (Zona.ESQUINA_INFERIOR_DERECHA, MINIMO):
            assert ventana.height() == ventana.minimumHeight()
            assert ventana.width() == ventana.minimumWidth()
        elif accion == (Zona.BORDE_SUPERIOR, ESTIRAR):
            assert ventana.height() == alto_ventana - arrastre.y()
        elif accion == (Zona.BORDE_SUPERIOR, MAXIMO):
            assert ventana.height() == y_ventana + alto_ventana
        elif accion == (Zona.BORDE_SUPERIOR, REDUCIR):
            assert ventana.height() == alto_ventana - arrastre.y()
        elif accion == (Zona.BORDE_SUPERIOR, MINIMO):
            assert ventana.height() == ventana.minimumHeight()
        elif accion == (Zona.BORDE_INFERIOR, ESTIRAR):
            assert ventana.height() == alto_ventana + arrastre.y()
        elif accion == (Zona.BORDE_INFERIOR, MAXIMO):
            assert ventana.height() == alto_pantalla - y_ventana
        elif accion == (Zona.BORDE_INFERIOR, REDUCIR):
            assert ventana.height() == alto_ventana + arrastre.y()
        elif accion == (Zona.BORDE_INFERIOR, MINIMO):
            assert ventana.height() == ventana.minimumHeight()
        elif accion == (Zona.BORDE_IZQUIERDO, ESTIRAR):
            assert ventana.width() == ancho_ventana - arrastre.x()
        elif accion == (Zona.BORDE_IZQUIERDO, MAXIMO):
            assert ventana.width() == x_ventana + ancho_ventana
        elif accion == (Zona.BORDE_IZQUIERDO, REDUCIR):
            assert ventana.width() == ancho_ventana - arrastre.x()
        elif accion == (Zona.BORDE_IZQUIERDO, MINIMO):
            assert ventana.width() == ventana.minimumWidth()
        elif accion == (Zona.BORDE_DERECHO, ESTIRAR):
            assert ventana.width() == ancho_ventana + arrastre.x()
        elif accion == (Zona.BORDE_DERECHO, MAXIMO):
            assert ventana.width() == ancho_pantalla - x_ventana
        elif accion == (Zona.BORDE_DERECHO, REDUCIR):
            assert ventana.width() == ancho_ventana + arrastre.x()
        elif accion == (Zona.BORDE_DERECHO, MINIMO):
            assert ventana.width() == ventana.minimumWidth()
        elif accion == (Zona.BARRA, SUBIR) or accion == (Zona.BARRA, BAJAR):
            assert ventana.pos().x() == posicion_ventana_x
            assert ventana.pos().y() == posicion_ventana_y + arrastre.y()
            assert ventana.height() == alto_ventana
            assert ventana.width() == ancho_ventana
        elif accion == (Zona.BARRA, IZQUIERDA) or accion == (Zona.BARRA, DERECHA):
            assert ventana.pos().x() == posicion_ventana_x + arrastre.x()
            assert ventana.pos().y() == posicion_ventana_y
            assert ventana.height() == alto_ventana
            assert ventana.width() == ancho_ventana
        elif accion == Zona.INTERIOR:
            assert ventana.pos().x() == posicion_ventana_x
            assert ventana.pos().y() == posicion_ventana_y
            assert ventana.height() == alto_ventana
            assert ventana.width() == ancho_ventana


# @formatter:off
@pytest.mark.parametrize('pos, zona',
                         [(QPoint(150, 150), Zona.INTERIOR),
                          (QPoint(4, 4), Zona.ESQUINA_SUPERIOR_IZQUIERDA),
                          (QPoint(296, 4), Zona.ESQUINA_SUPERIOR_DERECHA),
                          (QPoint(4, 296), Zona.ESQUINA_INFERIOR_IZQUIERDA),
                          (QPoint(296, 296), Zona.ESQUINA_INFERIOR_DERECHA),
                          (QPoint(150, 4), Zona.BORDE_SUPERIOR),
                          (QPoint(150, 296), Zona.BORDE_INFERIOR),
                          (QPoint(4, 150), Zona.BORDE_IZQUIERDO),
                          (QPoint(296, 150), Zona.BORDE_DERECHO),
                          (QPoint(150, 20), Zona.BARRA), ])
# @formatter:on
def test_ventana_captura_mouse_move_cursor(qtbot, pos, zona):
    ventana = VentanaCaptura(300, 300)
    qtbot.addWidget(ventana)
    global_pos = QPointF(ventana.mapToGlobal(QPoint(pos)))
    event = QMouseEvent(QEvent.Type.MouseMove,
                        QPointF(pos),
                        global_pos,
                        Qt.MouseButton.NoButton,
                        Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier)
    ventana.mouseMoveEvent(event)
    assert ventana.cursor().shape() == CURSORES[zona]


def test_ventana_captura_mouse_release(qtbot):
    ventana = VentanaCaptura(300, 300)
    qtbot.addWidget(ventana)
    ventana._clic_pos = QPoint(150, 150)
    ventana._zona_activa = Zona.INTERIOR
    qtbot.mouseRelease(ventana, Qt.MouseButton.LeftButton)
    assert ventana._clic_pos is None
    assert ventana._zona_activa is None


def test_ventana_captura_paint_event(qtbot):
    ventana = VentanaCaptura(400, 300)
    qtbot.addWidget(ventana)
    event = QPaintEvent(QRect(0, 0, 400, 300))
    ventana.paintEvent(event)  # no lanza excepción


def test_captura_funciona_bien(almacen_valido):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with patch('soyyo.acciones.VentanaCaptura') as mock_ventana:
        mock_ventana.return_value.imagen = MagicMock()
        mock_ventana.return_value.error = False
        mock_decoded = MagicMock()
        mock_decoded.data = b'otpauth://totp/Example:alice@google.com?secret=JBSWY3DPEHPK3PXP'
        with (patch('soyyo.acciones.QApplication'),
              patch('soyyo.auxiliares.captura_teclado', return_value=bytearray(b'12345678')),
              patch('soyyo.auxiliares.keyring.get_password', return_value=pepper),
              patch('soyyo.acciones.keyring.get_password', return_value=pepper),
              patch('soyyo.acciones.decode', return_value=[mock_decoded])):
            # @formatter:on
            resultado = captura(fichero)
    assert resultado == EstadoApp.SALIENDO_OK


def test_captura_no_autoriza(tmp_path):
    # @formatter:off
    with (patch('soyyo.acciones.QApplication'),
          patch('soyyo.acciones.VentanaCaptura') as mock_ventana,
          patch('soyyo.acciones.autorizame', return_value=(False, (None, bytearray(b'')), EstadoApp.SIN_PEPPER))):
        # @formatter:on
        mock_ventana.return_value.imagen = None
        mock_ventana.return_value.error = False
        fichero = tmp_path / 'datos.json'
        resultado = captura(fichero)
    assert resultado == EstadoApp.SIN_PEPPER


def test_captura_sin_imagen(tmp_path):
    # @formatter:off
    with (patch('soyyo.acciones.QApplication'),
          patch('soyyo.acciones.VentanaCaptura') as mock_ventana,
          patch('soyyo.acciones.decode', return_value=[]),
          patch('soyyo.acciones.autorizame', return_value=(True, (None, bytearray(b'')), None))):
        # @formatter:on
        mock_ventana.return_value.imagen = None
        mock_ventana.return_value.error = False
        fichero = tmp_path / 'datos.json'
        resultado = captura(fichero)
    assert resultado == EstadoApp.SALIENDO_ERROR


def test_captura_imagen_error(tmp_path, caplog):
    # @formatter:off
    with (patch('soyyo.acciones.QApplication'),
          patch('soyyo.acciones.VentanaCaptura') as mock_ventana,
          patch('soyyo.acciones.decode', return_value=[]),
          caplog.at_level(logging.ERROR)):
        # @formatter:on
        mock_ventana.return_value.imagen = None
        mock_ventana.return_value.error = CapturaError('Error misterioso durante la captura.', (), OSError())
        fichero = tmp_path / 'datos.json'
        assert captura(fichero) == EstadoApp.SALIENDO_ERROR
        mensajes = [r.message for r in caplog.records]
        assert len(mensajes) == 1


def test_captura_imagen_sin_qr(tmp_path):
    # @formatter:off
    with (patch('soyyo.acciones.QApplication'),
          patch('soyyo.acciones.VentanaCaptura') as mock_ventana,
          patch('soyyo.acciones.decode', return_value=[]),
          patch('soyyo.acciones.autorizame', return_value=(True, (None, bytearray(b'')), None))):
        # @formatter:on
        mock_ventana.return_value.imagen = 'imagen_falsa'
        mock_ventana.return_value.error = False
        fichero = tmp_path / 'datos.json'
        resultado = captura(fichero)
    assert resultado == EstadoApp.SALIENDO_ERROR


def test_captura_sin_pepper(almacen_valido):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with patch('soyyo.acciones.VentanaCaptura') as mock_ventana:
        mock_ventana.return_value.imagen = MagicMock()
        mock_ventana.return_value.error = False
        mock_decoded = MagicMock()
        mock_decoded.data = b'otpauth://totp/Example:alice@google.com?secret=JBSWY3DPEHPK3PXP'
        with (patch('soyyo.acciones.QApplication'),
              patch('soyyo.acciones.autorizame', return_value=(True, (None, bytearray(b'')), None)),
              patch('soyyo.acciones.decode', return_value=[mock_decoded]),
              patch('soyyo.acciones.keyring.get_password', return_value=None)):
            # @formatter:on
            resultado = captura(fichero)
    assert resultado == EstadoApp.SALIENDO_ERROR


def test_captura_error_escritura_fichero(almacen_valido, caplog):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with patch('soyyo.acciones.VentanaCaptura') as mock_ventana:
        mock_ventana.return_value.imagen = MagicMock()
        mock_ventana.return_value.error = False
        mock_decoded = MagicMock()
        mock_decoded.data = b'otpauth://totp/Example:alice@google.com?secret=JBSWY3DPEHPK3PXP'
        with (patch('soyyo.acciones.QApplication'),
              patch('soyyo.auxiliares.captura_teclado', return_value=bytearray(b'12345678')),
              patch('soyyo.auxiliares.keyring.get_password', return_value=pepper),
              patch('soyyo.acciones.keyring.get_password', return_value=pepper),
              patch('soyyo.acciones.decode', return_value=[mock_decoded]),
              patch('soyyo.acciones.guardar_json', side_effect=OSError),
              caplog.at_level(logging.ERROR)):
            # @formatter:on
            resultado = captura(fichero)
    assert resultado == EstadoApp.SALIENDO_ERROR
    mensajes = [r.message for r in caplog.records]
    assert len(mensajes) == 1
    assert 'Error de escritura.' in mensajes[0]


def test_captura_error_inesperado(almacen_valido, caplog):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.acciones.QApplication', side_effect=Exception),
          caplog.at_level(logging.ERROR)):
        # @formatter:on
        with pytest.raises(Exception):
            captura(fichero)
        mensajes = [r.message for r in caplog.records]
        assert len(mensajes) == 1
        assert 'Error indeterminado en el proceso de captura.' in mensajes[0]


def test_lista_funciona_bien_sin_totps(almacen_valido):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.auxiliares.captura_teclado', return_value=bytearray(b'12345678')),
          patch('soyyo.auxiliares.keyring.get_password', return_value=pepper),
          patch('soyyo.acciones.keyring.get_password', return_value=pepper)):
        # @formatter:on
        resultado = lista(fichero)
    assert resultado == EstadoApp.SALIENDO_OK


def test_lista_funciona_bien_con_totps(almacen_valido):
    fichero, pepper = almacen_valido(totps=True)
    # @formatter:off
    with (patch('soyyo.auxiliares.captura_teclado', return_value=bytearray(b'12345678')),
          patch('soyyo.auxiliares.keyring.get_password', return_value=pepper),
          patch('soyyo.acciones.keyring.get_password', return_value=pepper),
          patch('soyyo.acciones.Fernet.decrypt', return_value=b'{"nombre": "Nombre"}'), ):
        # @formatter:on
        resultado = lista(fichero)
    assert resultado == EstadoApp.SALIENDO_OK


def test_lista_no_autoriza(tmp_path):
    # @formatter:off
    with patch('soyyo.acciones.autorizame', return_value=(False,  (None, bytearray(b'')), EstadoApp.SIN_PEPPER)):
        # @formatter:on
        fichero = tmp_path / 'datos.json'
        resultado = lista(fichero)
    assert resultado == EstadoApp.SIN_PEPPER


def test_lista_sin_pepper(almacen_valido):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.acciones.autorizame', return_value=(True, (None, bytearray(b'')), None)),
          patch('soyyo.acciones.keyring.get_password', return_value=None)):
        # @formatter:on
        resultado = lista(fichero)
    assert resultado == EstadoApp.SALIENDO_ERROR


def test_lista_error_inesperado(tmp_path, caplog):
    fichero = tmp_path / 'datos.json'
    # @formatter:off
    with (patch('soyyo.acciones.autorizame', side_effect=Exception),
          caplog.at_level(logging.ERROR)):
        # @formatter:on
        with pytest.raises(Exception):
            lista(fichero)
        mensajes = [r.message for r in caplog.records]
        assert len(mensajes) == 1
        assert 'Error indeterminado en el proceso lista.' in mensajes[0]
