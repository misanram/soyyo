## Instalación

### Dependencias del sistema

'''bash
$ sudo apt install libzbar0
'''

### Instalación del paquete

```bash
$ ./bin/pip install git+https://github.com/misanram/soyyo
```

### Una máquina de estados

La aplicación se plantea como una máquina de estados. Los estados están definidos en una Enum y la aplicación
consiste en un bucle que encierra una estructura ```if ... elif... else``` con una condición para cada estado definido.
Toda acción devuelve un estado de los que están definidos en la Enum y que debe importar previamente, por lo que no
pueden (deben) generarse estados imposibles.

### Como manejamos la autorización:

El programa funciona por opciones, cada opción que se solicita en el arranque ejecuta una acción y termina. Tener un
proceso separado de autorización previa a las acciones solictadas genera varios problemas. Cuando la autorización es
positiva el programa podría pasar a un estado de "AUTORIZADO" y permitir que el usuario realizara más tarde la
acción deseada. Esto genera por lo menos dos problemas:

* Habría que compartir el PIN del usaurio obtenido durante la autorización, entre acciones con lo que la acción
  "autorizar" además de devolver un estado, debería traspasar el PIN de alguna manera ... ¿Pasarlo como atributo de la
  instancia Aplicación? El PIN podría pasar horas desde que se solicita hasta que se usa almacenado en una variable
  en algún rincón de la memoria ... eso puede ser peligroso.
* Durante el tiempo que el usuario tarde en completar la acción, el almacen JSON podría ser manipulado lo que
  llevaría a inconsistencias de variados tipos.

### Almacenamiento de datos

Los TOTP (https://github.com/google/google-authenticator/wiki/Key-Uri-Format) se almacenan en un fichero JSON con
esta estructura:

```
{
    'version':  Número de la vesión del JSON
    'autorizacion': Diccionario con datos de autorización {
        'hash': el  hash calculado del pin
        'salt': la salt usada
    },
    'intentos': Número de PIN usados (intentos de PIN)
    'bloqueado_hasta': datetime en isoformat de cuando puede realizarse el próximo intento de acceder al programa
    'num_bloqueos': Número de bloqueo. 3 intentos fallidos suman un bloqueo. num_bloqueo define el tiempo de  bloeuado hasta
    'totp': Diccionario con los TOTP almacenados    {
        'uuid-generado': {
             'uri': datos raw del QR, 
             'issuer': el issuer,
              'account': la account,
              'nombre': 'issuer' (modificable por el usaurio),
              'secret' 'secret',
              'digits': int('digits'),
              'period': int('period'),
              'algoritmo': 'algorithm' | 'SHA1'
    }, 
    'firma': hash de los datos del JSON (todos los demás salvo la firma).
}
```


