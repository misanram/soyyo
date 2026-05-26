"""
Tests del módulo acciones.py
"""

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import keyring.errors as keyring_errors
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent, QPaintEvent
from PySide6.QtWidgets import QApplication

from soyyo.acciones import autorizar, captura, reset, setup, VentanaCaptura
from soyyo.constantes import CURSORES, EstadoSistema, Zona

ESTIRAR = 'estirar'
MAXIMO = 'maximo'
REDUCIR = 'reducir'
MINIMO = 'minimo'
SUBIR = 'subir'
BAJAR = 'bajar'
DERECHA = 'derecha'
IZQUIERDA = 'izquierda'


@pytest.fixture
def almacen_valido(tmp_path):
    """Crea un fichero de datos con firma válida"""

    def _factory(minutos_bloqueo=0, num_bloqueos=0):
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
        firma = hmac.new(pepper, cadena_json, 'sha512').hexdigest()

        datos = {'version': 1, 'autorizacion': autorizacion, 'intentos': 1, 'bloqueado_hasta': momento,
                 'num_bloqueos': num_bloqueos, 'totp': {}, 'firma': firma}
        fichero = tmp_path / 'datos.json'
        with open(fichero, 'w', encoding='utf8') as fout:
            json.dump(datos, fout, sort_keys=True, separators=(',', ':'))

        return fichero, pepper_64

    return _factory


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
    # @formatter:off
    with (patch('soyyo.acciones.input', return_value='S'),
          patch('soyyo.acciones.delete_password', return_value=None)):
        # @formatter:on
        respuesta = reset(fichero)
    assert respuesta == EstadoSistema.PRIMER_ARRANQUE


def test_reset_S_keyring_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    # @formatter:off
    with (patch('soyyo.acciones.input', return_value='S'),
          patch('soyyo.acciones.delete_password', side_effect=keyring_errors.PasswordDeleteError)):
        # @formatter:on
        respuesta = reset(fichero)
    assert respuesta == EstadoSistema.PRIMER_ARRANQUE


def test_setup_sin_error2(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    pepper_almacenado = {}  # actúa como keyring en memoria
    def fake_set_password(servicio, usuario, valor):
        pepper_almacenado[(servicio, usuario)] = valor
    def fake_get_password(servicio, usuario):
        return pepper_almacenado.get((servicio, usuario))
    with (patch('soyyo.acciones.set_password', side_effect=fake_set_password),
          patch('soyyo.auxiliares.get_password', side_effect=fake_get_password),
          patch('soyyo.acciones.obtener_pin', return_value=bytearray(b'12345678'))):
        assert setup(fichero) == EstadoSistema.INICIALIZACION_CORRECTA

def test_setup_sin_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    # @formatter:off
    with (patch('soyyo.acciones.set_password'),
          patch('soyyo.acciones.obtener_pin', return_value=bytearray(b'12345678'))):
        # @formatter:on
        assert setup(fichero) == EstadoSistema.INICIALIZACION_CORRECTA


def test_setup_keyboard_interrupt(tmp_path, capsys):
    fichero = tmp_path / 'datos.json'
    with patch('soyyo.acciones.obtener_pin', side_effect=KeyboardInterrupt):
        assert setup(fichero) == EstadoSistema.SALIENDO_OK


def test_setup_pines_distintos(tmp_path, capsys):
    fichero = tmp_path / 'datos.json'
    # @formatter:off
    with (patch('soyyo.acciones.set_password'),
          patch('soyyo.acciones.obtener_pin', side_effect=[bytearray(b'0'), bytearray(b'1'),
                                                           bytearray(b'12345678'),bytearray(b'12345678')])):
        # @formatter:on
        setup(fichero)
        captured = capsys.readouterr()
    assert '\nAmbos valores deben ser iguales.\n\n' in captured.out


def test_setup_set_keyring_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    # @formatter:off
    with (patch('soyyo.acciones.obtener_pin', return_value=bytearray(b'12345678')),
          patch('soyyo.acciones.set_password', side_effect=keyring_errors.PasswordSetError)):
        # @formatter:on
        assert setup(fichero) == EstadoSistema.SALIENDO_ERROR


def test_setup_file_write_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    # @formatter:off
    with (patch('soyyo.acciones.set_password'),
          patch('soyyo.acciones.delete_password'),
          patch('soyyo.acciones.guarda_json', side_effect=OSError),
          patch('soyyo.acciones.obtener_pin', return_value=bytearray(b'12345678'))):
        # @formatter:on
        assert setup(fichero) == EstadoSistema.SALIENDO_ERROR


def test_setup_delete_password_keyring_error(tmp_path):
    fichero = tmp_path / 'datos.json'
    fichero.touch()
    fichero.chmod(0o444)
    # @formatter:off
    with (patch('soyyo.acciones.set_password'),
          patch('soyyo.acciones.obtener_pin', return_value=bytearray(b'12345678')),
          patch('soyyo.acciones.delete_password', side_effect=keyring_errors.PasswordDeleteError)):
        # @formatter:on
        with pytest.raises(keyring_errors.PasswordDeleteError):
            setup(fichero)


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


def test_captura():
    with patch('soyyo.acciones.QApplication'):
        with patch('soyyo.acciones.VentanaCaptura') as mock_ventana:
            mock_ventana.return_value.imagen = None
            resultado = captura()
    assert resultado == EstadoSistema.SALIENDO_ERROR


def test_captura_sin_qr():
    with patch('soyyo.acciones.QApplication'):
        with patch('soyyo.acciones.VentanaCaptura') as mock_ventana:
            mock_ventana.return_value.imagen = 'imagen_falsa'
            with patch('soyyo.acciones.decode', return_value=[]):
                resultado = captura()
    assert resultado == EstadoSistema.SALIENDO_ERROR


def test_captura_ok():
    mock_totp = MagicMock()
    mock_totp.issuer = 'Google'
    mock_totp.name = 'usuario@gmail.com'
    mock_decoded = MagicMock()
    mock_decoded.data = b'otpauth://totp/...'
    # @formatter:off
    with (patch('soyyo.acciones.QApplication'),
          patch('soyyo.acciones.VentanaCaptura') as mock_ventana,
          patch('soyyo.acciones.decode', return_value=[mock_decoded]),
          patch('soyyo.acciones.pyotp.parse_uri', return_value=mock_totp),):
        # @formatter:on
        mock_ventana.return_value.imagen = 'imagen_falsa'
        resultado = captura()
    assert resultado == EstadoSistema.SALIENDO_OK


def test_autorizar_bloqueo_temporal(almacen_valido, capsys):
    fichero, pepper = almacen_valido(minutos_bloqueo=10000)
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        resultado = autorizar(fichero)
    assert resultado == EstadoSistema.SALIENDO_OK


def test_autorizar_bloqueo_temporal_finalizado(almacen_valido, capsys):
    fichero, pepper = almacen_valido(minutos_bloqueo=-10000)
    pin = bytearray(b'12345678')
    # @formatter:off
    with (patch('soyyo.acciones.obtener_pin', return_value=pin),
          patch('soyyo.auxiliares.get_password', return_value=pepper)):
        # @formatter:on
        assert autorizar(fichero) == EstadoSistema.AUTORIZADO


def test_autorizar_bloqueo_permanente(almacen_valido, capsys):
    fichero, pepper = almacen_valido(num_bloqueos=10)
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        resultado = autorizar(fichero)
    assert resultado == EstadoSistema.SALIENDO_OK


def test_autorizar_ok(almacen_valido):
    fichero, pepper = almacen_valido()
    pin = bytearray(b'12345678')
    with (patch('soyyo.acciones.obtener_pin', return_value=pin), patch('soyyo.auxiliares.get_password',
                                                                       return_value=pepper)):
        # @formatter:on
        assert autorizar(fichero) == EstadoSistema.AUTORIZADO


@pytest.mark.parametrize('pin, respuesta',
                         [(bytearray(b'1234567'), EstadoSistema.SALIENDO_OK),
                          (bytearray(b'12345678'), EstadoSistema.AUTORIZADO), ])
def test_autorizar_un_fallo(almacen_valido, pin, respuesta):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.acciones.obtener_pin', return_value=pin),
          patch('soyyo.auxiliares.get_password', return_value=pepper)):
        # @formatter:on
        assert respuesta == autorizar(fichero)


