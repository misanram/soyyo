"""
Mensajes que muestra el programa (esto puede que deaparezca o no...)
"""

MSG_SIN_KEYRING = """
    No hay un sistema de almacenamiento seguro disponible en este sistema.
        La aplicación no puede continuar.
        Para instalar uno consulte con el administrador de su sistema."""

MSG_SIN_PEPPER = """
    No hay clave de firma en el sistema de almacenamiento seguro del sistema.
        Las semillas almacenadas no son legibles
        Debe resetar la aplicación.
"""

MSG_FICHERO_CORRUPTO = """
    El almacén de datos es ilegible o está corrupto.
        Las semillas almacenadas no son legibles
        Debe resetar la aplicación."""

MSG_FIRMA_INVALIDA = """
    El almacén de datos parece haber sido manipulado.
        Las semillas almacenadas no son legibles
        Debe resetar la aplicación."""

MSG_SALIENDO_OK = """
    Aplicación finalizada."""

MSG_SALIENDO_ERROR = """
    La aplicación no puede continuar debido a un error."""

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

        Ello eliminará todas sus secreto TOTP almacenados

        Este paso es irreversible.
        Si/No/Cancelar: """
