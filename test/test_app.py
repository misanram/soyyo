"""
Tests del módulo app.py
"""

from unittest.mock import patch

import pytest

from soyyo.app import Aplicacion, get_options, main
from soyyo.estados import EstadoSistema


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
        app = Aplicacion(None)
        assert app._comprueba_estado() == EstadoSistema.SIN_KEYRING


def test__comprueba_estado_primer_arranque():
    with (patch('soyyo.app.get_options'), patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=False)):
        app = Aplicacion(None)
        assert app._comprueba_estado() == EstadoSistema.PRIMER_ARRANQUE


def test__comprueba_estado_sin_pepper():
    with (patch('soyyo.app.get_options'), patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=True),
          patch('soyyo.app.chek_pepper', return_value=False)):
        app = Aplicacion(None)
        assert app._comprueba_estado() == EstadoSistema.SIN_PEPPER


def test__comprueba_estado_fichero_corrupto():
    with (patch('soyyo.app.get_options'), patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=True),
          patch('soyyo.app.chek_pepper', return_value=True),
          patch('soyyo.app.chek_integridad_json', return_value=False)):
        app = Aplicacion(None)
        assert app._comprueba_estado() == EstadoSistema.FICHERO_CORRUPTO


def test__comprueba_estado_firma_invalida():
    with (patch('soyyo.app.get_options'), patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=True),
          patch('soyyo.app.chek_pepper', return_value=True),
          patch('soyyo.app.chek_integridad_json', return_value=True),
          patch('soyyo.app.chek_firma', return_value=False)):
        app = Aplicacion(None)
        assert app._comprueba_estado() == EstadoSistema.FIRMA_INVALIDA


def test__comprueba_estado_todo_ok():
    with (patch('soyyo.app.get_options'), patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=True),
          patch('soyyo.app.chek_pepper', return_value=True),
          patch('soyyo.app.chek_integridad_json', return_value=True),
          patch('soyyo.app.chek_firma', return_value=True)):
        app = Aplicacion(None)
        assert app._comprueba_estado() == EstadoSistema.OK


def test__comprueba_estado_exception_en_chek(capsys):
    with (patch('soyyo.app.get_options'), patch('soyyo.app.chek_keyring', return_value=True),
          patch('soyyo.app.chek_almacen', return_value=True),
          patch('soyyo.app.chek_pepper', return_value=True),
          patch('soyyo.app.chek_integridad_json', return_value=True),
          patch('soyyo.app.chek_firma', side_effect=Exception)):
        with pytest.raises(SystemExit):
            main()
            app = Aplicacion(None)
            app._comprueba_estado()
    captured = capsys.readouterr()
    assert 'La aplicación no puede continuar.' in captured.out


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


def test_run_sin_pepper(capsys):
    with (patch.object(Aplicacion, '_comprueba_estado', return_value=EstadoSistema.SIN_PEPPER),
          patch('sys.argv', ['soyyo'])):
        with pytest.raises(SystemExit):
            main()
    captured = capsys.readouterr()
    assert 'No hay clave de firma en el sistema de almacenamiento seguro del sistema.' in captured.out


def test_run_fichero_corrupto(capsys):
    with (patch.object(Aplicacion, '_comprueba_estado', return_value=EstadoSistema.FICHERO_CORRUPTO),
          patch('sys.argv', ['soyyo'])):
        with pytest.raises(SystemExit):
            main()
    captured = capsys.readouterr()
    assert 'El almacén de datos es ilegible o está corrupto.' in captured.out


def test_run_firma_invalida(capsys):
    with (patch.object(Aplicacion, '_comprueba_estado', return_value=EstadoSistema.FIRMA_INVALIDA),
          patch('sys.argv', ['soyyo'])):
        with pytest.raises(SystemExit):
            main()
    captured = capsys.readouterr()
    assert 'El almacén de datos parece haber sido manipulado.' in captured.out


def test_main(capsys):
    with (patch.object(Aplicacion, '_comprueba_estado', return_value=EstadoSistema.OK),
          patch('sys.argv', ['soyyo'])):
        main()
    captured = capsys.readouterr()
    assert 'True' in captured.out
