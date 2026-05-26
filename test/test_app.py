"""
Tests del módulo app.py
"""
import argparse
import logging
from unittest.mock import patch

import pytest

from soyyo.app import Aplicacion, get_options, main
from soyyo.constantes import EstadoApp


def test_get_options_no_args():
    with patch('sys.argv', ['soyyo']):
        args = get_options()
        assert all(vars(args).values()) is False


def test_get_options_reset():
    with patch('sys.argv', ['soyyo', '--reset']):
        argumentos = get_options().parse_args()
        assert argumentos.reset is True


def test__comprobar_estado_sin_keyring():
    # @formatter:off
    with (patch('soyyo.app.get_options'),
          patch('soyyo.app.chek_keyring', return_value=False)):
        # @formatter:on
        app = Aplicacion(argparse.Namespace())
        assert app._comprobar_estado() == EstadoApp.SIN_KEYRING


def test__comprobar_estado_primer_arranque():
    # @formatter:off
    with (patch('soyyo.app.get_options'),
          patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=False)):
        # @formatter:on
        app = Aplicacion(argparse.Namespace())
        assert app._comprobar_estado() == EstadoApp.PRIMER_ARRANQUE


def test__comprobar_estado_sin_pepper():
    # @formatter:off
    with (patch('soyyo.app.get_options'),
          patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=True),
          patch('soyyo.app.comprobar_seguridad', return_value=EstadoApp.SIN_PEPPER)):
        # @formatter:on
        app = Aplicacion(argparse.Namespace())
        assert app._comprobar_estado() == EstadoApp.SIN_PEPPER


def test__comprobar_estado_fichero_corrupto():
    # @formatter:off
    with (patch('soyyo.app.get_options'),
          patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=True),
          patch('soyyo.app.comprobar_seguridad', return_value=EstadoApp.FICHERO_CORRUPTO)):
        # @formatter:on
        app = Aplicacion(argparse.Namespace())
        assert app._comprobar_estado() == EstadoApp.FICHERO_CORRUPTO


def test__comprobar_estado_firma_invalida():
    # @formatter:off
    with (patch('soyyo.app.get_options'),
          patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=True),
          patch('soyyo.app.comprobar_seguridad', return_value=EstadoApp.FIRMA_INVALIDA)):
        # @formatter:on
        app = Aplicacion(argparse.Namespace())
        assert app._comprobar_estado() == EstadoApp.FIRMA_INVALIDA


def test__comprobar_estado_todo_ok():
    with (patch('soyyo.app.get_options'),
          patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=True),
          patch('soyyo.app.comprobar_seguridad', return_value=EstadoApp.INICIALIZACION_CORRECTA)):
        # @formatter:on
        app = Aplicacion(argparse.Namespace())
        assert app._comprobar_estado() == EstadoApp.INICIALIZACION_CORRECTA


def test_run_estado_autorizado_sin_argumentos(caplog):
    # @formatter:off
    with (patch.object(Aplicacion, '_comprobar_estado', return_value=EstadoApp.AUTORIZADO),
          patch('sys.argv', ['soyyo']),
          caplog.at_level(logging.DEBUG)):
        # @formatter:on
        with pytest.raises(SystemExit):
            main()
    mensajes = [r.message for r in caplog.records]
    assert len(mensajes) == 1
    assert 'Aplicación llamada sin argumentos.' in mensajes


def test_run_estado_erroneo(caplog):
    # @formatter:off
    with (patch.object(Aplicacion, '_comprobar_estado', return_value=None),
          patch('sys.argv', ['soyyo', '--test']),
          caplog.at_level(logging.ERROR)):
        # @formatter:on
        with pytest.raises(SystemExit):
            main()
    mensajes = [r.message for r in caplog.records]
    assert len(mensajes) == 1
    assert 'La aplicación ha caido en un estado imposible:' in mensajes[0]


def test_run_reset(capsys):
    # @formatter:off
    with (patch.object(Aplicacion, '_comprobar_estado',return_value=EstadoApp.INICIALIZACION_CORRECTA),
          patch('sys.argv', ['soyyo', '--reset']),
          patch('soyyo.app.reset', return_value=EstadoApp.PRIMER_ARRANQUE),
          patch('soyyo.app.setup', return_value=EstadoApp.SALIENDO_OK), ):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    assert ' Aplicación finalizada.' in captured.out


def test_run_captura(capsys):
    # @formatter:off
    with (patch.object(Aplicacion, '_comprobar_estado', return_value=EstadoApp.AUTORIZADO),
          patch('sys.argv', ['soyyo', '--captura']),
          patch('soyyo.app.captura', return_value=EstadoApp.SALIENDO_OK), ):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    assert 'Aplicación finalizada' in captured.out


def test_run_sin_keyring(capsys):
    # @formatter:off
    with (patch.object(Aplicacion, '_comprobar_estado', return_value=EstadoApp.SIN_KEYRING),
          patch('sys.argv', ['soyyo', '--test'])):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
    captured = capsys.readouterr()
    assert 'No hay un sistema de almacenamiento seguro disponible en este sistema.' in captured.out


def test_run_sin_pepper(capsys):
    # @formatter:off
    with (patch.object(Aplicacion, '_comprobar_estado', return_value=EstadoApp.SIN_PEPPER),
          patch('sys.argv', ['soyyo', '--test'])):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
    captured = capsys.readouterr()
    assert 'No hay clave de firma en el sistema de almacenamiento seguro del sistema.' in captured.out


def test_run_fichero_corrupto(capsys):
    # @formatter:off
    with (patch.object(Aplicacion, '_comprobar_estado', return_value=EstadoApp.FICHERO_CORRUPTO),
          patch('sys.argv', ['soyyo', '--test'])):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
    captured = capsys.readouterr()
    assert 'El almacén de datos es ilegible o está corrupto.' in captured.out


def test_run_firma_invalida(capsys):
    # @formatter:off
    with (patch.object(Aplicacion, '_comprobar_estado', return_value=EstadoApp.FIRMA_INVALIDA),
          patch('sys.argv', ['soyyo', '--test'])):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
    captured = capsys.readouterr()
    assert 'El almacén de datos parece haber sido manipulado' in captured.out


def test_run_saliendo_ok():
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          patch.object(Aplicacion,'_comprobar_estado', return_value=EstadoApp.SALIENDO_OK)):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0


def test_run_saliendo_error():
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          patch.object(Aplicacion, '_comprobar_estado', return_value=EstadoApp.SALIENDO_ERROR)):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1


def test_main(capsys):
    # @formatter:off
    with (patch.object(Aplicacion,'_comprobar_estado',return_value=EstadoApp.INICIALIZACION_CORRECTA),
          patch('sys.argv',['soyyo', '--test']),
          patch('soyyo.app.autorizar', return_value=EstadoApp.AUTORIZADO),):
        main()
    captured = capsys.readouterr()
    assert 'True' in captured.out
