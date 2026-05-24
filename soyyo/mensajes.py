"""
Mensajes que muestra el programa (esto puede que desaparezca o no...)
"""

MSG_SIN_KEYRING = """
    No hay un sistema de almacenamiento seguro disponible en este sistema.
        La aplicación no puede continuar.
        Para instalar uno consulte con el administrador de su sistema."""

MSG_SIN_PEPPER = """
    No hay clave de firma en el sistema de almacenamiento seguro del sistema.
        Los datos TOTP almacenados no son legibles
        Probablemente deba resetar la aplicación."""

MSG_FICHERO_CORRUPTO = """
    El almacén de datos es ilegible o está corrupto.
        Los datos TOTP almacenados no son legibles
        Probablemente deba resetar la aplicación."""

MSG_ERROR_LECTURA_ESCRITURA_ALMACEN_DATOS = """
    Ha ocurrido un error al leer o escribir en el almacen de datos..
        Reinicie la aplicación a ver si hay suerte lapróxima vez."""

MSG_FIRMA_INVALIDA = """
    El almacén de datos parece haber sido manipulado.
        Los datos TOTP almacenados no son legibles
        Probablemente deba resetar la aplicación."""

MSG_SALIENDO_OK = """
    Aplicación finalizada.
    """

MSG_SALIENDO_ERROR = """
    La aplicación finaliza debido a un error.
    """

MSG_ERROR_CAPTURA = """
    No se ha podido capturar una imagen.
    """

MSG_ERROR_DECODIFICA = """
    No se ha podido decodificar la imagen capturada.
    """

MSG_ERROR_APP_BLOQUEDA = """
    Demasiados errores en el PIN, .
    Aplicación bloqueada de forma irreversible."""

MSG_ERROR_APP_BLOQUEADA_TEMPORAL = """
    La aplicación está bloqueda de forma temporal.
    La apliacción se desbloqueara el %s"""

MSG_SETUP = """
    Debe crear un PIN para usar la aplicación.
    Manténgalo en secreto y no lo comparta.

    MUY IMPORTANTE: El PIN no puede recuperarse. Si lo olvida,
    no podrá acceder a los datos de la aplicación.

    - Use solamente caracteres numéricos.
    - Longitud: 8-20 caracteres."""

MSG_PROMPT_RESET = """
        ¡¡¡ATENCIÓN!!!

        Ha solicitado eliminar por completo toda la configuración.

        Ello eliminará todas sus secretos TOTP almacenados.

        Este paso es irreversible.
        Si/No/Cancelar: """

MSG_RESET_REALIZADO = """
        

        Reset realizado
"""
