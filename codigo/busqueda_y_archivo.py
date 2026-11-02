"""05 · Búsqueda y archivo · SGD–UNSCH.

Requerimientos: RF 13, 14, 18, 19.
Conserva las clases y atributos del análisis y de su diagrama.
El programa general es main.py; este módulo se importa desde allí.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import Protocol
from typing import runtime_checkable
import calendar
from typing import TYPE_CHECKING
from usuarios_y_seguridad import Permiso, Usuario, fecha_local, _requerir, _validar, _vista

if TYPE_CHECKING:
    from registro_documental import ArchivoElectronico, Documento
    from flujo_y_seguimiento import Dependencia


@runtime_checkable
class RepositorioDocumentos(Protocol):
    def listar_documentos(self) -> tuple[Documento, ...]: ...


class EstadoDocumento(str, Enum):
    ACTIVO = 'ACTIVO'
    ARCHIVADO = 'ARCHIVADO'
    ELIMINACION_PENDIENTE = 'ELIMINACION_PENDIENTE'
    ELIMINADO = 'ELIMINADO'


class ModalidadConservacion(str, Enum):
    TEMPORAL = 'TEMPORAL'
    PERMANENTE = 'PERMANENTE'


class UnidadPlazo(str, Enum):
    DIAS = 'DIAS'
    MESES = 'MESES'
    ANIOS = 'ANIOS'


class ResultadoEliminacion(str, Enum):
    CONFIRMADA = 'CONFIRMADA'
    FALLIDA = 'FALLIDA'


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class CriterioBusqueda:
    """Filtros combinables para localizar documentos (RF 13)."""
    __slots__ = ('__numero_expediente', '__asunto', '__fecha_desde', '__fecha_hasta', '__remitente', '__estado_documento')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __numero_expediente: str | None
    __asunto: str | None
    __fecha_desde: date | None
    __fecha_hasta: date | None
    __remitente: Usuario | None
    __estado_documento: EstadoDocumento | None

    def __init__(self, *,
                 numero_expediente: str | None = None,
                 asunto: str | None = None,
                 fecha_desde: date | None = None,
                 fecha_hasta: date | None = None,
                 remitente: Usuario | None = None,
                 estado_documento: EstadoDocumento | None = None,
                 ) -> None:
        _validar(numero_expediente, str | None, "numero_expediente")
        self.__numero_expediente = numero_expediente
        _validar(asunto, str | None, "asunto")
        self.__asunto = asunto
        _validar(fecha_desde, date | None, "fecha_desde")
        self.__fecha_desde = fecha_desde
        _validar(fecha_hasta, date | None, "fecha_hasta")
        self.__fecha_hasta = fecha_hasta
        _validar(remitente, Usuario | None, "remitente")
        self.__remitente = remitente
        _validar(estado_documento, EstadoDocumento | None, "estado_documento")
        self.__estado_documento = estado_documento
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            raise ValueError("La fecha inicial no puede superar la fecha final.")

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'numero_expediente': self.__numero_expediente,
            'asunto': self.__asunto,
            'fecha_desde': self.__fecha_desde,
            'fecha_hasta': self.__fecha_hasta,
            'remitente': self.__remitente,
            'estado_documento': self.__estado_documento,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def numero_expediente(self) -> str | None:
        return self.__numero_expediente

    @numero_expediente.setter
    def numero_expediente(self, valor: str | None) -> None:
        _validar(valor, str | None, "numero_expediente")
        self.__numero_expediente = valor

    def coincide(self, documento: Documento) -> bool:
        datos = documento.consultar()
        tramite = datos["tramite"].consultar()
        # El rango de fechas se interpreta en la hora local de la universidad.
        fecha = fecha_local(tramite["fecha_hora_registro"])
        return ((self.__numero_expediente is None or str(documento.numero_expediente) == self.__numero_expediente)
            and (self.__asunto is None or self.__asunto.casefold() in tramite["asunto"].casefold())
            and (self.__fecha_desde is None or fecha >= self.__fecha_desde)
            and (self.__fecha_hasta is None or fecha <= self.__fecha_hasta)
            and (self.__remitente is None or tramite["remitente"] is self.__remitente)
            and (self.__estado_documento is None or documento.estado is self.__estado_documento))


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class MotorBusqueda:
    """Busca documentos activos y archivados según un criterio (RF 13)."""
    __slots__ = ('__repositorio',)
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __repositorio: RepositorioDocumentos

    def __init__(self, *,
                 repositorio: RepositorioDocumentos,
                 ) -> None:
        _validar(repositorio, RepositorioDocumentos, "repositorio")
        self.__repositorio = repositorio

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'repositorio': self.__repositorio,
        }
        return _vista(datos)

    def buscar(self, criterio: CriterioBusqueda, usuario: Usuario) -> tuple[Documento, ...]:
        _requerir(usuario, Permiso.VISUALIZAR)
        # La búsqueda consulta activos y archivados; desarchivar es una operación separada.
        return tuple(d for d in self.__repositorio.listar_documentos()
                     if d.estado in {EstadoDocumento.ACTIVO, EstadoDocumento.ARCHIVADO}
                     and criterio.coincide(d))


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class Desarchivamiento:
    """Registro de la salida de un documento del archivo y su motivo (RF 14)."""
    __slots__ = ('__id_desarchivo', '__documento', '__archivador_origen', '__usuario', '__fecha_hora', '__motivo')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_desarchivo: int
    __documento: Documento
    __archivador_origen: Archivador
    __usuario: Usuario
    __fecha_hora: datetime
    __motivo: str

    def __init__(self, *,
                 id_desarchivo: int,
                 documento: Documento,
                 archivador_origen: Archivador,
                 usuario: Usuario,
                 fecha_hora: datetime,
                 motivo: str,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from registro_documental import Documento

        _validar(id_desarchivo, int, "id_desarchivo")
        self.__id_desarchivo = id_desarchivo
        _validar(documento, Documento, "documento")
        self.__documento = documento
        _validar(archivador_origen, Archivador, "archivador_origen")
        self.__archivador_origen = archivador_origen
        _validar(usuario, Usuario, "usuario")
        self.__usuario = usuario
        _validar(fecha_hora, datetime, "fecha_hora")
        self.__fecha_hora = fecha_hora
        _validar(motivo, str, "motivo")
        self.__motivo = motivo

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_desarchivo': self.__id_desarchivo,
            'documento': self.__documento,
            'archivador_origen': self.__archivador_origen,
            'usuario': self.__usuario,
            'fecha_hora': self.__fecha_hora,
            'motivo': self.__motivo,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def motivo(self) -> str:
        return self.__motivo


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class Archivador:
    """Agrupación lógica de documentos archivados de una dependencia (RF 18)."""
    __slots__ = ('__id_archivador', '__nombre', '__dependencia')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_archivador: int
    __nombre: str
    __dependencia: Dependencia

    def __init__(self, *,
                 id_archivador: int,
                 nombre: str,
                 dependencia: Dependencia,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from flujo_y_seguimiento import Dependencia

        _validar(id_archivador, int, "id_archivador")
        self.__id_archivador = id_archivador
        _validar(nombre, str, "nombre")
        self.__nombre = nombre
        _validar(dependencia, Dependencia, "dependencia")
        self.__dependencia = dependencia

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_archivador': self.__id_archivador,
            'nombre': self.__nombre,
            'dependencia': self.__dependencia,
        }
        return _vista(datos)


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class PoliticaConservacion:
    """Plazo de conservación de la tabla de retención documental (RF 19)."""
    __slots__ = ('__id_politica', '__nombre', '__referencia_pcda', '__version', '__modalidad', '__duracion', '__unidad_plazo', '__evento_inicio')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_politica: int
    __nombre: str
    __referencia_pcda: str
    __version: str
    __modalidad: ModalidadConservacion
    __duracion: int | None
    __unidad_plazo: UnidadPlazo | None
    __evento_inicio: str

    def __init__(self, *,
                 id_politica: int,
                 nombre: str,
                 referencia_pcda: str,
                 version: str,
                 modalidad: ModalidadConservacion,
                 duracion: int | None,
                 unidad_plazo: UnidadPlazo | None,
                 evento_inicio: str,
                 ) -> None:
        _validar(id_politica, int, "id_politica")
        self.__id_politica = id_politica
        _validar(nombre, str, "nombre")
        self.__nombre = nombre
        _validar(referencia_pcda, str, "referencia_pcda")
        self.__referencia_pcda = referencia_pcda
        _validar(version, str, "version")
        self.__version = version
        _validar(modalidad, ModalidadConservacion, "modalidad")
        self.__modalidad = modalidad
        _validar(duracion, int | None, "duracion")
        self.__duracion = duracion
        _validar(unidad_plazo, UnidadPlazo | None, "unidad_plazo")
        self.__unidad_plazo = unidad_plazo
        _validar(evento_inicio, str, "evento_inicio")
        self.__evento_inicio = evento_inicio
        if modalidad is ModalidadConservacion.TEMPORAL:
            if duracion is None or duracion <= 0 or unidad_plazo is None:
                raise ValueError("Una política temporal necesita duración positiva y unidad.")
        else:
            if duracion is not None or unidad_plazo is not None:
                raise ValueError("La conservación permanente no establece plazo de eliminación.")

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_politica': self.__id_politica,
            'nombre': self.__nombre,
            'referencia_pcda': self.__referencia_pcda,
            'version': self.__version,
            'modalidad': self.__modalidad,
            'duracion': self.__duracion,
            'unidad_plazo': self.__unidad_plazo,
            'evento_inicio': self.__evento_inicio,
        }
        return _vista(datos)

    def fecha_vencimiento(self, inicio: date) -> date | None:
        if self.__modalidad is ModalidadConservacion.PERMANENTE:
            return None
        if self.__unidad_plazo is UnidadPlazo.DIAS:
            return inicio + timedelta(days=self.__duracion)
        meses = self.__duracion if self.__unidad_plazo is UnidadPlazo.MESES else self.__duracion*12
        indice = inicio.year*12 + inicio.month-1 + meses
        anio, mes = indice//12, indice%12+1
        return date(anio, mes, min(inicio.day, calendar.monthrange(anio, mes)[1]))

    def plazo_cumplido(self, inicio: date, corte: date) -> bool:
        vencimiento = self.fecha_vencimiento(inicio)
        return vencimiento is not None and corte >= vencimiento


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class RegistroArchivamiento:
    """Registro del ingreso de un documento al archivo (RF 18)."""
    __slots__ = ('__id_archivamiento', '__documento', '__archivador', '__usuario', '__fecha_hora', '__politica_aplicada')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_archivamiento: int
    __documento: Documento
    __archivador: Archivador
    __usuario: Usuario
    __fecha_hora: datetime
    __politica_aplicada: PoliticaConservacion | None

    def __init__(self, *,
                 id_archivamiento: int,
                 documento: Documento,
                 archivador: Archivador,
                 usuario: Usuario,
                 fecha_hora: datetime,
                 politica_aplicada: PoliticaConservacion | None,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from registro_documental import Documento

        _validar(id_archivamiento, int, "id_archivamiento")
        self.__id_archivamiento = id_archivamiento
        _validar(documento, Documento, "documento")
        self.__documento = documento
        _validar(archivador, Archivador, "archivador")
        self.__archivador = archivador
        _validar(usuario, Usuario, "usuario")
        self.__usuario = usuario
        _validar(fecha_hora, datetime, "fecha_hora")
        self.__fecha_hora = fecha_hora
        _validar(politica_aplicada, PoliticaConservacion | None, "politica_aplicada")
        self.__politica_aplicada = politica_aplicada

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_archivamiento': self.__id_archivamiento,
            'documento': self.__documento,
            'archivador': self.__archivador,
            'usuario': self.__usuario,
            'fecha_hora': self.__fecha_hora,
            'politica_aplicada': self.__politica_aplicada,
        }
        return _vista(datos)


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class RegistroEliminacion:
    """Resultado de la eliminación de un archivo confirmada por TI (RF 19)."""
    __slots__ = ('__id_eliminacion', '__archivo', '__ejecutor', '__fecha_hora', '__motivo', '__resultado', '__detalle_resultado')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_eliminacion: int
    __archivo: ArchivoElectronico
    __ejecutor: Usuario
    __fecha_hora: datetime
    __motivo: str
    __resultado: ResultadoEliminacion
    __detalle_resultado: str | None

    def __init__(self, *,
                 id_eliminacion: int,
                 archivo: ArchivoElectronico,
                 ejecutor: Usuario,
                 fecha_hora: datetime,
                 motivo: str,
                 resultado: ResultadoEliminacion,
                 detalle_resultado: str | None,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from registro_documental import ArchivoElectronico

        _validar(id_eliminacion, int, "id_eliminacion")
        self.__id_eliminacion = id_eliminacion
        _validar(archivo, ArchivoElectronico, "archivo")
        self.__archivo = archivo
        _validar(ejecutor, Usuario, "ejecutor")
        self.__ejecutor = ejecutor
        _validar(fecha_hora, datetime, "fecha_hora")
        self.__fecha_hora = fecha_hora
        _validar(motivo, str, "motivo")
        self.__motivo = motivo
        _validar(resultado, ResultadoEliminacion, "resultado")
        self.__resultado = resultado
        _validar(detalle_resultado, str | None, "detalle_resultado")
        self.__detalle_resultado = detalle_resultado

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_eliminacion': self.__id_eliminacion,
            'archivo': self.__archivo,
            'ejecutor': self.__ejecutor,
            'fecha_hora': self.__fecha_hora,
            'motivo': self.__motivo,
            'resultado': self.__resultado,
            'detalle_resultado': self.__detalle_resultado,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def resultado(self) -> ResultadoEliminacion:
        return self.__resultado
