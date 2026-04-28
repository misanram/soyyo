"""
Tests del módulo app.py
"""

import base64
import hmac
import json
import os
from unittest.mock import patch

import pytest

from soyyo.app import Aplicacion, get_options, main
from soyyo.auxiliares import EstadoSistema


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


def test_get_options_no_args():
    with patch('sys.argv', ['soyyo']):
        args = get_options()
        assert all(vars(args).values()) is False


def test_get_options_reset():
    with patch('sys.argv', ['soyyo', '--reset']):
        args = get_options()
        assert args.reset is True


def test__comprueba_estado_sin_keyring():
    with patch('soyyo.app.get_options'), patch('soyyo.app.chek_keyring', return_value=False):
        app = Aplicacion()
        assert app._comprueba_estado() == EstadoSistema.SIN_KEYRING


def test__comprueba_estado_primer_arranque():
    with (patch('soyyo.app.get_options'), patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=False)):
        app = Aplicacion()
        assert app._comprueba_estado() == EstadoSistema.PRIMER_ARRANQUE


def test__comprueba_estado_sin_pepper():
    with (patch('soyyo.app.get_options'), patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=True),
          patch('soyyo.app.chek_pepper', return_value=False)):
        app = Aplicacion()
        assert app._comprueba_estado() == EstadoSistema.SIN_PEPPER


def test__comprueba_estado_todo_ok(almacen_valido):
    fichero, pepper_64 = almacen_valido
    with (patch('soyyo.app.get_options'), patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=True),
          patch('soyyo.app.chek_pepper', return_value=True),
          patch('soyyo.auxiliares.get_password', return_value=pepper_64)):
        app = Aplicacion()
        app.data_path = fichero
        assert app._comprueba_estado() == EstadoSistema.OK


def test_main(capsys):
    with (patch.object(Aplicacion, '_comprueba_estado', return_value=EstadoSistema.OK),
          patch('sys.argv', ['soyyo'])):
        main()
    captured = capsys.readouterr()
    assert 'True' in captured.out


def test_run_reset(capsys):
    with (patch.object(Aplicacion, '_comprueba_estado', return_value=EstadoSistema.OK),
          patch('sys.argv', ['soyyo', '--reset']),
          patch('soyyo.app.reset', return_value=EstadoSistema.PRIMER_ARRANQUE),
          patch('soyyo.app.setup', return_value=EstadoSistema.OK),
          ):
        main()
    captured = capsys.readouterr()
    assert 'False' in captured.out


def test_run_sin_key_ring(capsys):
    with (patch.object(Aplicacion, '_comprueba_estado', return_value=EstadoSistema.SIN_KEYRING),
          patch('sys.argv', ['soyyo'])):
        with pytest.raises(SystemExit):
            main()
    captured = capsys.readouterr()
    assert 'No hay un sistema de almacenamiento seguro disponible en este sistema.' in captured.out


def test_run_fichero_corrupto(capsys):
    with (patch.object(Aplicacion, '_comprueba_estado', return_value=EstadoSistema.FICHERO_CORRUPTO),
          patch('sys.argv', ['soyyo'])):
        with pytest.raises(SystemExit):
            main()
    captured = capsys.readouterr()
    assert 'El almacen de datos es ilegible o está corrupto.' in captured.out


def test_run_firma_invalida(capsys):
    with (patch.object(Aplicacion, '_comprueba_estado', return_value=EstadoSistema.FIRMA_INVALIDA),
          patch('sys.argv', ['soyyo'])):
        with pytest.raises(SystemExit):
            main()
    captured = capsys.readouterr()
    assert 'El almacen de datos es parece haber sido manipulado.' in captured.out
