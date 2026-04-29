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
import tkinter as tk
from tkinter import ttk

import keyring.errors as keyring_errors
import pyotp
from keyring import delete_password, set_password
from PIL import ImageGrab
from pyzbar.pyzbar import decode

from soyyo.auxiliares import validate_pin
from soyyo.estados import EstadoSistema
from soyyo.mensajes import MSG_PROMPT_RESET, MSG_SETUP

log = logging.getLogger(__name__)


class VentanaCaptura(ttk.Frame):
    """
    Clase para capturar pantalla con código QR

    """

    def __init__(self, master=None):
        super().__init__(master)
        self.grid(column=0, row=0, sticky=tk.NSEW)
        self._crearWidgets()
        self.s = ttk.Style()
        self.s.configure('TButton', font=('TkDefaultFont', 12, 'bold'))
        top = self.winfo_toplevel()
        top.rowconfigure(0, weight=1)
        top.columnconfigure(0, weight=1)
        top.resizable(height=tk.TRUE, width=tk.TRUE)
        top.minsize(200, 210)
        top.title('soyyo captura de QR')
        top.protocol("WM_DELETE_WINDOW", self._cerrar)
        top.wait_visibility()
        top.attributes('-alpha', 0.5)

    def _cerrar(self):
        self.quit()

    def _capturar(self):
        x = self.canvas.winfo_rootx()
        y = self.canvas.winfo_rooty()
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        top = self.winfo_toplevel()
        top.withdraw()
        top.update()
        time.sleep(1)

        imagen = ImageGrab.grab(bbox=(x, y, x + w, y + h))

        top.deiconify()

        decodificada = decode(imagen)

        print(dir(decodificada[0]))
        print(decodificada[0].data)
        print(decodificada[0].type)

        totp = pyotp.parse_uri(decodificada[0].data)

        print(totp.issuer)  # nombre del servicio
        print(totp.name)  # usuario
        print(totp.secret)  # la clave
        print(totp.now())  # genera el token actual
        print(totp.interval)
        print(totp.digits)

    def _crearWidgets(self):
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.columnconfigure(0, weight=1)

        self.frame_visor = ttk.Frame(self)
        self.frame_visor.grid(row=0, column=0, sticky=tk.NSEW)
        self.frame_visor.rowconfigure(0, weight=1)
        self.frame_visor.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.frame_visor, bg='gray')
        self.canvas.grid(row=0, column=0, sticky=tk.NSEW)

        self.frame_botones = ttk.Frame(self)
        self.frame_botones.columnconfigure(0, weight=1)
        self.frame_botones.grid(row=1, column=0, sticky=tk.EW)

        self.boton_cancelar = ttk.Button(self.frame_botones, text='Cancelar', command=self._cerrar)
        self.boton_cancelar.grid(row=0, column=1, pady=5, padx=5, sticky=tk.EW)
        self.frame_botones.columnconfigure(1, weight=1)

        self.boton_captura = ttk.Button(self.frame_botones, text='Capturar', command=self._capturar)
        self.boton_captura.grid(row=0, column=0, pady=5, padx=5, sticky=tk.EW)
        self.frame_botones.columnconfigure(0, weight=1)


def setup(data_path):
    """
    Pide el PIN y lo guarda.
    """

    while True:
        if sys.stdout.isatty():
            print('\033[2J\033[H', end='')  # pragma: no cover

        print(MSG_SETUP)
        preguntas = ['PIN', 'Repita el PIN']
        pines = []

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


def captura(data_path):
    """
    Captura el QR de un secreto TOTP
    """

    ventana = VentanaCaptura()
    ventana.mainloop()

    return EstadoSistema.SALIENDO_OK
