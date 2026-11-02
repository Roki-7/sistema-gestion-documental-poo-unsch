# Sistema de Gestión Documental · UNSCH

**Análisis, diseño UML e implementación orientada a objetos en Python.**

Proyecto académico del SGD a integrar en el SIIGE de la Universidad Nacional
de San Cristóbal de Huamanga. Los 27 requerimientos se organizan en siete grupos;
la interfaz de usuario se trata como requisito transversal.

**49 clases del modelo · 230 atributos privados · 47 propiedades públicas · 60 pruebas**

## Explorar el proyecto

| Grupo | Análisis | Diagrama UML | Código |
|---|---|---|---|
| 01 · Registro documental | [Leer](01_Registro_documental/Analisis_Registro_documental.md) | [Ver](01_Registro_documental/Diagrama_01_Registro_documental.png) | [registro_documental.py](codigo/registro_documental.py) |
| 02 · Usuarios y seguridad | [Leer](02_Usuarios_y_seguridad/Analisis_Usuarios_y_seguridad.md) | [Ver](02_Usuarios_y_seguridad/Diagrama_02_Usuarios_y_seguridad.png) | [usuarios_y_seguridad.py](codigo/usuarios_y_seguridad.py) |
| 03 · Flujo y seguimiento | [Leer](03_Flujo_y_seguimiento/Analisis_Flujo_y_seguimiento.md) | [Ver](03_Flujo_y_seguimiento/Diagrama_03_Flujo_y_seguimiento.png) | [flujo_y_seguimiento.py](codigo/flujo_y_seguimiento.py) |
| 04 · Notificaciones | [Leer](04_Notificaciones/Analisis_Notificaciones.md) | [Ver](04_Notificaciones/Diagrama_04_Notificaciones.png) | [notificaciones.py](codigo/notificaciones.py) |
| 05 · Búsqueda y archivo | [Leer](05_Busqueda_y_archivo/Analisis_Busqueda_y_archivo.md) | [Ver](05_Busqueda_y_archivo/Diagrama_05_Busqueda_y_archivo.png) | [busqueda_y_archivo.py](codigo/busqueda_y_archivo.py) |
| 06 · Reportes | [Leer](06_Reportes/Analisis_Reportes.md) | [Ver](06_Reportes/Diagrama_06_Reportes.png) | [reportes.py](codigo/reportes.py) |
| 07 · Integraciones | [Leer](07_Integraciones/Analisis_Integraciones.md) | [Ver](07_Integraciones/Diagrama_07_Integraciones.png) | [integraciones.py](codigo/integraciones.py) |

El [mapa de los 27 requerimientos](docs/Mapa_Requerimientos.md) relaciona cada RF con su
análisis y su código, y documenta las clases por grupo, la herencia, las reglas verificadas
y el alcance de la implementación.

## Estructura

| Carpeta | Contenido |
|---|---|
| `01_` a `07_` | Análisis de cada grupo y su diagrama de clases en PNG. |
| `diagramas/` | Editable draw.io con una pestaña por grupo. |
| `codigo/` | Los siete módulos del modelo y el programa general `main.py`. |
| `tests/` | Pruebas de comportamiento del modelo. |
| `docs/` | Mapa de requerimientos y decisiones de implementación. |
| `.github/workflows/` | Ejecución automática de las pruebas en GitHub Actions. |

Si cambias el modelo, actualiza en conjunto el análisis del grupo, su pestaña
del draw.io, la imagen PNG y el código.

## Ejecutar y comprobar

Con **Python 3.11 o superior** (comprobado en 3.13), desde la raíz de este repositorio:

```powershell
python -m pip install -r requirements.txt
python codigo/main.py
python -m unittest discover -s tests -v
```

[main.py](codigo/main.py) recorre los siete grupos y demuestra encapsulamiento,
abstracción, herencia y polimorfismo. GitHub Actions ejecuta las mismas pruebas
en Python 3.11, 3.12 y 3.13.

## Publicar en GitHub

```powershell
git init
git add .
git commit -m "Integra analisis, diagramas UML y modelo POO del SGD UNSCH"
git branch -M main
git remote add origin <URL-del-repositorio>
git push -u origin main
```

`.gitignore` excluye las cachés de Python, los entornos virtuales y las bases de
datos locales.

**Alcance:** modelo POO ejecutable con una demostración de consola. Los repositorios
Demo son en memoria; la auditoría y los expedientes se guardan en SQLite. La interfaz SIIGE
y las conexiones reales de correo, firma digital y PIDE se incorporarán con sus
contratos institucionales.
