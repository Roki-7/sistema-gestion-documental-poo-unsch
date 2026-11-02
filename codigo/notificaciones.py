"""04 · Notificaciones · SGD–UNSCH.

Requerimientos: RF 04, 08, 26.
Conserva las clases y atributos del análisis y de su diagrama.
El programa general es main.py; este módulo se importa desde allí.
"""
from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from collections.abc import Mapping
from datetime import date
from datetime import datetime
from enum import Enum
from typing import Protocol
from typing import runtime_checkable
from typing import TYPE_CHECKING
from usuarios_y_seguridad import Permiso, Usuario, ahora, _correo, _requerir, _texto, _validar, _vista
from registro_documental import Documento
from busqueda_y_archivo import EstadoDocumento

if TYPE_CHECKING:
    from registro_documental import ArchivoElectronico, ModoRegistro, Tramite
    from flujo_y_seguimiento import CambioEstadoTramite, SolicitudVistoBueno
    from busqueda_y_archivo import Archivador, PoliticaConservacion


@runtime_checkable
class RepositorioNotificaciones(Protocol):
    def guardar(self, notificacion: Notificacion) -> None: ...
    def guardar_intento(self, intento: IntentoEnvio) -> None: ...
    def existe_evento(self, evento: str, correo: str) -> bool: ...


class EstadoEnvio(str, Enum):
    PENDIENTE = 'PENDIENTE'
    ENVIADO = 'ENVIADO'
    FALLIDO = 'FALLIDO'


