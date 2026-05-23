"""
Acciones que reliza el programa

"""

import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import time

import keyring.errors as keyring_errors
import pyotp
from keyring import delete_password, set_password
from PIL import ImageGrab
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QPushButton, QWidget
from pyzbar.pyzbar import decode

from soyyo.auxiliares import validate_pin
from soyyo.constantes import CURSORES, EstadoSistema, Zona
from soyyo.mensajes import MSG_ERROR_CAPTURA, MSG_ERROR_DECODIFICA, MSG_PROMPT_RESET, MSG_SETUP

os.environ["QT_QPA_PLATFORM"] = "xcb"
log = logging.getLogger(__name__)

BORDE = 8


class VentanaCaptura(QWidget):
    """
    Clase para generar una pantalla de captura de imagenes y capturar una imagen
    """

    def __init__(self, ancho, alto):
        super().__init__()
        self._pantalla = QApplication.primaryScreen().availableGeometry()
        self._clic_pos = None
        self._zona_activa = None
        self._ancho_original = ancho
        self._alto_original = alto
        self.imagen = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.resize(QSize(self._ancho_original, self._alto_original))
        self.setMinimumSize(200, 200)

        # Botones en la parte superior (opacos, sobre fondo sólido)
        self._btn_capturar = QPushButton("Capturar", self)
        self._btn_cancelar = QPushButton("Cancelar", self)
        self._btn_capturar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_capturar.move(10, 10)
        self._btn_cancelar.move(100, 10)
        self._btn_capturar.clicked.connect(self._capturar)
        self._btn_cancelar.clicked.connect(self.close)

    def _zona_actual(self, pos):
        if pos is None:
            raise ValueError('pos no puede ser None')
        x = pos.x()
        y = pos.y()
        zona = Zona.INTERIOR

        if (y < BORDE) and (x < BORDE):
            zona = Zona.ESQUINA_SUPERIOR_IZQUIERDA
        elif (y < BORDE) and (x > self.width() - BORDE):
            zona = Zona.ESQUINA_SUPERIOR_DERECHA
        elif (y > self.height() - BORDE) and (x < BORDE):
            zona = Zona.ESQUINA_INFERIOR_IZQUIERDA
        elif (y > self.height() - BORDE) and (x > self.width() - BORDE):
            zona = Zona.ESQUINA_INFERIOR_DERECHA
        elif (y < BORDE) and (BORDE < x < self.width() - BORDE):
            zona = Zona.BORDE_SUPERIOR
        elif (y > self.height() - BORDE) and (BORDE < x < self.width() - BORDE):
            zona = Zona.BORDE_INFERIOR
        elif (x < BORDE) and (BORDE < y < self.height() - BORDE):
            zona = Zona.BORDE_IZQUIERDO
        elif (x > self.width() - BORDE) and (BORDE < y < self.height() - BORDE):
            zona = Zona.BORDE_DERECHO
        elif (BORDE < y < 40) and (BORDE < x < self.width() - BORDE):
            zona = Zona.BARRA

        return zona

    def _capturar(self):
        geo = self.geometry()
        area = (
                geo.x(),
                geo.y() + 40,  # descarta la barra de botones
                geo.x() + geo.width(),
                geo.y() + geo.height()
                )
        self.hide()
        log.debug(f'Área a capturar: {area}')
        self.imagen = ImageGrab.grab(bbox=area, all_screens=True)
        self.show()
        self.close()

    def mousePressEvent(self, event):
        """
        Gestión del evento cuando se presiona el botón izquierdo del ratón.
        """

        if event.button() == Qt.MouseButton.LeftButton:
            self._clic_pos = event.position().toPoint()  # posición relativa al widget
            self._zona_activa = self._zona_actual(self._clic_pos)
            self._ancho_original = self.size().width()
            self._alto_original = self.size().height()

    def mouseMoveEvent(self, event):
        """
        Gestión del evento cuando se mueve el ratón.
        """

        if self._clic_pos is not None:
            delta = event.position().toPoint() - self._clic_pos
            limite_inferior = self._pantalla.height() - (self.y() + self._alto_original)
            limite_derecho = self._pantalla.width() - (self.x() + self._ancho_original)
            nueva_x = self.pos().x()
            nueva_y = self.pos().y()
            nuevo_ancho = self.size().width()
            nuevo_alto = self.size().height()
            if self._zona_activa == Zona.ESQUINA_SUPERIOR_IZQUIERDA:
                nueva_x = max(self.pos().x() + delta.x(), 0)
                if nueva_x > 0:
                    nuevo_ancho -= delta.x()
                else:
                    nuevo_ancho += self.pos().x()
                nueva_y = max(self.pos().y() + delta.y(), 0)
                if nueva_y > 0:
                    nuevo_alto -= delta.y()
                else:
                    nuevo_alto += self.pos().y()
                if nuevo_ancho <= 200:
                    nueva_x = self.pos().x()
                    nuevo_ancho = 200
                if nuevo_alto <= 200:
                    nueva_y = self.pos().y()
                    nuevo_alto = 200
            elif self._zona_activa == Zona.ESQUINA_SUPERIOR_DERECHA:
                nueva_y = max(self.pos().y() + delta.y(), 0)
                nuevo_ancho = self._ancho_original + min(delta.x(), limite_derecho)
                if nueva_y > 0:
                    nuevo_alto -= delta.y()
                else:
                    nuevo_alto += self.pos().y()
                if nuevo_alto <= 200:
                    nueva_y = self.pos().y()
                    nuevo_alto = 200
            elif self._zona_activa == Zona.ESQUINA_INFERIOR_IZQUIERDA:
                nueva_x = max(self.pos().x() + delta.x(), 0)
                if nueva_x > 0:
                    nuevo_ancho -= delta.x()
                else:
                    nuevo_ancho += self.pos().x()
                nuevo_alto = self._alto_original + min(delta.y(), limite_inferior)
                if nuevo_ancho <= 200:
                    nueva_x = self.pos().x()
                    nuevo_ancho = 200
            elif self._zona_activa == Zona.ESQUINA_INFERIOR_DERECHA:
                nuevo_alto = self._alto_original + min(delta.y(), limite_inferior)
                nuevo_ancho = self._ancho_original + min(delta.x(), limite_derecho)
            elif self._zona_activa == Zona.BORDE_SUPERIOR:
                nueva_y = max(self.pos().y() + delta.y(), 0)
                if nueva_y > 0:
                    nuevo_alto -= delta.y()
                else:
                    nuevo_alto += self.pos().y()
                if nuevo_alto <= 200:
                    nueva_y = self.pos().y()
                    nuevo_alto = 200
            elif self._zona_activa == Zona.BORDE_INFERIOR:
                nuevo_alto = self._alto_original + min(delta.y(), limite_inferior)
            elif self._zona_activa == Zona.BORDE_IZQUIERDO:
                nueva_x = max(self.pos().x() + delta.x(), 0)
                if nueva_x > 0:
                    nuevo_ancho -= delta.x()
                else:
                    nuevo_ancho += self.pos().x()
                if nuevo_ancho <= 200:
                    nueva_x = self.pos().x()
                    nuevo_ancho = 200
            elif self._zona_activa == Zona.BORDE_DERECHO:
                nuevo_ancho = self._ancho_original + min(delta.x(), limite_derecho)
            elif self._zona_activa == Zona.BARRA:
                nueva_x = self.pos().x() + delta.x()
                nueva_y = self.pos().y() + delta.y()
            self.setGeometry(nueva_x, nueva_y, nuevo_ancho, nuevo_alto)
        else:
            zona = self._zona_actual(event.position().toPoint())
            self.setCursor(CURSORES[zona])

    def mouseReleaseEvent(self, event):
        """
        Gestión del evento cuando se libera el ratón.
        """

        self._clic_pos = None
        self._zona_activa = None

    def paintEvent(self, event):
        """
        Gestión del evento cuando hay que dibujar la ventana.
        """

        painter = QPainter(self)
        # Barra superior opaca (donde van los botones)
        painter.fillRect(QRect(0, 0, self.width(), 40), QColor(50, 50, 50, 255))
        # Área de selección semitransparente
        painter.fillRect(QRect(0, 40, self.width(), self.height() - 40), QColor(100, 100, 255, 60))
        # Marco del área de selección
        painter.setPen(QColor(0, 120, 255))
        painter.drawRect(QRect(0, 40, self.width() - 1, self.height() - 41))