@pytest.mark.parametrize('pin, respuesta',
                         [(bytearray(b'1234567'), EstadoSistema.SALIENDO_OK),
                          (bytearray(b'1234567'), EstadoSistema.SALIENDO_OK),
                          (bytearray(b'12345678'), EstadoSistema.AUTORIZADO), ])
def test_autorizar_dos_fallos(almacen_valido, pin, respuesta):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.acciones.obtener_pin', return_value=pin),
          patch('soyyo.auxiliares.get_password', return_value=pepper)):
        # @formatter:on
        assert respuesta == autorizar(fichero)


def test_autorizar_tres_fallos(almacen_valido, caplog):
    import logging
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.acciones.obtener_pin', return_value='0000'),
          patch('soyyo.acciones.validar_pin', return_value=False),
          patch('soyyo.auxiliares.get_password', return_value=pepper),
          patch('soyyo.acciones.guarda_json'),
          caplog.at_level(logging.INFO)):
        # @formatter:on
        resultado = autorizar(data_path=fichero)

    # Verificar los tres intentos en el log
    mensajes = [r.message for r in caplog.records if 'PIN erróneo' in r.message]
    assert len(mensajes) == 3
    assert 'intento 1' in mensajes[0]
    assert 'intento 2' in mensajes[1]
    assert 'intento 3' in mensajes[2]
    assert resultado == EstadoSistema.SALIENDO_OK


def test_autorizar_KeyboardInterrupt(almacen_valido):
    fichero, pepper = almacen_valido()
    # @formatter:off
    with (patch('soyyo.acciones.obtener_pin', side_effect=KeyboardInterrupt),
          patch('soyyo.auxiliares.get_password', return_value=pepper)):
        # @formatter:on
        assert autorizar(fichero) == EstadoSistema.SALIENDO_OK


def test_autorizar_firma_invalida(almacen_valido):
    fichero, pepper = almacen_valido()
    pepper = base64.b64encode(b'fake_pepper').decode('utf-8')
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        assert autorizar(fichero) == EstadoSistema.FIRMA_INVALIDA


def test_autorizar_pepper_not_found(almacen_valido):
    fichero, pepper = almacen_valido()
    pepper = None
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        assert autorizar(fichero) == EstadoSistema.SIN_PEPPER


def test_autorizar_error_lectura_fichero_almacen(almacen_valido):
    fichero, pepper = almacen_valido()
    fichero = Path('/noexiste')
    with patch('soyyo.auxiliares.get_password', return_value=pepper):
        assert autorizar(fichero) == EstadoSistema.SALIENDO_ERROR
