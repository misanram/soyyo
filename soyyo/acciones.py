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
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import keyring
import keyring.errors as keyring_errors
from cryptography.fernet import Fernet
from PIL import ImageGrab
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QPushButton, QWidget
from pyzbar.pyzbar import decode

from .auxiliares import (autorizame, captura_teclado, check_almacen, check_keyring, guardar_json,
                         reintentar_keyring, selecciona_ruta)
from .constantes import CURSORES, EstadoApp, Zona
from .errores import CapturaError, FirmaInvalidaError, PepperNotFoundError, SinRutaLlaveError
from .mensajes import (MSG_CABECERA, MSG_ERROR_APP_BLOQUEADA_TEMPORAL, MSG_ERROR_APP_BLOQUEDA,
                       MSG_ERROR_CAPTURA, MSG_ERROR_DECODIFICA, MSG_FICHERO_CORRUPTO,
                       MSG_INSTRUCCIONES_SETUP, MSG_PIN_FICHERO_LLAVE, MSG_PIN_SETUP, MSG_PROMPT_RESET,
                       MSG_RESET_REALIZADO,
                       MSG_SIN_PEPPER,
                       MSG_TOTP_CAPTURADO)

BORDE = 8

os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')

log = logging.getLogger(__name__)

keyring.get_password = reintentar_keyring()(keyring.get_password)  # type: ignore


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
        self.error = None
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
        area = None
        try:
            geo = self.geometry()
            area = (geo.x(), geo.y() + 40,  # descarta la barra de botones
                    geo.x() + geo.width(), geo.y() + geo.height())
            self.hide()
            log.debug(f'Área a capturar: {area}')
            self.imagen = ImageGrab.grab(bbox=area, all_screens=True)
            self.show()
            self.close()
        except Exception as error:
            self.error = CapturaError('Falló la captura de pantalla', area=area, causa=error)
            self.close()

    def mousePressEvent(self, event):
        """
        Gestión del evento cuando se presiona el botón izquierdo del ratón.
        """

        if event.button() == Qt.MouseButton.LeftButton:  # pragma: no branch
            self._clic_pos = event.position().toPoint()
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