def setup(data_path):
    """
    Pide el PIN y lo guarda.
    """

    while True:
        if sys.stdout.isatty():
            print('\033[2J\033[H', end='')  # pragma: no cover

        print(MSG_SETUP)
        preguntas = ['PIN', 'Repita el PIN']

        try:
            pines = [validate_pin(arg) for arg in preguntas]
        except KeyboardInterrupt:
            return EstadoSistema.SALIENDO_OK

        if len(set(pines)) != 1:
            print('\nAmbos valores deben ser iguales.\n\n')
            time.sleep(1)
            continue
        break

    pin = str(set(pines).pop())
    salt = os.urandom(32)
    pepper = os.urandom(32)

    dk = hashlib.pbkdf2_hmac('sha256', pin.encode(), salt, 500_000)

    hash_64 = base64.b64encode(dk).decode('utf-8')
    salt_64 = base64.b64encode(salt).decode('utf-8')
    pepper_64 = base64.b64encode(pepper).decode('utf-8')

    autorizacion = {'hash': hash_64, 'salt': salt_64}
    totp = {}

    datos = {'version': 1, 'autorizacion': autorizacion, 'intentos': 0, 'totp': totp}
    cadena_json = json.dumps(datos, sort_keys=True, separators=(',', ':')).encode()
    firma = hmac.new(pepper, cadena_json, 'sha512').hexdigest()

    try:
        set_password('soyyo', 'pepper', pepper_64)
    except keyring_errors.PasswordSetError as error:
        log.error(error)
        print(error)
        return EstadoSistema.SALIENDO_ERROR

    try:
        datos = {'version': 1, 'autorizacion': autorizacion, 'intentos': 0, 'totp': totp,
                 'firma': firma}
        with open(data_path, 'w', encoding='utf8') as fout:
            json.dump(datos, fout, sort_keys=True, separators=(',', ':'))
        return EstadoSistema.OK
    except Exception as error:
        log.error(error)
        delete_password('soyyo', 'pepper')
        print(error)
        return EstadoSistema.SALIENDO_ERROR