class TipoEventoNotificacion(str, Enum):
    RECEPCION_TRAMITE = 'RECEPCION_TRAMITE'
    RECEPCION_DOCUMENTO = 'RECEPCION_DOCUMENTO'
    TRAMITE_OBSERVADO = 'TRAMITE_OBSERVADO'
    TRAMITE_FINALIZADO = 'TRAMITE_FINALIZADO'
    SOLICITUD_VISTO_BUENO = 'SOLICITUD_VISTO_BUENO'
    MEMORANDO_EMITIDO = 'MEMORANDO_EMITIDO'


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class Notificacion:
    """Mensaje de correo generado por un evento del trámite (RF 04, 08)."""
    __slots__ = ('__id_notificacion', '__tramite', '__correo_destinatario', '__asunto', '__mensaje', '__fecha_creacion', '__estado', '__fecha_envio', '__tipo_evento', '__id_evento_origen', '__correo_remitente', '__documento')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_notificacion: int
    __tramite: Tramite | None
    __correo_destinatario: str
    __asunto: str
    __mensaje: str
    __fecha_creacion: datetime
    __estado: EstadoEnvio
    __fecha_envio: datetime | None
    __tipo_evento: TipoEventoNotificacion
    __id_evento_origen: str
    __correo_remitente: str
    __documento: Documento | None

    def __init__(self, *,
                 id_notificacion: int,
                 tramite: Tramite | None = None,
                 correo_destinatario: str,
                 asunto: str,
                 mensaje: str,
                 fecha_creacion: datetime | None = None,
                 estado: EstadoEnvio = EstadoEnvio.PENDIENTE,
                 fecha_envio: datetime | None = None,
                 tipo_evento: TipoEventoNotificacion,
                 id_evento_origen: str,
                 correo_remitente: str,
                 documento: Documento | None = None,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from registro_documental import Tramite

        _validar(id_notificacion, int, "id_notificacion")
        self.__id_notificacion = id_notificacion
        _validar(tramite, Tramite | None, "tramite")
        self.__tramite = tramite
        _validar(correo_destinatario, str, "correo_destinatario")
        self.__correo_destinatario = correo_destinatario
        _validar(asunto, str, "asunto")
        self.__asunto = asunto
        _validar(mensaje, str, "mensaje")
        self.__mensaje = mensaje
        if fecha_creacion is None:
            fecha_creacion = ahora()
        _validar(fecha_creacion, datetime, "fecha_creacion")
        self.__fecha_creacion = fecha_creacion
        _validar(estado, EstadoEnvio, "estado")
        self.__estado = estado
        _validar(fecha_envio, datetime | None, "fecha_envio")
        self.__fecha_envio = fecha_envio
        _validar(tipo_evento, TipoEventoNotificacion, "tipo_evento")
        self.__tipo_evento = tipo_evento
        _validar(id_evento_origen, str, "id_evento_origen")
        self.__id_evento_origen = id_evento_origen
        _validar(correo_remitente, str, "correo_remitente")
        self.__correo_remitente = correo_remitente
        _validar(documento, Documento | None, "documento")
        self.__documento = documento
        self.__correo_destinatario = _correo(correo_destinatario)
        self.__correo_remitente = _correo(correo_remitente)
        if estado is EstadoEnvio.ENVIADO and fecha_envio is None:
            raise ValueError("Una notificación enviada necesita fecha de envío.")

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_notificacion': self.__id_notificacion,
            'tramite': self.__tramite,
            'correo_destinatario': self.__correo_destinatario,
            'asunto': self.__asunto,
            'mensaje': self.__mensaje,
            'fecha_creacion': self.__fecha_creacion,
            'estado': self.__estado,
            'fecha_envio': self.__fecha_envio,
            'tipo_evento': self.__tipo_evento,
            'id_evento_origen': self.__id_evento_origen,
            'correo_remitente': self.__correo_remitente,
            'documento': self.__documento,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def estado(self) -> EstadoEnvio:
        return self.__estado

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def fecha_envio(self) -> datetime | None:
        return self.__fecha_envio

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def tipo_evento(self) -> TipoEventoNotificacion:
        return self.__tipo_evento

    def enviar(self, servicio: ServicioCorreo, id_intento: int) -> IntentoEnvio:
        _validar(id_intento, int, "id_intento")
        if self.__estado is EstadoEnvio.ENVIADO:
            raise ValueError("La notificación ya fue aceptada por el servicio de correo.")
        instante = ahora()
        try:
            referencia = _texto(servicio.enviar(self.__correo_remitente,
                self.__correo_destinatario, self.__asunto, self.__mensaje), "ID del servicio")
        except Exception as exc:
            intento = IntentoEnvio(id_intento=id_intento, notificacion=self, fecha_hora=instante,
                aceptado_por_servicio=False, detalle_resultado=type(exc).__name__,
                id_mensaje_servicio=None)
            self.__estado = EstadoEnvio.FALLIDO
            return intento
        intento = IntentoEnvio(id_intento=id_intento, notificacion=self, fecha_hora=instante,
            aceptado_por_servicio=True, detalle_resultado="Aceptado por el proveedor de correo",
            id_mensaje_servicio=referencia)
        self.__estado, self.__fecha_envio = EstadoEnvio.ENVIADO, instante
        return intento


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class IntentoEnvio:
    """Resultado de cada intento de entregar una notificación al proveedor de correo."""
    __slots__ = ('__id_intento', '__notificacion', '__fecha_hora', '__aceptado_por_servicio', '__detalle_resultado', '__id_mensaje_servicio')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_intento: int
    __notificacion: Notificacion
    __fecha_hora: datetime
    __aceptado_por_servicio: bool
    __detalle_resultado: str | None
    __id_mensaje_servicio: str | None

    def __init__(self, *,
                 id_intento: int,
                 notificacion: Notificacion,
                 fecha_hora: datetime,
                 aceptado_por_servicio: bool,
                 detalle_resultado: str | None,
                 id_mensaje_servicio: str | None,
                 ) -> None:
        _validar(id_intento, int, "id_intento")
        self.__id_intento = id_intento
        _validar(notificacion, Notificacion, "notificacion")
        self.__notificacion = notificacion
        _validar(fecha_hora, datetime, "fecha_hora")
        self.__fecha_hora = fecha_hora
        _validar(aceptado_por_servicio, bool, "aceptado_por_servicio")
        self.__aceptado_por_servicio = aceptado_por_servicio
        _validar(detalle_resultado, str | None, "detalle_resultado")
        self.__detalle_resultado = detalle_resultado
        _validar(id_mensaje_servicio, str | None, "id_mensaje_servicio")
        self.__id_mensaje_servicio = id_mensaje_servicio

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_intento': self.__id_intento,
            'notificacion': self.__notificacion,
            'fecha_hora': self.__fecha_hora,
            'aceptado_por_servicio': self.__aceptado_por_servicio,
            'detalle_resultado': self.__detalle_resultado,
            'id_mensaje_servicio': self.__id_mensaje_servicio,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def aceptado_por_servicio(self) -> bool:
        return self.__aceptado_por_servicio


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class GestorNotificaciones:
    """Coordina el registro y envío de notificaciones sin duplicar eventos."""
    __slots__ = ('__servicio_correo', '__repositorio')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __servicio_correo: ServicioCorreo
    __repositorio: RepositorioNotificaciones

    def __init__(self, *,
                 servicio_correo: ServicioCorreo,
                 repositorio: RepositorioNotificaciones,
                 ) -> None:
        _validar(servicio_correo, ServicioCorreo, "servicio_correo")
        self.__servicio_correo = servicio_correo
        _validar(repositorio, RepositorioNotificaciones, "repositorio")
        self.__repositorio = repositorio

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'servicio_correo': self.__servicio_correo,
            'repositorio': self.__repositorio,
        }
        return _vista(datos)

    def registrar(self, notificacion: Notificacion) -> None:
        datos = notificacion.consultar()
        if self.__repositorio.existe_evento(datos["id_evento_origen"], datos["correo_destinatario"]):
            raise ValueError("El evento ya tiene una notificación para ese destinatario.")
        self.__repositorio.guardar(notificacion)

    def enviar(self, notificacion: Notificacion, id_intento: int) -> IntentoEnvio:
        intento = notificacion.enviar(self.__servicio_correo, id_intento)
        self.__repositorio.guardar_intento(intento)
        self.__repositorio.guardar(notificacion)
        return intento

    def notificar(self, *, id_notificacion: int, id_intento: int, id_evento: str,
                  tipo: TipoEventoNotificacion, remitente: str, destinatario: str,
                  asunto: str, mensaje: str, tramite: Tramite | None = None,
                  documento: Documento | None = None) -> Notificacion:
        notificacion = Notificacion(id_notificacion=id_notificacion, tramite=tramite,
            correo_destinatario=destinatario, asunto=asunto, mensaje=mensaje,
            tipo_evento=tipo, id_evento_origen=id_evento, correo_remitente=remitente,
            documento=documento)
        self.registrar(notificacion)
        self.enviar(notificacion, id_intento)
        return notificacion


