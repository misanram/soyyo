"""
Tests del módulo app.py
"""
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


def test_run_llama_a_comprobar_estado(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.INICIALIZACION_CORRECTA),):
        # @formatter:on
        aplicacion = Aplicacion(get_options().parse_args())
        aplicacion.run()
        mensajes = [r.message for r in caplog.records]
        assert len(mensajes) == 2
        assert 'Estado inicial: Programa iniciado correctamente' in mensajes[0]
        assert 'Estado final: Programa iniciado correctamente' in mensajes[1]


def test_run_estado_erroneo(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value='EstadoApp.IMPOSIBLE'),):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 1
    assert len(mensajes) == 2
    assert 'Estado inicial: EstadoApp.IMPOSIBLE' in mensajes[0]
    assert 'La aplicación ha caido en un estado imposible' in mensajes[1]


def test_run_reset(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--reset']),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.INICIALIZACION_CORRECTA),
          patch('soyyo.app.reset', return_value=EstadoApp.PRIMER_ARRANQUE),
          patch('soyyo.app.setup', return_value=EstadoApp.SALIENDO_OK), ):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 0
    assert len(mensajes) == 2
    assert 'Estado inicial: Programa iniciado correctamente' in mensajes[0]
    assert 'Estado postreset: Primer arranque' in mensajes[1]


def test_run_captura(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--captura']),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.INICIALIZACION_CORRECTA),
          patch('soyyo.app.captura', return_value=EstadoApp.SALIENDO_OK)):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 0
    assert len(mensajes) == 1
    assert 'Estado inicial: Programa iniciado correctamente' in mensajes


def test_run_sin_keyring(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.SIN_KEYRING)):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 1
    assert len(mensajes) == 1
    assert 'Estado inicial: Sin keyring' in mensajes


def test_run_sin_pepper(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.SIN_PEPPER)):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 1
    assert len(mensajes) == 1
    assert 'Estado inicial: Sin pepper' in mensajes


def test_run_fichero_corrupto(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.FICHERO_CORRUPTO)):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 1
    assert len(mensajes) == 1
    assert 'Estado inicial: Fichero corrupto' in mensajes


def test_run_firma_invalida(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.FIRMA_INVALIDA)):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 1
    assert len(mensajes) == 1
    assert 'Estado inicial: Firma invalida' in mensajes


def test_run_saliendo_ok(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.SALIENDO_OK)):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 0
    assert len(mensajes) == 1
    assert 'Estado inicial: Saliendo OK' in mensajes


def test_run_saliendo_error(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.SALIENDO_ERROR)):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 1
    assert len(mensajes) == 1
    assert 'Estado inicial: Saliendo con error' in mensajes


def test_main(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo']),
          caplog.at_level(logging.DEBUG)):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 0
    assert len(mensajes) == 1
    assert 'Aplicación llamada sin argumentos.' in mensajes


def test_main_error_no_controlado(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', side_effect=Exception),):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 1
    assert len(mensajes) == 1
    assert 'Error no controlado.' in mensajes
