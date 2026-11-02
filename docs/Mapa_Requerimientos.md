# Mapa de los 27 requerimientos

Cada funcionalidad conserva su número del documento original. La última columna
indica dónde se implementa y qué regla aplica el código. Los atributos de cada
clase están en el cuadro de su análisis y en su diagrama; el código usa los mismos
nombres, tipos y visibilidad.

| RF | Funcionalidad | Análisis | Implementación y comportamiento |
|---|---|---|---|
| 01 | Registro manual y automatizado; expediente único | [Grupo 01](../01_Registro_documental/Analisis_Registro_documental.md) | [registro_documental.py](../codigo/registro_documental.py): `NumeroExpediente.generar()` reserva el número AA + seis dígitos en SQLite; `ModoRegistro` distingue registro manual y automatizado. |
| 02 | Carga de archivos electrónicos | [Grupo 01](../01_Registro_documental/Analisis_Registro_documental.md) | [registro_documental.py](../codigo/registro_documental.py): `Documento.adjuntar_archivo()` asocia el archivo; `ArchivoElectronico.leer()` solo lee dentro de la ruta permitida. |
| 03 | Cargo externo e identificador interno | [Grupo 01](../01_Registro_documental/Analisis_Registro_documental.md) | [registro_documental.py](../codigo/registro_documental.py): `Tramite.generar_cargo()` crea una instantánea para trámites externos; `Cargo.texto()` muestra la fecha y hora de Perú. |
| 04 | Correo de recepción del trámite | [Grupo 04](../04_Notificaciones/Analisis_Notificaciones.md) | [notificaciones.py](../codigo/notificaciones.py): `notificar_cambio()` avisa la primera recepción; retomar la atención no genera un segundo aviso. |
| 05 | Clasificación documental | [Grupo 01](../01_Registro_documental/Analisis_Registro_documental.md) | [registro_documental.py](../codigo/registro_documental.py): `Tramite.clasificar()` valida categoría, tipo y prioridad. |
| 06 | Metadatos del trámite | [Grupo 01](../01_Registro_documental/Analisis_Registro_documental.md) | [registro_documental.py](../codigo/registro_documental.py): el constructor de `Tramite` valida cada metadato. |
| 07 | Seguimiento de estados | [Grupo 03](../03_Flujo_y_seguimiento/Analisis_Flujo_y_seguimiento.md) | [registro_documental.py](../codigo/registro_documental.py) y [flujo_y_seguimiento.py](../codigo/flujo_y_seguimiento.py): `Tramite.cambiar_estado()` solo admite transiciones válidas y devuelve un `CambioEstadoTramite`. |
| 08 | Notificaciones al personal y solicitantes | [Grupo 04](../04_Notificaciones/Analisis_Notificaciones.md) | [notificaciones.py](../codigo/notificaciones.py): `GestorNotificaciones` registra cada `Notificacion` y sus `IntentoEnvio` a través del contrato `ServicioCorreo`, sin duplicar eventos. |
| 09 | Historial de derivaciones | [Grupo 03](../03_Flujo_y_seguimiento/Analisis_Flujo_y_seguimiento.md) | [flujo_y_seguimiento.py](../codigo/flujo_y_seguimiento.py) y [registro_documental.py](../codigo/registro_documental.py): cada `Derivacion` conserva fechas y áreas; `Tramite.hoja_de_ruta()` las ordena. |
| 10 | Usuarios externos y sus trámites | [Grupo 02](../02_Usuarios_y_seguridad/Analisis_Usuarios_y_seguridad.md) | [usuarios_y_seguridad.py](../codigo/usuarios_y_seguridad.py): `Usuario` con `TipoUsuario` interno o externo; el trámite referencia a su remitente. |
| 11 | Acceso por roles | [Grupo 02](../02_Usuarios_y_seguridad/Analisis_Usuarios_y_seguridad.md) | [usuarios_y_seguridad.py](../codigo/usuarios_y_seguridad.py): `Rol` agrupa permisos y cada operación de los siete módulos comprueba `VISUALIZAR`, `MODIFICAR` o `APROBAR`. |
| 12 | Auditoría persistente | [Grupo 02](../02_Usuarios_y_seguridad/Analisis_Usuarios_y_seguridad.md) | [usuarios_y_seguridad.py](../codigo/usuarios_y_seguridad.py): `RegistroAuditoria.registrar()` asigna el identificador y guarda el evento en SQLite; `main.py` lo invoca tras cada creación, modificación y acceso. |
| 13 | Búsqueda por criterios | [Grupo 05](../05_Busqueda_y_archivo/Analisis_Busqueda_y_archivo.md) | [busqueda_y_archivo.py](../codigo/busqueda_y_archivo.py): `MotorBusqueda` aplica un `CriterioBusqueda`; las fechas se interpretan en la hora de Perú. |
| 14 | Activos, archivados y motivo del desarchivo | [Grupo 05](../05_Busqueda_y_archivo/Analisis_Busqueda_y_archivo.md) | [registro_documental.py](../codigo/registro_documental.py) y [busqueda_y_archivo.py](../codigo/busqueda_y_archivo.py): la búsqueda no desarchiva; `Documento.desarchivar()` exige un motivo y devuelve un `Desarchivamiento`. |
| 15 | Validación de firma digital | [Grupo 07](../07_Integraciones/Analisis_Integraciones.md) | [integraciones.py](../codigo/integraciones.py): `AdaptadorValidacionFirma` vincula la respuesta al SHA-256 del contenido; sin firmas o con error no se considera válida. |
| 16 | Solicitud de visto bueno | [Grupo 03](../03_Flujo_y_seguimiento/Analisis_Flujo_y_seguimiento.md) | [registro_documental.py](../codigo/registro_documental.py): `Tramite.solicitar_visto_bueno()` deja el trámite pendiente hasta la resolución del jefe. |
| 17 | Aviso y resolución del visto bueno | [Grupo 03](../03_Flujo_y_seguimiento/Analisis_Flujo_y_seguimiento.md) | [notificaciones.py](../codigo/notificaciones.py) y [flujo_y_seguimiento.py](../codigo/flujo_y_seguimiento.py): `notificar_solicitud()` avisa al jefe; `SolicitudVistoBueno.resolver()` solo lo acepta del jefe vigente, aunque haya cambiado la jefatura. |
| 18 | Archivadores y conservación | [Grupo 05](../05_Busqueda_y_archivo/Analisis_Busqueda_y_archivo.md) | [registro_documental.py](../codigo/registro_documental.py) y [busqueda_y_archivo.py](../codigo/busqueda_y_archivo.py): `Documento.archivar()` registra el archivador y la `PoliticaConservacion` aplicada. |
| 19 | Ubicación y eliminación de archivos | [Grupo 05](../05_Busqueda_y_archivo/Analisis_Busqueda_y_archivo.md) | [registro_documental.py](../codigo/registro_documental.py): la eliminación exige plazo vencido y autorización; TI confirma cada archivo y un documento solo físico se elimina como registro. |
| 20 | Reportes automáticos | [Grupo 06](../06_Reportes/Analisis_Reportes.md) | [reportes.py](../codigo/reportes.py): tres especializaciones de `Reporte`; `ProgramacionReporte` las ejecuta a diario o cada semana. |
| 21 | Personalización y exportación | [Grupo 06](../06_Reportes/Analisis_Reportes.md) | [reportes.py](../codigo/reportes.py): `personalizar()` elige y ordena columnas; `ExportadorExcel` y `ExportadorPDF` producen `.xlsx` y `.pdf` reales. |
| 22 | Interoperabilidad PIDE | [Grupo 07](../07_Integraciones/Analisis_Integraciones.md) | [integraciones.py](../codigo/integraciones.py): `AdaptadorPIDE` confirma solo la respuesta con su correlación; una respuesta ambigua queda indeterminada. |
| 23 | Interfaz intuitiva por perfil | [Transversal](#rf-23--requisito-transversal-de-interfaz) | Pendiente; la entrega incluye una demostración de consola. |
| 24 | Asignación masiva | [Grupo 03](../03_Flujo_y_seguimiento/Analisis_Flujo_y_seguimiento.md) | [flujo_y_seguimiento.py](../codigo/flujo_y_seguimiento.py): `asignar_masivamente()` rechaza documentos repetidos, inactivos o ya asignados. |
| 25 | Derivación masiva y área de inicio | [Grupo 03](../03_Flujo_y_seguimiento/Analisis_Flujo_y_seguimiento.md) | [flujo_y_seguimiento.py](../codigo/flujo_y_seguimiento.py): `derivar_masivamente()` crea una derivación por trámite y `ConfiguracionDerivacion` resuelve el área inicial; solo deriva la dependencia que tiene el trámite. |
| 26 | Memorandos múltiples | [Grupo 04](../04_Notificaciones/Analisis_Notificaciones.md) | [notificaciones.py](../codigo/notificaciones.py): `Memorando` hereda de `Documento`, exige correos institucionales y envía una notificación por destinatario. |
| 27 | Corrección de derivación pendiente | [Grupo 03](../03_Flujo_y_seguimiento/Analisis_Flujo_y_seguimiento.md) | [flujo_y_seguimiento.py](../codigo/flujo_y_seguimiento.py): `Derivacion.corregir()` solo actúa antes de la aceptación; conserva la original y registra el motivo en `CorreccionDerivacion`. |

## RF-23 · Requisito transversal de interfaz

> El Sistema de Gestión Documental (SGD) debe contar con una interfaz de usuario intuitiva, fácil de usar para los diferentes perfiles de usuarios (administrativos, gestores, directivos).

Este requisito afecta a los siete grupos. La interfaz debe mostrar al usuario
las acciones que tiene autorizadas, el estado del trámite y los resultados de sus
operaciones con mensajes comprensibles. Los perfiles, recorridos y criterios de
usabilidad deben validarse con la universidad.

Las clases del dominio mantienen sus responsabilidades: la interfaz usa sus
operaciones y respeta sus permisos. Por eso el requisito no añade un atributo
artificial como `intuitivo` ni duplica clases por perfil. En esta entrega,
`codigo/main.py` es una demostración de consola; la interfaz gráfica del SIIGE
queda por desarrollar.

# Modelo y decisiones de implementación

## Clases por grupo

Una clase compartida aparece en cada grupo que la estudió, pero se define una sola vez. En total son **49 clases, 230 atributos privados y 47 propiedades públicas**, iguales a los diagramas.

| Grupo | Módulo | Clases del diagrama |
|---|---|---|
| 01 · Registro documental | `registro_documental.py` | `Tramite`, `Documento`, `NumeroExpediente`, `ArchivoElectronico`, `Cargo`, `Categoria`, `TipoDocumento`, `Prioridad` |
| 02 · Usuarios y seguridad | `usuarios_y_seguridad.py` | `Usuario`, `Rol`, `RegistroAuditoria` |
| 03 · Flujo y seguimiento | `flujo_y_seguimiento.py` | `Tramite`¹, `CambioEstadoTramite`, `Derivacion`, `Dependencia`, `SolicitudVistoBueno`, `AsignacionDocumento`, `Proveido`, `ConfiguracionDerivacion`, `CorreccionDerivacion` |
| 04 · Notificaciones | `notificaciones.py` | `Notificacion`, `IntentoEnvio`, `GestorNotificaciones`, `Memorando`, `ServicioCorreo` |
| 05 · Búsqueda y archivo | `busqueda_y_archivo.py` | `CriterioBusqueda`, `MotorBusqueda`, `Documento`¹, `Desarchivamiento`, `Archivador`, `PoliticaConservacion`, `RegistroArchivamiento`, `ArchivoElectronico`¹, `RegistroEliminacion` |
| 06 · Reportes | `reportes.py` | `Reporte`, `ReporteEstadoTramites`, `ReporteTiemposRespuesta`, `ReporteCargaTrabajo`, `ResultadoReporte`, `ProgramacionReporte`, `FiltroReporte`, `ExportadorReporte`, `ExportadorExcel`, `ExportadorPDF` |
| 07 · Integraciones | `integraciones.py` | `ValidacionFirma`, `ResultadoFirma`, `ServicioValidacionFirma`, `AdaptadorValidacionFirma`, `EntidadInteroperante`, `IntercambioDocumentario`, `ServicioInteroperabilidad`, `AdaptadorPIDE` |
| Programa general | `main.py` | Ninguna entidad nueva: crea y coordina los objetos de los siete módulos y registra la auditoría. |

¹ Definida en `registro_documental.py`.

Las enumeraciones y contratos técnicos se encuentran en el módulo de su funcionalidad.

## Visibilidad y encapsulamiento

Los atributos del modelo se escriben como `__atributo`, tal como aparecen en los diagramas. `@property` implementa las propiedades públicas. Las propiedades marcadas `{readOnly}` no tienen setter y las colecciones públicas se entregan como tuplas o conjuntos inmutables.

`consultar()` es una operación de lectura que permite revisar los datos del objeto sin habilitar la modificación directa de sus contenedores. Los objetos relacionados conservan su identidad y sus propias reglas. Este método no implementa permisos de usuario: el control de acceso se aplica en las operaciones de negocio y debe reforzarse en la futura capa de aplicación.

No se han agregado atributos protegidos, porque los diagramas aprobados no los contienen. Algunos métodos internos empiezan con `_`; eso no cambia la visibilidad de los atributos del modelo. La convención `__` de Python evita accesos accidentales; no sustituye la autenticación.

Los diagramas originales presentan atributos y propiedades. Para ejecutar el modelo se han añadido constructores y métodos que concretan los requerimientos, sin agregar atributos a las entidades. Las firmas de esos métodos pueden incorporarse después al compartimento de operaciones UML.

## Herencia y realización

| Implementación | Relación del diagrama |
|---|---|
| `Memorando(Documento)` | Herencia. |
| `ReporteEstadoTramites(Reporte)` | Herencia. |
| `ReporteTiemposRespuesta(Reporte)` | Herencia. |
| `ReporteCargaTrabajo(Reporte)` | Herencia. |
| `ExportadorExcel(ExportadorReporte)` | Realización de contrato mediante clase abstracta. |
| `ExportadorPDF(ExportadorReporte)` | Realización de contrato mediante clase abstracta. |
| `AdaptadorValidacionFirma(ServicioValidacionFirma)` | Realización de contrato mediante clase abstracta. |
| `AdaptadorPIDE(ServicioInteroperabilidad)` | Realización de contrato mediante clase abstracta. |

## Reglas de negocio verificadas

Las reglas se implementan en los métodos; las entidades, atributos y propiedades de los diagramas no cambian. Cada regla tiene al menos una prueba en `tests/test_sgd_modular.py`.

| Tema | Regla protegida |
|---|---|
| Fecha de recepción | El primer cambio a atención registra la fecha y las reanudaciones la conservan. |
| Avisos de recepción | Retomar la atención desde observación o visto bueno no produce una segunda recepción. |
| Intentos de envío | El identificador se valida antes de llamar al servicio de correo. |
| Número de expediente | Dos objetos con el mismo número comparan por valor. |
| Persistencia | Las escrituras de expedientes y auditoría usan un punto de recuperación SQL y respetan la transacción del llamador. |
| Auditoría | `RegistroAuditoria.registrar()` asigna el identificador y persiste el evento (RF-12: «debe almacenarse en base de datos»). |
| Jefatura | El jefe debe ser un usuario interno; `designar_jefe()` exige el permiso `APROBAR` (RF-16: su modificación «debe estar autorizada»). |
| Visto bueno | Resuelve el jefe vigente aunque haya cambiado la jefatura; la solicitud conserva a quién se dirigió y quién resolvió (RF-16). |
| Derivaciones | Solo la dependencia que tiene el trámite puede derivarlo. Un trámite finalizado o pendiente de visto bueno bloquea nuevas derivaciones y su aceptación. |
| Archivo | Al volver a archivar se conservan la política y la fecha original de cómputo; los datos inválidos no cambian el estado. |
| Eliminación | Un documento solo físico puede eliminarse; si tiene archivos, TI confirma cada uno (RF-19). |
| Fechas locales | Las búsquedas por fecha y el cargo usan la hora de Perú; los instantes se guardan en UTC. |
| Reportes | `generar()` exige un solicitante autorizado; las filas se copian en profundidad con sus parámetros; la programación transmite el calendario hábil. |
| Personalización y exportación | El constructor y `personalizar()` aplican las mismas reglas de columnas. Excel guarda como texto las celdas que parecen fórmulas. |
| Tipos | Los filtros distinguen fecha de fecha-hora; los tiempos de espera deben ser finitos. |

Si el llamador abre una transacción SQLite, le corresponde confirmarla o revertirla. Fuera de una transacción previa, cada escritura se confirma al liberar su punto de recuperación.

## Tipos auxiliares que se concretaron para ejecutar el modelo

Los nombres de estos tipos ya figuraban en los atributos del análisis. Como sus valores no se habían precisado, el código adopta los siguientes valores de prototipo; no representan plazos ni reglas oficiales de la universidad.

| Tipo | Valores del prototipo |
|---|---|
| `UnidadPlazo` | `DIAS`, `MESES`, `ANIOS`. |
| `ResultadoEliminacion` | `CONFIRMADA`, `FALLIDA`. |
| `EventoMedicion` | `REGISTRO`, `RECEPCION`, `FINALIZACION`. |
| `UnidadTiempo` | `SEGUNDOS`, `MINUTOS`, `HORAS`. |
| `AgrupacionCarga` | `USUARIO`, `DEPENDENCIA`. |
| `UnidadCarga` | `DOCUMENTOS`, `TRAMITES`. |
| `FrecuenciaReporte` | `DIARIA`, `SEMANAL`. |
| `OrigenEjecucion` | `MANUAL`, `PROGRAMADA`. |

El requisito AA + seis dígitos implica **ocho dígitos**. El ejemplo `2478965` del documento tiene siete; la implementación sigue la regla escrita y rechaza ese ejemplo como formato inválido.

## Contratos y adaptadores técnicos

`RepositorioDocumentos`, `RepositorioNotificaciones`, `RepositorioReportes` y `ProveedorCredenciales` son contratos técnicos que ya aparecen como tipos de atributos. Se expresan con `Protocol`; no son entidades nuevas del dominio.

`_RepositorioDemo` y `_CorreoDemo` se utilizan exclusivamente para la demostración y las pruebas. El primero conserva datos en memoria; el segundo imprime un mensaje y devuelve un identificador de demostración. No representan un envío real.

Los adaptadores de firma y PIDE reciben una función `transporte(direccion, solicitud, tiempo_espera, credenciales)`. La universidad debe facilitar el contrato real para escribir esa función. El código no presupone que PIDE use este formato interno:

- Firma: el transporte devuelve `consulta_completada`, una lista `firmas` y, opcionalmente, `referencia`. Cada firma contiene `referencia`, `estado` y, opcionalmente, `firmante` y `detalle`.
- Interoperabilidad: devuelve `id_correlacion` y una confirmación con `referencia`, o un rechazo explícito. Una respuesta ambigua o un error de transporte dejan el intercambio como indeterminado, sin reenvío automático.

## Alcance de la implementación

Se entrega un modelo POO ejecutable y verificable, preparado para evolucionar a una aplicación. Los números de expediente y la auditoría tienen operaciones de persistencia SQLite. Los demás repositorios se conectan mediante contratos; su implementación de demostración es en memoria.

Las operaciones devuelven registros de cambios, archivamientos, correcciones e intentos. La futura capa de aplicación debe conservarlos, coordinar notificaciones y auditoría, y aplicar transacciones al persistir cambios relacionados. Los identificadores de esos registros se suministran por parámetro y su unicidad corresponde al repositorio. El número de expediente y el identificador de auditoría se generan aquí de forma persistente.

Los reportes de tiempo admiten un calendario institucional suministrado como función. El repositorio de demostración solo conoce el estado actual, la recepción y la dependencia destinataria: no reconstruye cortes históricos, no conoce el evento de finalización y no filtra por responsable. Un repositorio real puede aportar esos datos mediante el mismo contrato. El planificador externo debe invocar periódicamente `ejecutar_si_corresponde()`.

La plantilla institucional del cargo, las políticas P.C.D.A., las credenciales, los servicios reales y la interfaz SIIGE se incorporarán cuando sus contratos y configuraciones estén disponibles. No se fijan plazos oficiales ni direcciones de servicios reales dentro del código.

[Volver al índice](../README.md)