# HERENCIA: reutilización de los atributos y operaciones de la base.
class Memorando(Documento):
    """Documento interno que se envía a varios destinatarios institucionales (RF 26)."""
    __slots__ = ('__correos_destinatarios', '__autor', '__fecha_emision')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __correos_destinatarios: set[str]
    __autor: Usuario
    __fecha_emision: datetime | None

    def __init__(self, *,
                 modo_registro: ModoRegistro,
                 cantidad_folios: int,
                 tramite: Tramite,
                 archivos: list[ArchivoElectronico] | None = None,
                 estado: EstadoDocumento = EstadoDocumento.ACTIVO,
                 archivador: Archivador | None = None,
                 politica_conservacion: PoliticaConservacion | None = None,
                 fecha_inicio_computo: date | None = None,
                 correos_destinatarios: set[str],
                 autor: Usuario,
                 fecha_emision: datetime | None = None,
                 ) -> None:
        super().__init__(modo_registro=modo_registro, cantidad_folios=cantidad_folios, tramite=tramite, archivos=archivos, estado=estado, archivador=archivador, politica_conservacion=politica_conservacion, fecha_inicio_computo=fecha_inicio_computo)
        _validar(correos_destinatarios, set[str], "correos_destinatarios")
        self.__correos_destinatarios = set(correos_destinatarios)
        _validar(autor, Usuario, "autor")
        self.__autor = autor
        _validar(fecha_emision, datetime | None, "fecha_emision")
        self.__fecha_emision = fecha_emision
        if not correos_destinatarios:
            raise ValueError("Seleccione al menos un destinatario institucional.")
        self.__correos_destinatarios = {_correo(c) for c in correos_destinatarios}

    def consultar(self) -> Mapping[str, object]:
        datos = dict(super().consultar())
        datos.update({
            'correos_destinatarios': self.__correos_destinatarios,
            'autor': self.__autor,
            'fecha_emision': self.__fecha_emision,
        })
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def correos_destinatarios(self) -> frozenset[str]:
        return frozenset(self.__correos_destinatarios)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def fecha_emision(self) -> datetime | None:
        return self.__fecha_emision

    def emitir(self, actor: Usuario, dominio_institucional: str) -> None:
        _requerir(actor, Permiso.MODIFICAR)
        if actor is not self.__autor:
            raise PermissionError("El emisor debe ser el autor del memorando.")
        if self.__fecha_emision is not None:
            raise ValueError("El memorando ya fue emitido.")
        dominio = _texto(dominio_institucional, "dominio institucional").casefold().lstrip("@")
        if any(c.rsplit("@", 1)[1].casefold() != dominio for c in self.__correos_destinatarios):
            raise ValueError("Todos los destinatarios deben tener correo institucional.")
        self.__fecha_emision = ahora()

    def enviar_multiple(self, gestor: GestorNotificaciones, remitente: str, asunto: str,
                        mensaje: str, primer_id: int) -> tuple[Notificacion, ...]:
        if self.__fecha_emision is None:
            raise ValueError("Primero emita el memorando.")
        resultado = []
        evento = f"memorando:{self.numero_expediente}:{self.__fecha_emision.isoformat()}"
        for indice, correo in enumerate(sorted(self.__correos_destinatarios)):
            resultado.append(gestor.notificar(id_notificacion=primer_id+indice,
                id_intento=primer_id+indice, id_evento=evento,
                tipo=TipoEventoNotificacion.MEMORANDO_EMITIDO, remitente=remitente,
                destinatario=correo, asunto=asunto, mensaje=mensaje,
                tramite=self.consultar()["tramite"], documento=self))
        return tuple(resultado)