def comprobar_estado(data_path):
    """
       Determina el estado inicial del sistema mediante comprobaciones secuenciales.
       El orden es estricto: cada comprobación asume que las anteriores han pasado.

       Secuencia:
           1. Keyring del sistema operativo (requisito de plataforma)
           2. Existencia del almacén (distingue primer arranque de ejecución normal)
           3. Luego hace una comprobación de seguridad, comprobando atómicamente almacén, pepper y firma:
                Comprueba que exista almacen, pepper y firma.
                Que todo sea legible y correcto.
                Que la firma abra el almacén.
                Que la aplicación no esté bloqueada temporalemente
                Que la aplicación no esté bloqueada permanentemente

       Devuelve un estado, uno de los siguientes valores:
           - INICIALIZACION_CORRECTA → todo en orden
           - PRIMER_ARRANQUE → no hay almacén (primera ejecución o datos perdidos)
           - SIN_KEYRING → el SO no tiene keyring; el programa no puede funcionar
           - SIN_PEPPER → almacén presente, pero pepper ausente; datos irrecuperables
           - FICHERO_CORRUPTO → JSON inválido o error de lectura
           - FIRMA_INVALIDA → JSON válido, pero la firma no coincide
           - SALIENDO_OK - No hay errores, pero el programa sufre un bloque temporal o permamente
           - INICIALIZACION_CORRECTA - si el programa puede funcionar.


       Notas:
           PRIMER_ARRANQUE cubre dos casos: 1) primera ejecución de la app y 2) pérdida accidental
           del almacén. La interfaz debe informar al usuario de esta ambigüedad.
           SALIENDO_OK cubre dos casos: Bloqueo permanete y bloqueo temporal. El programa está en
           condiciones de funcionar, operar hay un bloqueo por eerrores al ingresar el PIN. Se informa al
           usuario de la situación y sale sin generar errores.
       """
    try:
        if not check_keyring():
            return EstadoApp.SIN_KEYRING
        elif not check_almacen(data_path):
            return EstadoApp.PRIMER_ARRANQUE

        with open(data_path, 'r', encoding='utf8') as fin:
            datos = json.load(fin)
            firma = datos.pop('firma', None)
            if firma is None:
                raise FirmaInvalidaError
        cadena_json = json.dumps(datos, sort_keys=True, separators=(',', ':')).encode()
        pepper = keyring.get_password('soyyo', 'pepper')
        if pepper:
            pepper64 = base64.b64decode(pepper)
            nueva_firma = hmac.new(pepper64, cadena_json, 'sha512').hexdigest()
            if hmac.compare_digest(firma, nueva_firma):
                num_bloqueos = datos['num_bloqueos']
                if datos['bloqueado_hasta']:
                    bloqueado_hasta = datetime.fromisoformat(datos['bloqueado_hasta'])
                    if datetime.now(timezone.utc) < bloqueado_hasta:
                        log.info('Aplicación bloqueada temporalmente.')
                        print(MSG_ERROR_APP_BLOQUEADA_TEMPORAL % bloqueado_hasta.astimezone().strftime('%c'))
                        return EstadoApp.SALIENDO_OK
                if num_bloqueos >= 10:
                    log.info('Aplicación bloqueada permanentemente.')
                    print(MSG_ERROR_APP_BLOQUEDA)
                    return EstadoApp.SALIENDO_OK
                return EstadoApp.INICIALIZACION_CORRECTA
            else:
                raise FirmaInvalidaError
        else:
            raise PepperNotFoundError
    except FirmaInvalidaError:
        log.exception('No hay firma en el archivo o esta es inválida.')
        return EstadoApp.FIRMA_INVALIDA
    except PepperNotFoundError:
        log.exception(PepperNotFoundError.__doc__)
        return EstadoApp.SIN_PEPPER
    except json.JSONDecodeError:
        log.exception('Error al abrir el archivo JSON.')
        return EstadoApp.FICHERO_CORRUPTO
    except OSError:
        log.exception("Fallo al leer '%s'", data_path)
        return EstadoApp.FICHERO_CORRUPTO
    except Exception:
        log.exception('Error indeterminado en el proceso de comprobar_estado.')
        raise


def reset(data_path):
    """
    Elimina (si existen) el almacen de datos y la clave pepper del keyring
    """

    while True:
        if sys.stdout.isatty():
            print('\033c', end='')  # pragma: no cover

        try:
            print(MSG_CABECERA)
            data = input(MSG_PROMPT_RESET).upper().strip()
        except KeyboardInterrupt:
            data = 'C'

        if len(data) != 1 or data not in 'NSC':
            continue

        if data == 'S':
            data_path.unlink(missing_ok=True)
            try:
                keyring.delete_password('soyyo', 'pepper')
            except keyring_errors.PasswordDeleteError:
                pass
            print(MSG_RESET_REALIZADO)
        return EstadoApp.SALIENDO_OK


