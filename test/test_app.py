"""
Tests del módulo app.py
"""
import argparse
import importlib.util
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from unittest.mock import patch

import pytest  # noqa

from soyyo.app import (Aplicacion, configura_argparser, configurar_i18n, configurar_logging, main)
from soyyo.constantes import EstadoApp
from .conftest import prefix_temporal


def test_configurar_i18n_sin_locale(caplog):
    """
    Verifica que cuando no hay locale configurado, se registra un warning
    """
    with patch('locale.getlocale', return_value=(None, None)):
        configurar_i18n()

        assert 'No se encontró traducción para None' in caplog.text
        assert caplog.records[-1].levelname == 'WARNING'


def test_configurar_i18n_sin_archivo_traduccion(caplog):
    """
    Verifica que cuando no existe el archivo .mo, se registra un warning
    """

    locale_actual = 'es_ES'
    with (patch('locale.getlocale', return_value=(locale_actual, None)),
          patch('os.path.exists', return_value=False)):
        configurar_i18n()
        assert f'No se encontró traducción para {locale_actual}' in caplog.text
        assert caplog.records[-1].levelname == 'WARNING'


def test_configurar_i18n_instala_traduccion():
    configurar_i18n()
    assert callable(argparse._)  # type: ignore
    assert callable(argparse.ngettext)  # type: ignore


def test_configurar_i18n_traduce_mensaje_real():
    """
    Verifica que configurar_i18n carga y aplica las traducciones de la app con locale es_ES.
    """

    locale_actual = 'es_ES'
    with patch('locale.getlocale', return_value=(locale_actual, None)):
        configurar_i18n()
    assert argparse._(  # type: ignore
            'show this help message and exit') == 'Muestra este mensaje de ayuda y termina'


def test_configura_argparser_no_args():
    with patch('sys.argv', ['soyyo']):
        args = configura_argparser()
        assert all(vars(args).values()) is False


def test_configura_argparser_reset():
    with patch('sys.argv', ['soyyo', '--reset']):
        argumentos = configura_argparser().parse_args()
        assert argumentos.reset is True


def test_configura_argparser_captura():
    with patch('sys.argv', ['soyyo', '--captura']):
        argumentos = configura_argparser().parse_args()
        assert argumentos.captura is True


def test_configura_argparser_lista():
    with patch('sys.argv', ['soyyo', '--lista']):
        argumentos = configura_argparser().parse_args()
        assert argumentos.lista is True


def test_run_llama_a_comprobar_estado(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.INICIALIZACION_CORRECTA),):
        # @formatter:on
        aplicacion = Aplicacion(configura_argparser().parse_args())
        aplicacion.run()
        mensajes = [r.message for r in caplog.records]
        assert len(mensajes) == 2
        assert 'Estado inicial: Programa iniciado correctamente' in mensajes[0]
        assert 'Estado final: Programa iniciado correctamente' in mensajes[1]


def test_run_estado_erroneo(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          patch('soyyo.app.configurar_logging'),
          patch('soyyo.app.configurar_i18n'),
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


def test_run_sistema_incompatible(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          patch('soyyo.app.configurar_logging'),
          patch('soyyo.app.configurar_i18n'),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.SISTEMA_INCOMPATIBLE)):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 1
    assert len(mensajes) == 1
    assert 'Estado inicial: Sistema incompatible (no linux o no terminal)' in mensajes


def test_run_sin_keyring(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--test']),
          patch('soyyo.app.configurar_logging'),
          patch('soyyo.app.configurar_i18n'),
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
          patch('soyyo.app.configurar_logging'),
          patch('soyyo.app.configurar_i18n'),
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
          patch('soyyo.app.configurar_logging'),
          patch('soyyo.app.configurar_i18n'),
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
          patch('soyyo.app.configurar_logging'),
          patch('soyyo.app.configurar_i18n'),
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
          patch('soyyo.app.configurar_logging'),
          patch('soyyo.app.configurar_i18n'),
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
          patch('soyyo.app.configurar_logging'),
          patch('soyyo.app.configurar_i18n'),
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
          patch('soyyo.app.configurar_logging'),
          patch('soyyo.app.configurar_i18n'),
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
          patch('soyyo.app.configurar_logging'),
          patch('soyyo.app.configurar_i18n'),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', side_effect=Exception),):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 1
    assert len(mensajes) == 1
    assert 'Error no controlado.' in mensajes


def test_run_reset(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--reset']),
          patch('soyyo.app.configurar_logging'),
          patch('soyyo.app.configurar_i18n'),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.INICIALIZACION_CORRECTA),
          patch('soyyo.app.reset', return_value=EstadoApp.PRIMER_ARRANQUE),
          patch('soyyo.app.setup', return_value=EstadoApp.SALIENDO_OK), ):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 0
    assert len(mensajes) == 4
    assert 'Estado inicial: Programa iniciado correctamente' in mensajes[0]
    assert 'Acción solicitada: reset' in mensajes[1]
    assert 'Estado postreset: Primer arranque' in mensajes[2]
    assert 'Acción solicitada: setup' in mensajes[3]


def test_run_captura(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--captura']),
          patch('soyyo.app.configurar_logging'),
          patch('soyyo.app.configurar_i18n'),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.INICIALIZACION_CORRECTA),
          patch('soyyo.app.captura', return_value=EstadoApp.SALIENDO_OK)):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 0
    assert len(mensajes) == 2
    assert 'Estado inicial: Programa iniciado correctamente' in mensajes[0]
    assert 'Acción solicitada: captura' in mensajes[1]


