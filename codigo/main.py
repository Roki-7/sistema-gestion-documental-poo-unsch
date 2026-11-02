"""Programa general de los siete grupos del SGD–UNSCH.

Ejecutar desde la raíz del repositorio: python codigo/main.py
Los módulos contienen el modelo. Aquí se crean y conectan sus objetos.
Los adaptadores Demo no envían correos ni contactan con servicios reales.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import closing
from datetime import datetime
import secrets
import sqlite3

import registro_documental as registro  # 01 · Registro documental
import usuarios_y_seguridad as seguridad  # 02 · Usuarios y seguridad
import flujo_y_seguimiento as flujo  # 03 · Flujo y seguimiento
import notificaciones as avisos  # 04 · Notificaciones
import busqueda_y_archivo as archivos  # 05 · Búsqueda y archivo
import reportes as informes  # 06 · Reportes
import integraciones as servicios  # 07 · Integraciones


class _RepositorioDemo:
    """Persistencia en memoria para explorar la colaboración entre los siete grupos."""
    def __init__(self, documentos: tuple[registro.Documento, ...] = ()) -> None:
        self.documentos = list(documentos)
        self.notificaciones: dict[int, avisos.Notificacion] = {}
        self.intentos: dict[int, avisos.IntentoEnvio] = {}

    def listar_documentos(self) -> tuple[registro.Documento, ...]:
        return tuple(self.documentos)

    def guardar(self, notificacion: avisos.Notificacion) -> None:
        datos = notificacion.consultar()
        for otra in self.notificaciones.values():
            d = otra.consultar()
            if d["id_notificacion"] != datos["id_notificacion"] and (
                d["id_evento_origen"], d["correo_destinatario"]) == (
                datos["id_evento_origen"], datos["correo_destinatario"]):
                raise ValueError("Evento y destinatario duplicados.")
        anterior = self.notificaciones.get(datos["id_notificacion"])
        if anterior is not None and anterior is not notificacion:
            raise ValueError("El ID de notificación ya existe.")
        self.notificaciones[datos["id_notificacion"]] = notificacion

    def guardar_intento(self, intento: avisos.IntentoEnvio) -> None:
        clave = intento.consultar()["id_intento"]
        if clave in self.intentos:
            raise ValueError("El ID de intento ya existe.")
        self.intentos[clave] = intento

    def existe_evento(self, evento: str, correo: str) -> bool:
        return any(n.consultar()["id_evento_origen"] == evento
                   and n.consultar()["correo_destinatario"] == correo for n in self.notificaciones.values())

    def consultar(self, tipo: str, filtros: Mapping[str, object],
                  fecha_corte: datetime) -> list[dict[str, object]]:
        filas = []
        vistos = set()
        # El adaptador demo solo informa del estado actual. Para cortes históricos
        # se necesita un repositorio basado en CambioEstadoTramite.
        for documento in self.documentos:
            tramite = documento.consultar()["tramite"]
            t = tramite.consultar()
            if t["fecha_hora_registro"] > fecha_corte:
                continue
            fecha = seguridad.fecha_local(t["fecha_hora_registro"])
            if filtros["fecha_desde"] and fecha < filtros["fecha_desde"]:
                continue
            if filtros["fecha_hasta"] and fecha > filtros["fecha_hasta"]:
                continue
            if filtros["dependencia"] and t["destinatario"] is not filtros["dependencia"]:
                continue
            if filtros["estado_tramite"] and t["estado"] is not filtros["estado_tramite"]:
                continue
            if filtros["responsable"] is not None:
                raise ValueError("El repositorio demo no almacena asignaciones para filtrar por responsable.")
            expediente = str(t["numero_expediente"])
            if tipo in {"estado", "tiempos"}:
                if expediente in vistos:
                    continue
                vistos.add(expediente)
            if tipo == "estado":
                filas.append({"estado": t["estado"].value})
            elif tipo == "tiempos":
                filas.append({"expediente": expediente, "registro": t["fecha_hora_registro"],
                              "recepcion": t["fecha_recepcion"], "finalizacion": None})
            elif tipo == "carga":
                # No se atribuye una carga a un responsable que no está registrado.
                filas.append({"dependencia": t["destinatario"].consultar()["nombre"],
                              "usuario": "SIN_ASIGNACION", "documento": id(documento), "tramite": expediente})
            else:
                raise ValueError("Tipo de reporte desconocido.")
        return filas


class _CorreoDemo(avisos.ServicioCorreo):
    """Solo demuestra el contrato; no envía mensajes por Internet."""
    __slots__ = ()

    def enviar(self, remitente: str, destinatario: str, asunto: str, mensaje: str) -> str:
        print(f"  [Correo de demostración] {destinatario}: {asunto}")
        return "demo-" + secrets.token_hex(6)


def crear_escenario(conexion: sqlite3.Connection) -> dict[str, object]:
    operador = seguridad.Usuario(id_usuario=1, nombres="Roki", apellidos="Ochoa Medrano",
        correo="operador@unsch.edu.pe", tipo_usuario=seguridad.TipoUsuario.INTERNO,
        roles=[seguridad.Rol(codigo="GESTOR", nombre="Gestor documental", permisos={seguridad.Permiso.VISUALIZAR, seguridad.Permiso.MODIFICAR})])
    jefe = seguridad.Usuario(id_usuario=2, nombres="Jefa", apellidos="De dependencia",
        correo="jefatura@unsch.edu.pe", tipo_usuario=seguridad.TipoUsuario.INTERNO,
        roles=[seguridad.Rol(codigo="JEFE", nombre="Jefatura", permisos=set(seguridad.Permiso))])
    solicitante = seguridad.Usuario(id_usuario=3, nombres="Ana", apellidos="Quispe",
        correo="ana@example.org", tipo_usuario=seguridad.TipoUsuario.EXTERNO)
    origen = flujo.Dependencia(codigo="MP", nombre="Mesa de partes", jefe=jefe)
    destino = flujo.Dependencia(codigo="EPIS", nombre="Escuela de Ingeniería de Sistemas", jefe=jefe)
    tramite = registro.Tramite(numero_expediente=registro.NumeroExpediente.generar(conexion), remitente=solicitante,
        destinatario=origen, asunto="Solicitud de constancia de estudios",
        categoria=registro.Categoria(codigo="ACA", nombre="Académico"),
        tipo_documento=registro.TipoDocumento(codigo="SOL", nombre="Solicitud"),
        prioridad=registro.Prioridad(codigo="NOR", nombre="Normal"),
        ambito=flujo.AmbitoTramite.EXTERNO, es_academico=True)
    documento = registro.Documento(modo_registro=registro.ModoRegistro.MANUAL, cantidad_folios=3, tramite=tramite)
    tramite.agregar_documento(documento, operador)
    return dict(operador=operador, jefe=jefe, solicitante=solicitante, origen=origen,
                destino=destino, tramite=tramite, documento=documento)


def demostracion() -> None:
    """Recorre los siete grupos y muestra cómo colaboran sus objetos."""
    print("SGD–UNSCH | Demostración de los siete grupos y los pilares de POO")

    # La base demo es temporal. Los módulos admiten también una base en archivo.
    # closing() garantiza que la conexión se cierre al terminar.
    with closing(sqlite3.connect(":memory:")) as conexion:
        Accion = seguridad.AccionAuditoria

        def auditar(usuario: seguridad.Usuario, accion: seguridad.AccionAuditoria,
                    tipo_registro: str, id_registro: object, detalle: str | None = None) -> None:
            # RF-12: la capa de aplicación registra cada operación confirmada.
            seguridad.RegistroAuditoria.registrar(conexion, usuario, accion,
                tipo_registro, str(id_registro), detalle)

        escenario = crear_escenario(conexion)
        tramite = escenario["tramite"]
        documento = escenario["documento"]
        operador = escenario["operador"]
        jefe = escenario["jefe"]
        expediente = documento.numero_expediente
        auditar(operador, Accion.CREACION, "Tramite", expediente, "Registro en mesa de partes")
        auditar(operador, Accion.CREACION, "Documento", expediente, "3 folios")

        # 01. ENCAPSULAMIENTO: consultamos propiedades; no escribimos __atributos.
        print(f"01. Expediente: {expediente}")
        print(f"    Folios calculados: {tramite.cantidad_folios}")
        cargo = tramite.generar_cargo("Persona natural", "Correo electrónico")
        print(cargo.texto())

        # 02. Roles y permisos: cada operación comprueba el permiso del actor.
        print("02. Permisos del operador:",
              sorted(p.value for r in operador.roles for p in r.permisos))

        # 03. El trámite devuelve registros de sus cambios y derivaciones.
        cambio = tramite.recepcionar(operador, id_cambio=1)
        auditar(operador, Accion.MODIFICACION, "Tramite", expediente, "REGISTRADO → EN_ATENCION")
        proveido = flujo.Proveido(
            id_proveido=1, indicacion="Atender solicitud", autor=operador
        )
        derivacion = flujo.derivar_masivamente(
            (documento,), escenario["origen"], escenario["destino"],
            proveido, operador, primer_id=1,
        )[0]
        auditar(operador, Accion.CREACION, "Derivacion", 1, "Mesa de partes → EPIS")
        derivacion.aceptar(operador, escenario["destino"])
        auditar(operador, Accion.MODIFICACION, "Derivacion", 1, "Aceptada")
        solicitud, _ = tramite.solicitar_visto_bueno(
            escenario["destino"], operador, id_solicitud=1, id_cambio=2
        )
        auditar(operador, Accion.CREACION, "SolicitudVistoBueno", 1)
        repositorio = _RepositorioDemo((documento,))
        gestor = avisos.GestorNotificaciones(
            servicio_correo=_CorreoDemo(), repositorio=repositorio
        )
        # RF-17: el jefe recibe el aviso de la solicitud pendiente.
        avisos.notificar_solicitud(solicitud, gestor, "tramites@unsch.edu.pe", primer_id=10)
        solicitud.resolver(jefe, True, "Conforme, continuar la atención", id_cambio=3)
        auditar(jefe, Accion.MODIFICACION, "SolicitudVistoBueno", 1, "Aprobada")
        print(f"03. Derivación: {derivacion.estado.value}")
        print(f"    Visto bueno: {solicitud.estado.value}")

        # 04. ABSTRACCIÓN: el gestor depende del contrato ServicioCorreo.
        # _CorreoDemo lo implementa; puede sustituirse por otro proveedor.
        avisos.notificar_cambio(cambio, gestor, "tramites@unsch.edu.pe", primer_id=1)

        # HERENCIA: Memorando reutiliza los atributos de Documento mediante super().
        memorando = avisos.Memorando(
            modo_registro=registro.ModoRegistro.MANUAL,
            cantidad_folios=1,
            tramite=tramite,
            correos_destinatarios={"jefatura@unsch.edu.pe"},
            autor=operador,
        )
        tramite.agregar_documento(memorando, operador)
        memorando.emitir(operador, "unsch.edu.pe")
        auditar(operador, Accion.CREACION, "Memorando", expediente, "Emitido")
        memorando.enviar_multiple(
            gestor, "tramites@unsch.edu.pe", "Atención académica",
            "Revisar el expediente.", primer_id=20,
        )
        repositorio.documentos.append(memorando)
        print(f"04. Notificaciones demo: {len(repositorio.notificaciones)}")
        print(f"    Memorando hereda el expediente: {memorando.numero_expediente}")

        # 05. Buscar un documento archivado no cambia automáticamente su estado.
        archivador = archivos.Archivador(
            id_archivador=1, nombre="Académicos", dependencia=escenario["destino"]
        )
        documento.archivar(archivador, operador, id_registro=1)
        auditar(operador, Accion.MODIFICACION, "Documento", expediente, "Archivado")
        motor = archivos.MotorBusqueda(repositorio=repositorio)
        encontrados = motor.buscar(
            archivos.CriterioBusqueda(asunto="constancia"), operador
        )
        auditar(operador, Accion.ACCESO, "Documento", expediente,
                f"Búsqueda por asunto: {len(encontrados)} resultados")
        documento.desarchivar(
            operador, "Revisión solicitada por el interesado", id_registro=1
        )
        auditar(operador, Accion.MODIFICACION, "Documento", expediente, "Desarchivado")
        print(f"05. Documentos localizados: {len(encontrados)}")
        print(f"    Estado del documento: {documento.estado.value}")

        # 06. POLIMORFISMO: mismo método generar(), diferentes cálculos.
        # ABSTRACCIÓN: ambos objetos cumplen el contrato de Reporte.
        lista_reportes = [
            informes.ReporteEstadoTramites(
                titulo="Estado de trámites",
                filtros=informes.FiltroReporte(),
                repositorio=repositorio,
            ),
            informes.ReporteCargaTrabajo(
                titulo="Carga por dependencia",
                filtros=informes.FiltroReporte(),
                repositorio=repositorio,
                agrupar_por=informes.AgrupacionCarga.DEPENDENCIA,
                unidad_carga=informes.UnidadCarga.TRAMITES,
            ),
        ]
        for reporte in lista_reportes:
            resultado = reporte.generar(operador)
            auditar(operador, Accion.ACCESO, "Reporte", reporte.titulo)
            filas = [dict(fila) for fila in resultado.consultar()["filas"]]
            print(f"06. {reporte.titulo}: {filas}")

        # 07. Se utiliza un transporte explícito de PRUEBA; no es el servicio real.
        adaptador = servicios.AdaptadorValidacionFirma(
            direccion_servicio="https://servicio-universidad.invalid/validar"
        )
        adjunto = registro.ArchivoElectronico(
            nombre="solicitud.pdf", formato="pdf", ruta_almacenamiento="solicitud.pdf"
        )
        validacion = adaptador.validar(
            adjunto, b"contenido de demostracion", id_validacion=1,
            transporte=lambda *args: {
                "consulta_completada": True, "firmas": [], "referencia": "demo"
            },
        )
        print("07. Archivo sin firmas, ¿firma válida?:", validacion.es_valida())

        # 02. El log de auditoría quedó persistido en la base de datos.
        resumen = conexion.execute(
            "SELECT accion, count(*) FROM auditoria GROUP BY accion ORDER BY accion"
        ).fetchall()
        print("02. Auditoría guardada en SQLite:", dict(resumen))

    print("Fin. No se enviaron correos ni se contactó con servicios externos.")


if __name__ == "__main__":
    demostracion()