def setup(data_path):
    """
    Pide el PIN y lo guarda en el keyring.
    """

    try:
        if sys.stdout.isatty():
            print('\033c', end='')  # pragma: no cover
        print(MSG_CABECERA)
        print(MSG_INSTRUCCIONES_SETUP, end='')
        captura_teclado(una_tecla=True)
        while True:
            try:
                ruta = selecciona_ruta()
            except KeyboardInterrupt:
                return EstadoApp.SALIENDO_OK
            if not ruta:
                log.warning('No hay ruta para guardar el fichero llave.')
                raise SinRutaLlaveError
            if sys.stdout.isatty():
                print('\033c', end='')  # pragma: no cover
            print(MSG_CABECERA)
            print(MSG_PIN_FICHERO_LLAVE)
            preguntas = ['\n\rPIN: ', '\n\rRepita el PIN: ']
            try:
                pines_llave = [captura_teclado(prompt=arg, setup=True) for arg in preguntas]
                print('\r')
            except KeyboardInterrupt:
                return EstadoApp.SALIENDO_OK

            if pines_llave[0] != pines_llave[1]:
                print('\nAmbos valores deben ser iguales.\n\n')
                time.sleep(1)
                continue
            break
        time.sleep(2)

        while True:
            if sys.stdout.isatty():
                print('\033c', end='')  # pragma: no cover

            print(MSG_CABECERA)
            print(MSG_PIN_SETUP)
            preguntas = ['\n\rPIN: ', '\n\rRepita el PIN: ']

            try:
                pines = [captura_teclado(prompt=arg, setup=True) for arg in preguntas]
                print('\r')
            except KeyboardInterrupt:
                return EstadoApp.SALIENDO_OK

            if pines[0] != pines[1]:
                print('\nAmbos valores deben ser iguales.\n\n')
                time.sleep(1)
                continue
            break

        pin = pines.pop()
        pines.clear()
        salt = os.urandom(32)
        pepper = os.urandom(32)

        dk = hashlib.pbkdf2_hmac('sha256', bytes(pin) + pepper, salt, 500_000, dklen=64)

        for i in range(len(pin)):
            pin[i] = 0
        del pin

        hash_64 = base64.b64encode(dk[:32]).decode('utf-8')
        salt_64 = base64.b64encode(salt).decode('utf-8')
        pepper_64 = base64.b64encode(pepper).decode('utf-8')

        autorizacion = {'hash': hash_64, 'salt': salt_64}
        totp = {}
        datos = {'version': 1, 'autorizacion': autorizacion, 'intentos': 0, 'bloqueado_hasta': None,
                 'num_bloqueos': 0, 'totp': totp}
        keyring.set_password('soyyo', 'pepper', pepper_64)
        guardar_json(data_path, datos)  # guardar_json no devuelve nada, guarda datos o levanta una excepción.
        return EstadoApp.SALIENDO_OK

    except keyring_errors.PasswordSetError as error:
        log.exception('Error al guardar el pepper en el keyring.')
        print(error)
        return EstadoApp.SALIENDO_ERROR
    except SinRutaLlaveError as error:
        log.exception('No hay ruta para guardar el fichero llave.')
        print(error)
        return EstadoApp.SALIENDO_ERROR
    except OSError as error:
        log.exception('Error al escribir archivo %s', data_path)
        print(error)
        try:
            keyring.delete_password('soyyo', 'pepper')
        except keyring_errors.PasswordDeleteError as sobreerror:
            log.exception('Error al eliminar el pepper del keyring')
            print(sobreerror)
        return EstadoApp.SALIENDO_ERROR
    except Exception:
        log.exception('Error indeterminado en el proceso de setup.')
        raise