# ABSTRACCIÓN: contrato de operaciones para sus implementaciones.
class ServicioCorreo(ABC):
    """Contrato que debe cumplir cualquier proveedor de correo."""
    __slots__ = ()

    @abstractmethod
    def enviar(self, remitente: str, destinatario: str, asunto: str, mensaje: str) -> str:
        """Entrega al proveedor y devuelve su ID; no equivale a lectura del destinatario."""
        raise NotImplementedError


def notificar_cambio(cambio: CambioEstadoTramite, gestor: GestorNotificaciones,
                     remitente: str, primer_id: int) -> Notificacion | None:
    # Importación diferida: evita la dependencia circular entre módulos.
    from flujo_y_seguimiento import AmbitoTramite, EstadoTramite

    datos = cambio.consultar()
    tramite = datos["tramite"]
    t = tramite.consultar()
    tipos = {EstadoTramite.OBSERVADO: TipoEventoNotificacion.TRAMITE_OBSERVADO,
             EstadoTramite.FINALIZADO: TipoEventoNotificacion.TRAMITE_FINALIZADO,
             EstadoTramite.EN_ATENCION: TipoEventoNotificacion.RECEPCION_TRAMITE}
    tipo = tipos.get(datos["estado_nuevo"])
    if tipo is TipoEventoNotificacion.RECEPCION_TRAMITE and datos["estado_anterior"] is not EstadoTramite.REGISTRADO:
        return None
    if tipo is None:
        return None
    if tipo in {TipoEventoNotificacion.TRAMITE_OBSERVADO, TipoEventoNotificacion.TRAMITE_FINALIZADO}:
        if not (t["es_academico"] or t["ambito"] is AmbitoTramite.EXTERNO):
            return None
    return gestor.notificar(id_notificacion=primer_id, id_intento=primer_id,
        id_evento=f"cambio:{datos['id_cambio']}", tipo=tipo, remitente=remitente,
        destinatario=t["remitente"].consultar()["correo"],
        asunto=f"Expediente {t['numero_expediente']}: {datos['estado_nuevo'].value}",
        mensaje=datos["motivo"] or "Su trámite fue recibido y está en atención.", tramite=tramite)


def notificar_solicitud(solicitud: SolicitudVistoBueno, gestor: GestorNotificaciones,
                         remitente: str, primer_id: int) -> Notificacion:
    datos = solicitud.consultar()
    return gestor.notificar(id_notificacion=primer_id, id_intento=primer_id,
        id_evento=f"visto-bueno:{datos['id_solicitud']}",
        tipo=TipoEventoNotificacion.SOLICITUD_VISTO_BUENO, remitente=remitente,
        destinatario=datos["jefe_destinatario"].consultar()["correo"],
        asunto="Solicitud de visto bueno", mensaje="Tiene una solicitud pendiente de revisión.",
        tramite=datos["tramite"])
