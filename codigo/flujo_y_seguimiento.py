"""03 · Flujo y seguimiento · SGD–UNSCH.

Requerimientos: RF 07, 09, 16, 17, 24, 25, 27.
Conserva las clases y atributos del análisis y de su diagrama.
El programa general es main.py; este módulo se importa desde allí.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from usuarios_y_seguridad import Permiso, TipoUsuario, Usuario, ahora, _requerir, _texto, _validar, _vista

if TYPE_CHECKING:
    from registro_documental import Documento, Tramite


class EstadoTramite(str, Enum):
    REGISTRADO = 'REGISTRADO'
    EN_ATENCION = 'EN_ATENCION'
    OBSERVADO = 'OBSERVADO'
    PENDIENTE_VISTO_BUENO = 'PENDIENTE_VISTO_BUENO'
    FINALIZADO = 'FINALIZADO'


class EstadoDerivacion(str, Enum):
    PENDIENTE = 'PENDIENTE'
    ACEPTADA = 'ACEPTADA'
    CORREGIDA = 'CORREGIDA'


class EstadoVistoBueno(str, Enum):
    PENDIENTE = 'PENDIENTE'
    APROBADO = 'APROBADO'
    OBSERVADO = 'OBSERVADO'


class AmbitoTramite(str, Enum):
    INTERNO = 'INTERNO'
    EXTERNO = 'EXTERNO'


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class CambioEstadoTramite:
    """Registro histórico de una transición de estado del trámite (RF 07)."""
    __slots__ = ('__id_cambio', '__tramite', '__estado_anterior', '__estado_nuevo', '__fecha_hora', '__actor', '__motivo')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_cambio: int
    __tramite: Tramite
    __estado_anterior: EstadoTramite
    __estado_nuevo: EstadoTramite
    __fecha_hora: datetime
    __actor: Usuario
    __motivo: str | None

    def __init__(self, *,
                 id_cambio: int,
                 tramite: Tramite,
                 estado_anterior: EstadoTramite,
                 estado_nuevo: EstadoTramite,
                 fecha_hora: datetime | None = None,
                 actor: Usuario,
                 motivo: str | None = None,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from registro_documental import Tramite

        _validar(id_cambio, int, "id_cambio")
        self.__id_cambio = id_cambio
        _validar(tramite, Tramite, "tramite")
        self.__tramite = tramite
        _validar(estado_anterior, EstadoTramite, "estado_anterior")
        self.__estado_anterior = estado_anterior
        _validar(estado_nuevo, EstadoTramite, "estado_nuevo")
        self.__estado_nuevo = estado_nuevo
        if fecha_hora is None:
            fecha_hora = ahora()
        _validar(fecha_hora, datetime, "fecha_hora")
        self.__fecha_hora = fecha_hora
        _validar(actor, Usuario, "actor")
        self.__actor = actor
        _validar(motivo, str | None, "motivo")
        self.__motivo = motivo

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_cambio': self.__id_cambio,
            'tramite': self.__tramite,
            'estado_anterior': self.__estado_anterior,
            'estado_nuevo': self.__estado_nuevo,
            'fecha_hora': self.__fecha_hora,
            'actor': self.__actor,
            'motivo': self.__motivo,
        }
        return _vista(datos)


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class Derivacion:
    """Envío de documentos de un trámite entre dos dependencias (RF 09, 24, 27)."""
    __slots__ = ('__id_derivacion', '__tramite', '__fecha_hora', '__area_remitente', '__area_destino', '__estado', '__fecha_hora_aceptacion', '__documentos', '__proveido')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_derivacion: int
    __tramite: Tramite
    __fecha_hora: datetime
    __area_remitente: Dependencia
    __area_destino: Dependencia
    __estado: EstadoDerivacion
    __fecha_hora_aceptacion: datetime | None
    __documentos: list[Documento]
    __proveido: Proveido

    def __init__(self, *,
                 id_derivacion: int,
                 tramite: Tramite,
                 fecha_hora: datetime | None = None,
                 area_remitente: Dependencia,
                 area_destino: Dependencia,
                 estado: EstadoDerivacion = EstadoDerivacion.PENDIENTE,
                 fecha_hora_aceptacion: datetime | None = None,
                 documentos: list[Documento],
                 proveido: Proveido,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from registro_documental import Documento, Tramite
        from busqueda_y_archivo import EstadoDocumento

        _validar(id_derivacion, int, "id_derivacion")
        self.__id_derivacion = id_derivacion
        _validar(tramite, Tramite, "tramite")
        self.__tramite = tramite
        if fecha_hora is None:
            fecha_hora = ahora()
        _validar(fecha_hora, datetime, "fecha_hora")
        self.__fecha_hora = fecha_hora
        _validar(area_remitente, Dependencia, "area_remitente")
        self.__area_remitente = area_remitente
        _validar(area_destino, Dependencia, "area_destino")
        self.__area_destino = area_destino
        _validar(estado, EstadoDerivacion, "estado")
        self.__estado = estado
        _validar(fecha_hora_aceptacion, datetime | None, "fecha_hora_aceptacion")
        self.__fecha_hora_aceptacion = fecha_hora_aceptacion
        _validar(documentos, list[Documento], "documentos")
        self.__documentos = list(documentos)
        _validar(proveido, Proveido, "proveido")
        self.__proveido = proveido
        if tramite.estado in {EstadoTramite.FINALIZADO, EstadoTramite.PENDIENTE_VISTO_BUENO}:
            raise ValueError("El trámite no permite nuevas derivaciones en su estado actual.")
        if area_remitente is area_destino:
            raise ValueError("Use asignación interna; origen y destino deben ser distintos.")
        if not documentos or len({id(d) for d in documentos}) != len(documentos):
            raise ValueError("Seleccione documentos distintos y no vacíos.")
        if any(d.consultar()["tramite"] is not tramite for d in documentos):
            raise ValueError("Todos los documentos deben pertenecer al trámite.")
        if any(d.estado is not EstadoDocumento.ACTIVO for d in documentos):
            raise ValueError("Solo se pueden derivar documentos activos.")
        if estado is EstadoDerivacion.ACEPTADA and fecha_hora_aceptacion is None:
            raise ValueError("Una derivación aceptada necesita fecha de aceptación.")

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_derivacion': self.__id_derivacion,
            'tramite': self.__tramite,
            'fecha_hora': self.__fecha_hora,
            'area_remitente': self.__area_remitente,
            'area_destino': self.__area_destino,
            'estado': self.__estado,
            'fecha_hora_aceptacion': self.__fecha_hora_aceptacion,
            'documentos': self.__documentos,
            'proveido': self.__proveido,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def estado(self) -> EstadoDerivacion:
        return self.__estado

    def aceptar(self, actor: Usuario, dependencia: Dependencia) -> None:
        _requerir(actor, Permiso.MODIFICAR)
        if dependencia is not self.__area_destino:
            raise PermissionError("La dependencia debe ser la destinataria.")
        if self.__estado is not EstadoDerivacion.PENDIENTE:
            raise ValueError("Solo se acepta una derivación pendiente.")
        if self.__tramite.estado in {EstadoTramite.FINALIZADO, EstadoTramite.PENDIENTE_VISTO_BUENO}:
            raise ValueError("El trámite no permite aceptar una derivación en su estado actual.")
        self.__estado, self.__fecha_hora_aceptacion = EstadoDerivacion.ACEPTADA, ahora()
        self.__tramite.actualizar_destinatario(self, actor)

    def corregir(self, destino: Dependencia, autor: Usuario, motivo: str,
                 id_nueva_derivacion: int, id_correccion: int) -> CorreccionDerivacion:
        _requerir(autor, Permiso.MODIFICAR)
        if self.__estado is not EstadoDerivacion.PENDIENTE:
            raise ValueError("No se corrige una derivación aceptada o ya corregida.")
        motivo = _texto(motivo, "motivo de corrección")
        if destino is self.__area_destino:
            raise ValueError("Seleccione un destino distinto al anterior.")
        if id_nueva_derivacion == self.__id_derivacion:
            raise ValueError("La derivación sustituta necesita otro identificador.")
        _verificar_origen(self.__tramite, self.__area_remitente)
        nueva =Derivacion(id_derivacion=id_nueva_derivacion, tramite=self.__tramite,
            area_remitente=self.__area_remitente, area_destino=destino,
            documentos=list(self.__documentos), proveido=self.__proveido)
        correccion = CorreccionDerivacion(id_correccion=id_correccion,
            derivacion_original=self, derivacion_sustituta=nueva, motivo=motivo, autor=autor)
        self.__estado = EstadoDerivacion.CORREGIDA
        return correccion


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class Dependencia:
    """Área u oficina de la universidad y su jefe designado."""
    __slots__ = ('__codigo', '__nombre', '__jefe')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __codigo: str
    __nombre: str
    __jefe: Usuario | None

    def __init__(self, *,
                 codigo: str,
                 nombre: str,
                 jefe: Usuario | None = None,
                 ) -> None:
        _validar(codigo, str, "codigo")
        self.__codigo = codigo
        _validar(nombre, str, "nombre")
        self.__nombre = nombre
        _validar(jefe, Usuario | None, "jefe")
        if jefe is not None and jefe.consultar()["tipo_usuario"] is not TipoUsuario.INTERNO:
            raise ValueError("El jefe debe ser un usuario interno.")
        self.__jefe = jefe

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'codigo': self.__codigo,
            'nombre': self.__nombre,
            'jefe': self.__jefe,
        }
        return _vista(datos)

    def designar_jefe(self, jefe: Usuario, actor: Usuario) -> None:
        # La designación modifica quién puede resolver los vistos buenos: requiere autorización.
        _requerir(actor, Permiso.APROBAR)
        _validar(jefe, Usuario, "jefe")
        if jefe.consultar()["tipo_usuario"] is not TipoUsuario.INTERNO:
            raise ValueError("El jefe debe ser un usuario interno.")
        self.__jefe = jefe


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class SolicitudVistoBueno:
    """Solicitud dirigida al jefe de una dependencia y su resolución (RF 16, 17)."""
    __slots__ = ('__id_solicitud', '__tramite', '__dependencia', '__solicitante', '__jefe_destinatario', '__fecha_solicitud', '__estado', '__resuelto_por', '__fecha_respuesta', '__motivo_respuesta')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_solicitud: int
    __tramite: Tramite
    __dependencia: Dependencia
    __solicitante: Usuario
    __jefe_destinatario: Usuario
    __fecha_solicitud: datetime
    __estado: EstadoVistoBueno
    __resuelto_por: Usuario | None
    __fecha_respuesta: datetime | None
    __motivo_respuesta: str | None

    def __init__(self, *,
                 id_solicitud: int,
                 tramite: Tramite,
                 dependencia: Dependencia,
                 solicitante: Usuario,
                 jefe_destinatario: Usuario,
                 fecha_solicitud: datetime | None = None,
                 estado: EstadoVistoBueno = EstadoVistoBueno.PENDIENTE,
                 resuelto_por: Usuario | None = None,
                 fecha_respuesta: datetime | None = None,
                 motivo_respuesta: str | None = None,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from registro_documental import Tramite

        _validar(id_solicitud, int, "id_solicitud")
        self.__id_solicitud = id_solicitud
        _validar(tramite, Tramite, "tramite")
        self.__tramite = tramite
        _validar(dependencia, Dependencia, "dependencia")
        self.__dependencia = dependencia
        _validar(solicitante, Usuario, "solicitante")
        self.__solicitante = solicitante
        _validar(jefe_destinatario, Usuario, "jefe_destinatario")
        self.__jefe_destinatario = jefe_destinatario
        if fecha_solicitud is None:
            fecha_solicitud = ahora()
        _validar(fecha_solicitud, datetime, "fecha_solicitud")
        self.__fecha_solicitud = fecha_solicitud
        _validar(estado, EstadoVistoBueno, "estado")
        self.__estado = estado
        _validar(resuelto_por, Usuario | None, "resuelto_por")
        self.__resuelto_por = resuelto_por
        _validar(fecha_respuesta, datetime | None, "fecha_respuesta")
        self.__fecha_respuesta = fecha_respuesta
        _validar(motivo_respuesta, str | None, "motivo_respuesta")
        self.__motivo_respuesta = motivo_respuesta
        if dependencia.consultar()["jefe"] is not jefe_destinatario:
            raise ValueError("El destinatario debe ser el jefe de la dependencia.")

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_solicitud': self.__id_solicitud,
            'tramite': self.__tramite,
            'dependencia': self.__dependencia,
            'solicitante': self.__solicitante,
            'jefe_destinatario': self.__jefe_destinatario,
            'fecha_solicitud': self.__fecha_solicitud,
            'estado': self.__estado,
            'resuelto_por': self.__resuelto_por,
            'fecha_respuesta': self.__fecha_respuesta,
            'motivo_respuesta': self.__motivo_respuesta,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def estado(self) -> EstadoVistoBueno:
        return self.__estado

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def fecha_respuesta(self) -> datetime | None:
        return self.__fecha_respuesta

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def motivo_respuesta(self) -> str | None:
        return self.__motivo_respuesta

    def _resolver(self, actor: Usuario, aprobado: bool, motivo: str) -> None:
        _requerir(actor, Permiso.APROBAR)
        # Resuelve el jefe designado al momento de resolver. Si cambió la jefatura,
        # __jefe_destinatario conserva a quién se dirigió y __resuelto_por, quién resolvió.
        if self.__dependencia.consultar()["jefe"] is not actor:
            raise PermissionError("Solo el jefe vigente de la dependencia puede resolver el visto bueno.")
        if self.__estado is not EstadoVistoBueno.PENDIENTE:
            raise ValueError("La solicitud ya fue resuelta.")
        motivo = _texto(motivo, "motivo de respuesta")
        self.__estado = EstadoVistoBueno.APROBADO if aprobado else EstadoVistoBueno.OBSERVADO
        self.__resuelto_por, self.__fecha_respuesta, self.__motivo_respuesta = actor, ahora(), motivo


    def resolver(self, actor: Usuario, aprobado: bool, motivo: str, id_cambio: int) -> CambioEstadoTramite:
        return self.__tramite.resolver_visto_bueno(self, actor, aprobado, id_cambio, motivo)


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class AsignacionDocumento:
    """Asignación de un documento a un responsable de una dependencia (RF 25)."""
    __slots__ = ('__id_asignacion', '__documento', '__dependencia', '__responsable', '__asignado_por', '__fecha_asignacion', '__fecha_fin')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_asignacion: int
    __documento: Documento
    __dependencia: Dependencia
    __responsable: Usuario
    __asignado_por: Usuario
    __fecha_asignacion: datetime
    __fecha_fin: datetime | None

    def __init__(self, *,
                 id_asignacion: int,
                 documento: Documento,
                 dependencia: Dependencia,
                 responsable: Usuario,
                 asignado_por: Usuario,
                 fecha_asignacion: datetime | None = None,
                 fecha_fin: datetime | None = None,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from registro_documental import Documento

        _validar(id_asignacion, int, "id_asignacion")
        self.__id_asignacion = id_asignacion
        _validar(documento, Documento, "documento")
        self.__documento = documento
        _validar(dependencia, Dependencia, "dependencia")
        self.__dependencia = dependencia
        _validar(responsable, Usuario, "responsable")
        self.__responsable = responsable
        _validar(asignado_por, Usuario, "asignado_por")
        self.__asignado_por = asignado_por
        if fecha_asignacion is None:
            fecha_asignacion = ahora()
        _validar(fecha_asignacion, datetime, "fecha_asignacion")
        self.__fecha_asignacion = fecha_asignacion
        _validar(fecha_fin, datetime | None, "fecha_fin")
        self.__fecha_fin = fecha_fin

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_asignacion': self.__id_asignacion,
            'documento': self.__documento,
            'dependencia': self.__dependencia,
            'responsable': self.__responsable,
            'asignado_por': self.__asignado_por,
            'fecha_asignacion': self.__fecha_asignacion,
            'fecha_fin': self.__fecha_fin,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def vigente(self) -> bool:
        return self.__fecha_fin is None

    def finalizar(self, actor: Usuario) -> None:
        _requerir(actor, Permiso.MODIFICAR)
        if self.__fecha_fin is not None:
            raise ValueError("La asignación ya finalizó.")
        self.__fecha_fin = ahora()


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class Proveido:
    """Indicación que acompaña a una derivación."""
    __slots__ = ('__id_proveido', '__indicacion', '__autor', '__fecha_hora')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_proveido: int
    __indicacion: str
    __autor: Usuario
    __fecha_hora: datetime

    def __init__(self, *,
                 id_proveido: int,
                 indicacion: str,
                 autor: Usuario,
                 fecha_hora: datetime | None = None,
                 ) -> None:
        _validar(id_proveido, int, "id_proveido")
        self.__id_proveido = id_proveido
        _validar(indicacion, str, "indicacion")
        self.__indicacion = indicacion
        _validar(autor, Usuario, "autor")
        self.__autor = autor
        if fecha_hora is None:
            fecha_hora = ahora()
        _validar(fecha_hora, datetime, "fecha_hora")
        self.__fecha_hora = fecha_hora

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_proveido': self.__id_proveido,
            'indicacion': self.__indicacion,
            'autor': self.__autor,
            'fecha_hora': self.__fecha_hora,
        }
        return _vista(datos)


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class ConfiguracionDerivacion:
    """Regla que define el área inicial de los trámites externos o académicos."""
    __slots__ = ('__id_configuracion', '__nombre', '__area_inicio', '__aplica_a_externos', '__aplica_a_academicos', '__activa')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_configuracion: int
    __nombre: str
    __area_inicio: Dependencia
    __aplica_a_externos: bool
    __aplica_a_academicos: bool
    __activa: bool

    def __init__(self, *,
                 id_configuracion: int,
                 nombre: str,
                 area_inicio: Dependencia,
                 aplica_a_externos: bool,
                 aplica_a_academicos: bool,
                 activa: bool = True,
                 ) -> None:
        _validar(id_configuracion, int, "id_configuracion")
        self.__id_configuracion = id_configuracion
        _validar(nombre, str, "nombre")
        self.__nombre = nombre
        _validar(area_inicio, Dependencia, "area_inicio")
        self.__area_inicio = area_inicio
        _validar(aplica_a_externos, bool, "aplica_a_externos")
        self.__aplica_a_externos = aplica_a_externos
        _validar(aplica_a_academicos, bool, "aplica_a_academicos")
        self.__aplica_a_academicos = aplica_a_academicos
        _validar(activa, bool, "activa")
        self.__activa = activa

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_configuracion': self.__id_configuracion,
            'nombre': self.__nombre,
            'area_inicio': self.__area_inicio,
            'aplica_a_externos': self.__aplica_a_externos,
            'aplica_a_academicos': self.__aplica_a_academicos,
            'activa': self.__activa,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def area_inicio(self) -> Dependencia:
        return self.__area_inicio

    def aplica(self, tramite: Tramite) -> bool:
        datos = tramite.consultar()
        return self.__activa and ((self.__aplica_a_externos and datos["ambito"] is AmbitoTramite.EXTERNO)
                                 or (self.__aplica_a_academicos and datos["es_academico"]))

    def derivar(self, tramite: Tramite, origen: Dependencia, proveido: Proveido,
                id_derivacion: int, actor: Usuario) -> Derivacion:
        _requerir(actor, Permiso.MODIFICAR)
        if not self.aplica(tramite):
            raise ValueError("La configuración no aplica a este trámite.")
        _verificar_origen(tramite, origen)
        return Derivacion(id_derivacion=id_derivacion, tramite=tramite,
            area_remitente=origen, area_destino=self.__area_inicio,
            documentos=list(tramite.consultar()["documentos"]), proveido=proveido)


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class CorreccionDerivacion:
    """Sustitución de una derivación pendiente enviada a un destino equivocado (RF 27)."""
    __slots__ = ('__id_correccion', '__derivacion_original', '__derivacion_sustituta', '__motivo', '__autor', '__fecha_hora')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_correccion: int
    __derivacion_original: Derivacion
    __derivacion_sustituta: Derivacion
    __motivo: str
    __autor: Usuario
    __fecha_hora: datetime

    def __init__(self, *,
                 id_correccion: int,
                 derivacion_original: Derivacion,
                 derivacion_sustituta: Derivacion,
                 motivo: str,
                 autor: Usuario,
                 fecha_hora: datetime | None = None,
                 ) -> None:
        _validar(id_correccion, int, "id_correccion")
        self.__id_correccion = id_correccion
        _validar(derivacion_original, Derivacion, "derivacion_original")
        self.__derivacion_original = derivacion_original
        _validar(derivacion_sustituta, Derivacion, "derivacion_sustituta")
        self.__derivacion_sustituta = derivacion_sustituta
        _validar(motivo, str, "motivo")
        self.__motivo = motivo
        _validar(autor, Usuario, "autor")
        self.__autor = autor
        if fecha_hora is None:
            fecha_hora = ahora()
        _validar(fecha_hora, datetime, "fecha_hora")
        self.__fecha_hora = fecha_hora

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_correccion': self.__id_correccion,
            'derivacion_original': self.__derivacion_original,
            'derivacion_sustituta': self.__derivacion_sustituta,
            'motivo': self.__motivo,
            'autor': self.__autor,
            'fecha_hora': self.__fecha_hora,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def motivo(self) -> str:
        return self.__motivo

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def fecha_hora(self) -> datetime:
        return self.__fecha_hora


def _verificar_origen(tramite: Tramite, origen: Dependencia) -> None:
    """Solo deriva la dependencia que tiene el trámite en ese momento.

    El constructor de Derivacion no lo comprueba porque también reconstruye
    derivaciones históricas, cuyo remitente ya no tiene el trámite.
    """
    if tramite.consultar()["destinatario"] is not origen:
        raise PermissionError("Solo la dependencia que tiene el trámite puede derivarlo.")


def asignar_masivamente(documentos: tuple[Documento, ...], dependencia: Dependencia,
                        responsable: Usuario, actor: Usuario, primer_id: int,
                        vigentes: tuple[AsignacionDocumento, ...] = ()) -> tuple[AsignacionDocumento, ...]:
    # Importación diferida: evita la dependencia circular entre módulos.
    from busqueda_y_archivo import EstadoDocumento

    _requerir(actor, Permiso.MODIFICAR)
    if responsable.consultar()["tipo_usuario"] is not TipoUsuario.INTERNO:
        raise ValueError("El responsable debe ser un usuario interno.")
    if not documentos or len({id(d) for d in documentos}) != len(documentos):
        raise ValueError("Seleccione documentos distintos.")
    ocupados = {id(a.consultar()["documento"]) for a in vigentes if a.vigente}
    if any(id(d) in ocupados or d.estado is not EstadoDocumento.ACTIVO for d in documentos):
        raise ValueError("Hay documentos no activos o con asignación vigente.")
    return tuple(AsignacionDocumento(id_asignacion=primer_id+i, documento=d,
        dependencia=dependencia, responsable=responsable, asignado_por=actor)
        for i, d in enumerate(documentos))


def derivar_masivamente(documentos: tuple[Documento, ...], origen: Dependencia,
                         destino: Dependencia, proveido: Proveido, actor: Usuario,
                         primer_id: int) -> tuple[Derivacion, ...]:
    _requerir(actor, Permiso.MODIFICAR)
    if not documentos or len({id(d) for d in documentos}) != len(documentos):
        raise ValueError("Seleccione documentos distintos.")
    grupos: dict[Tramite, list[Documento]] = {}
    for documento in documentos:
        grupos.setdefault(documento.consultar()["tramite"], []).append(documento)
    for tramite in grupos:
        _verificar_origen(tramite, origen)
    # Una derivación por trámite, conservando el expediente de cada documento.
    return tuple(Derivacion(id_derivacion=primer_id+i, tramite=tramite,
        area_remitente=origen, area_destino=destino, documentos=docs, proveido=proveido)
        for i, (tramite, docs) in enumerate(grupos.items()))