def reset(data_path):
    """
    Elimina (si existen) el almacen de datos y la clave pepper del keyring
    """

    if sys.stdout.isatty():
        print('\033[2J\033[H', end='')  # pragma: no cover

    while True:
        if sys.stdout.isatty():
            print('\033[2J\033[H', end='')  # pragma: no cover

        try:
            data = input(MSG_PROMPT_RESET).upper().strip()
        except KeyboardInterrupt:
            data = 'C'

        if len(data) != 1 or data not in 'NSC':
            continue

        if data == 'S':
            data_path.unlink(missing_ok=True)
            try:
                delete_password('soyyo', 'pepper')
            except keyring_errors.PasswordDeleteError:
                pass
            return EstadoSistema.PRIMER_ARRANQUE
        else:
            return EstadoSistema.SALIENDO_OK


def captura():
    """
    Captura el QR de un secreto TOTP
    """

    app = QApplication(sys.argv)
    print(dir(app))
    ventana = VentanaCaptura(300, 300)
    ventana.show()
    app.exec()

    if ventana.imagen:
        decodificada = decode(ventana.imagen)
        if decodificada:
            log.debug('QR decodificado')
            totp = pyotp.parse_uri(decodificada[0].data)
            print(f'{totp.issuer}:{totp.name}')
            print(decodificada[0].data)
        else:
            print(MSG_ERROR_DECODIFICA)
            return EstadoSistema.SALIENDO_ERROR
    else:
        print(MSG_ERROR_CAPTURA)
        return EstadoSistema.SALIENDO_ERROR

    return EstadoSistema.SALIENDO_OK