def test_run_lista(caplog):
    # @formatter:off
    with (patch('sys.argv', ['soyyo', '--lista']),
          patch('soyyo.app.configurar_logging'),
          patch('soyyo.app.configurar_i18n'),
          caplog.at_level(logging.DEBUG),
          patch('soyyo.app.comprobar_estado', return_value=EstadoApp.INICIALIZACION_CORRECTA),
          patch('soyyo.app.lista', return_value=EstadoApp.SALIENDO_OK)):
        # @formatter:on
        with pytest.raises(SystemExit) as exc:
            main()
    mensajes = [r.message for r in caplog.records]
    assert exc.value.code == 0
    assert len(mensajes) == 2
    assert 'Estado inicial: Programa iniciado correctamente' in mensajes[0]
    assert 'Acción solicitada: lista' in mensajes[1]


def test_configurar_logging_crea_file_handler(prefix_temporal):
    """
    El RotatingFileHandler debe crearse con los parámetros correctos.
    """

    configurar_logging()
    handler = next(h for h in logging.root.handlers if isinstance(h, RotatingFileHandler))
    assert Path(handler.baseFilename).name == 'soyyo.log'
    assert handler.maxBytes == 1_000_000
    assert handler.backupCount == 5


def test_configurar_logging_logger_raiz(prefix_temporal):
    """
    Comprueba el nivel del logger raiz.
    """

    configurar_logging()
    assert logging.root.level == logging.WARNING


@pytest.mark.parametrize('logger, nivel', [('soyyo', logging.DEBUG), ('py.warnings', logging.WARNING), ])
def test_configurar_logging_logger_especifico(prefix_temporal, logger, nivel):
    """
    Comprueba el nivel de los logger.
    """

    configurar_logging()
    assert logging.getLogger(logger).level == nivel


def test_configurar_logging_warnings_no_se_propagan(prefix_temporal, tmp_path):
    """
    py.warnings no debe propagar al logger raíz.
    """

    configurar_logging()

    # Añadimos un handler temporal al root para capturar lo que llegue
    mensajes_root = []

    class HandlerCapturador(logging.Handler):
        """
        Clase para test
        """

        def emit(self, record):
            """
            Función para test
            """
            mensajes_root.append(record.getMessage())

    logging.root.addHandler(HandlerCapturador())
    logging.root.setLevel(logging.WARNING)

    # Creamos un módulo Python temporal en el directorio tmpdir
    modulo_path = Path(tmp_path) / 'modulo_con_warning.py'
    modulo_path.write_text("""
import warnings

def funcion_que_genera_warning():
    \"\"\"Esta función simula el código de un módulo importado\"\"\"
    warnings.warn('Warning desde módulo importado', UserWarning)
""")

    # Importamos dinámicamente ese módulo
    spec = importlib.util.spec_from_file_location(
            'modulo_con_warning',
            modulo_path
            )
    if spec is None:
        raise ImportError(f'No se pudo cargar el módulo desde {modulo_path}')
    modulo = importlib.util.module_from_spec(spec)
    sys.modules['modulo_con_warning'] = modulo
    if spec is None or spec.loader is None:
        raise ImportError(f'No se pudo cargar el módulo desde {modulo_path}')
    spec.loader.exec_module(modulo)

    # Ejecutamos la función que genera el warning
    modulo.funcion_que_genera_warning()

    # Forzamos la escritura de los logs pendientes
    for handler in logging.root.handlers:
        handler.flush()

    # Leemos el archivo de log y verificamos
    log_path = Path(sys.prefix) / '../soyyo.log'
    log_content = log_path.read_text()

    assert 'Warning desde módulo importado' in log_content
    assert 'Warning desde módulo importado' not in str(mensajes_root)


def test_configurar_logging_warning_modulo_importado_se_registra(prefix_temporal, tmp_path):
    """
    Prueba que los warnings generados por módulos importados quedan registrados en el archivo de log.
    """

    configurar_logging()

    # Creamos un módulo Python temporal en el directorio tmpdir
    modulo_path = Path(tmp_path) / 'modulo_con_warning.py'
    modulo_path.write_text("""
import warnings

def funcion_que_genera_warning():
    \"\"\"Esta función simula el código de un módulo importado\"\"\"
    warnings.warn('Warning desde módulo importado', UserWarning)
""")

    # Importamos dinámicamente ese módulo
    spec = importlib.util.spec_from_file_location(
            'modulo_con_warning',
            modulo_path
            )
    if spec is None:
        raise ImportError(f'No se pudo cargar el módulo desde {modulo_path}')
    modulo = importlib.util.module_from_spec(spec)
    sys.modules['modulo_con_warning'] = modulo
    if spec is None or spec.loader is None:
        raise ImportError(f'No se pudo cargar el módulo desde {modulo_path}')
    spec.loader.exec_module(modulo)

    # Ejecutamos la función que genera el warning
    modulo.funcion_que_genera_warning()

    # Forzamos la escritura de los logs pendientes
    for handler in logging.root.handlers:
        handler.flush()

    # Leemos el archivo de log y verificamos
    log_path = Path(sys.prefix) / '../soyyo.log'
    log_content = log_path.read_text()

    # Comprobaciones
    assert "Warning desde módulo importado" in log_content
    assert "WARN" in log_content or "WARNING" in log_content
    assert "modulo_con_warning" in log_content  # Debe aparecer el nombre del módulo