def captura(data_path):
    """
    Captura el QR de un secreto TOTP
    """

    pepper: Any = None
    datos: Any = None
    try:
        app = QApplication(sys.argv)
        ventana = VentanaCaptura(300, 300)
        ventana.show()
        app.exec()

        if ventana.error:
            raise ventana.error

        # datos[0] es el almacen JSON transformado en diccionario (dict[str, str])
        # datos[1] es el PIN (bytes)
        autoriza, datos, estado = autorizame(data_path)

        if not autoriza:
            # autorizame loguea los errores correctamente, no hace falta loguearlos de nuevo
            # Devuelve el estado correcto
            return estado

        if ventana.imagen:
            log.debug('imagen capturada')
            decodificada = decode(ventana.imagen)
            if decodificada:
                log.debug('QR decodificado')
                uri = urlsplit(decodificada[0].data)
                label = unquote(uri.path.lstrip(b'/'))  # type: ignore
                issuer, account = label.split(':', 1) if ':' in label else ('', label)
                parametros: dict[bytes, list] = parse_qs(uri.query)  # type: ignore
                totp = dict(uri=decodificada[0].data.decode(),
                            issuer=issuer,
                            account=account,
                            nombre=parametros.get(b'issuer', [issuer.encode('utf8')])[0].decode(),
                            secret=parametros.get(b'secret', [b''])[0].decode(),
                            digits=int(parametros.get(b'digits', [6])[0]),
                            period=int(parametros.get(b'period', [30])[0]),
                            algoritmo=parametros.get(b'algorithm', [b'SHA1'])[0].decode())
                # # Serializar
                # totp_json = json.dumps(totp)
                # # str -> bytes
                # totp_bytes = totp_json.encode('utf-8')
                # # Encriptar
                # totp_encriptado = f.encrypt(totp_bytes)
                # # bytes -> str
                # totp_encriptado_str = totp_encriptado.decode('utf-8')
                pepper64 = keyring.get_password('soyyo', 'pepper')
                if pepper64:
                    pepper = bytearray(base64.b64decode(pepper64))
                    salt = base64.b64decode(datos[0]['autorizacion']['salt'])
                    dk = hashlib.pbkdf2_hmac('sha256', bytes(datos[1]) + pepper, salt, 500_000, dklen=64)
                    clave_fernet = base64.urlsafe_b64encode(dk[32:])
                    fernet = Fernet(clave_fernet)
                    # Para encriptar el dato debe ser bytes
                    totp_encriptado = fernet.encrypt(json.dumps(totp).encode('utf-8'))
                    # JSON solo admite str. Para introducir el totp_encriptado en un JSON hay que
                    # transformarlo en str
                    datos[0]['totp'].update({str(uuid.uuid4()): totp_encriptado.decode()})
                    guardar_json(data_path, datos[0])
                else:
                    raise PepperNotFoundError
            else:
                log.warning('No se ha podido decodificar la imagen capturada.')
                print(MSG_ERROR_DECODIFICA)
                return EstadoApp.SALIENDO_ERROR
        else:
            log.warning('No se ha podido capturar una imagen.')
            print(MSG_ERROR_CAPTURA)
            return EstadoApp.SALIENDO_ERROR
        print(MSG_TOTP_CAPTURADO)
        return EstadoApp.SALIENDO_OK

    except CapturaError:
        log.exception(CapturaError)
        print(MSG_ERROR_CAPTURA)
        return EstadoApp.SALIENDO_ERROR
    except PepperNotFoundError:
        log.exception(PepperNotFoundError.__doc__)
        print(MSG_SIN_PEPPER)
        return EstadoApp.SALIENDO_ERROR
    except OSError:
        log.exception('Error de escritura.')
        print(MSG_FICHERO_CORRUPTO)
        return EstadoApp.SALIENDO_ERROR
    except Exception:
        log.exception('Error indeterminado en el proceso de captura.')
        raise
    finally:
        if datos is not None:
            for i in range(len(datos[1])):
                datos[1][i] = 0
            del datos
        if pepper is not None:
            for i in range(len(pepper)):
                pepper[i] = 0
            del pepper


def lista(data_path):
    """
    Lista los TOTP que hay en el almacén.

    """

    pepper: Any = None
    datos: Any = None
    try:
        if sys.stdout.isatty():
            print('\033c', end='')  # pragma: no cover
        print(MSG_CABECERA)
        # datos[0] es el almacen JSON transformado en diccionario (dict[str, str])
        # datos[1] es el PIN (bytes)
        autoriza, datos, estado = autorizame(data_path)

        if not autoriza:
            # autorizame loguea los errores correctamente, no hace falta loguearlos de nuevo
            # Devuelve el estado correcto
            return estado

        pepper64 = keyring.get_password('soyyo', 'pepper')
        if pepper64:
            pepper = bytearray(base64.b64decode(pepper64))
            salt = base64.b64decode(datos[0]['autorizacion']['salt'])
            dk = hashlib.pbkdf2_hmac('sha256', bytes(datos[1]) + pepper, salt, 500_000, dklen=64)
            clave_fernet = base64.urlsafe_b64encode(dk[32:])
            fernet = Fernet(clave_fernet)
            if datos[0]['totp']:
                for orden, totp in enumerate(datos[0]['totp'].values()):
                    nombre = json.loads(fernet.decrypt(totp.encode('utf-8')).decode('utf-8'))['nombre']
                    print(orden, nombre)
                print('\nSeleccione un TOTP para realizar acciones sobre él.')
            else:
                print('\nNo hay ningún TOTP registrado.')
        else:
            raise PepperNotFoundError
        return EstadoApp.SALIENDO_OK

    except PepperNotFoundError:
        log.exception(PepperNotFoundError.__doc__)
        print(MSG_SIN_PEPPER)
        return EstadoApp.SALIENDO_ERROR
    except Exception:
        log.exception('Error indeterminado en el proceso lista.')
        raise
    finally:
        if datos:
            for i in range(len(datos[1])):
                datos[1][i] = 0
            del datos
        if pepper:
            for i in range(len(pepper)):
                pepper[i] = 0
            del pepper
