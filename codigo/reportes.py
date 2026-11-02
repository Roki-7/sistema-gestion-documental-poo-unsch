"""06 · Reportes · SGD–UNSCH.

Requerimientos: RF 20, 21.
Conserva las clases y atributos del análisis y de su diagrama.
El programa general es main.py; este módulo se importa desde allí.
"""
from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from collections import Counter
from collections.abc import Callable
from collections.abc import Mapping
from copy import deepcopy
from datetime import date
from datetime import datetime
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Protocol
from typing import runtime_checkable
from zoneinfo import ZoneInfo
from typing import TYPE_CHECKING
from usuarios_y_seguridad import Permiso, Usuario, ahora, _requerir, _validar, _vista

if TYPE_CHECKING:
    from flujo_y_seguimiento import Dependencia, EstadoTramite


@runtime_checkable
class RepositorioReportes(Protocol):
    def consultar(self, tipo: str, filtros: Mapping[str, object],
                  fecha_corte: datetime) -> list[dict[str, object]]: ...


class EventoMedicion(str, Enum):
    REGISTRO = 'registro'
    RECEPCION = 'recepcion'
    FINALIZACION = 'finalizacion'


class UnidadTiempo(str, Enum):
    SEGUNDOS = 'SEGUNDOS'
    MINUTOS = 'MINUTOS'
    HORAS = 'HORAS'


class AgrupacionCarga(str, Enum):
    USUARIO = 'usuario'
    DEPENDENCIA = 'dependencia'


class UnidadCarga(str, Enum):
    DOCUMENTOS = 'documento'
    TRAMITES = 'tramite'


class FrecuenciaReporte(str, Enum):
    DIARIA = 'DIARIA'
    SEMANAL = 'SEMANAL'


class OrigenEjecucion(str, Enum):
    MANUAL = 'MANUAL'
    PROGRAMADA = 'PROGRAMADA'


# ABSTRACCIÓN: base común de los tres tipos de reporte.
class Reporte(ABC):
    """Base abstracta de los reportes: filtra, personaliza columnas y genera resultados (RF 20, 21)."""
    __slots__ = ('__titulo', '__filtros', '__repositorio', '__columnas_seleccionadas', '__orden_presentacion')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __titulo: str
    __filtros: FiltroReporte
    __repositorio: RepositorioReportes
    __columnas_seleccionadas: tuple[str, ...]
    __orden_presentacion: tuple[str, ...]

    def __init__(self, *,
                 titulo: str,
                 filtros: FiltroReporte,
                 repositorio: RepositorioReportes,
                 columnas_seleccionadas: tuple[str, ...] = (),
                 orden_presentacion: tuple[str, ...] = (),
                 ) -> None:
        _validar(titulo, str, "titulo")
        self.__titulo = titulo
        _validar(filtros, FiltroReporte, "filtros")
        self.__filtros = filtros
        _validar(repositorio, RepositorioReportes, "repositorio")
        self.__repositorio = repositorio
        _validar(columnas_seleccionadas, tuple[str, ...], "columnas_seleccionadas")
        self.__columnas_seleccionadas = columnas_seleccionadas
        _validar(orden_presentacion, tuple[str, ...], "orden_presentacion")
        self.__orden_presentacion = orden_presentacion
        self.personalizar(columnas_seleccionadas, orden_presentacion)

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'titulo': self.__titulo,
            'filtros': self.__filtros,
            'repositorio': self.__repositorio,
            'columnas_seleccionadas': self.__columnas_seleccionadas,
            'orden_presentacion': self.__orden_presentacion,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def titulo(self) -> str:
        return self.__titulo

    @titulo.setter
    def titulo(self, valor: str) -> None:
        _validar(valor, str, "titulo")
        self.__titulo = valor

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def columnas_seleccionadas(self) -> tuple[str, ...]:
        return tuple(self.__columnas_seleccionadas)

    def personalizar(self, columnas: tuple[str, ...], orden: tuple[str, ...] = ()) -> None:
        _validar(columnas, tuple[str, ...], "columnas")
        _validar(orden, tuple[str, ...], "orden")
        if len(set(columnas)) != len(columnas) or len(set(orden)) != len(orden):
            raise ValueError("No repita columnas.")
        if not set(orden) <= set(columnas):
            raise ValueError("El orden debe referirse a columnas seleccionadas.")
        self.__columnas_seleccionadas, self.__orden_presentacion = columnas, orden

    def _parametros_especificos(self) -> dict[str, object]:
        """Cada especialización conserva también sus criterios de cálculo."""
        return {}

    def _filas_base(self, tipo: str, corte: datetime) -> list[dict[str, object]]:
        return deepcopy(self.__repositorio.consultar(tipo, self.__filtros.consultar(), corte))

    @abstractmethod
    def _construir_filas(self, corte: datetime,
                        calendario_habil: Callable[[datetime, datetime], float] | None) -> list[dict[str, object]]:
        raise NotImplementedError

    def generar(self, solicitante: Usuario,
                origen: OrigenEjecucion = OrigenEjecucion.MANUAL,
                fecha_corte: datetime | None = None,
                calendario_habil: Callable[[datetime, datetime], float] | None = None) -> ResultadoReporte:
        # Todo reporte, manual o programado, se atribuye a un usuario autorizado.
        _validar(solicitante, Usuario, "solicitante")
        _requerir(solicitante, Permiso.VISUALIZAR)
        corte = fecha_corte or ahora()
        _validar(corte, datetime, "fecha_corte")
        filas = self._construir_filas(corte, calendario_habil)
        columnas = self.__columnas_seleccionadas
        if columnas:
            for fila in filas:
                if not set(columnas) <= set(fila):
                    raise ValueError("Una columna seleccionada no existe en el resultado.")
            orden = self.__orden_presentacion + tuple(c for c in columnas if c not in self.__orden_presentacion)
            filas = [{c: fila[c] for c in orden} for fila in filas]
        return ResultadoReporte(fecha_generacion=ahora(), fecha_corte=corte,
            solicitante=solicitante, origen_ejecucion=origen,
            parametros_aplicados={"titulo": self.__titulo, "filtros": dict(self.__filtros.consultar()),
                                 "columnas": columnas, "orden": self.__orden_presentacion,
                                 **self._parametros_especificos()}, filas=filas)


# HERENCIA: reutilización de los atributos y operaciones de la base.
class ReporteEstadoTramites(Reporte):
    """Cuenta los trámites por estado."""
    __slots__ = ()

    # POLIMORFISMO: hereda el constructor y consultar(); solo redefine el cálculo.
    def _construir_filas(self, corte: datetime, calendario_habil=None) -> list[dict[str, object]]:
        conteo = Counter(str(fila["estado"]) for fila in self._filas_base("estado", corte))
        return [{"estado": estado, "cantidad": cantidad} for estado, cantidad in sorted(conteo.items())]


# HERENCIA: reutilización de los atributos y operaciones de la base.
class ReporteTiemposRespuesta(Reporte):
    """Mide la duración entre dos eventos del trámite."""
    __slots__ = ('__evento_inicio', '__evento_fin', '__unidad_tiempo', '__usa_tiempo_habil')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __evento_inicio: EventoMedicion
    __evento_fin: EventoMedicion
    __unidad_tiempo: UnidadTiempo
    __usa_tiempo_habil: bool

    def __init__(self, *,
                 titulo: str,
                 filtros: FiltroReporte,
                 repositorio: RepositorioReportes,
                 columnas_seleccionadas: tuple[str, ...] = (),
                 orden_presentacion: tuple[str, ...] = (),
                 evento_inicio: EventoMedicion,
                 evento_fin: EventoMedicion,
                 unidad_tiempo: UnidadTiempo,
                 usa_tiempo_habil: bool,
                 ) -> None:
        super().__init__(titulo=titulo, filtros=filtros, repositorio=repositorio, columnas_seleccionadas=columnas_seleccionadas, orden_presentacion=orden_presentacion)
        _validar(evento_inicio, EventoMedicion, "evento_inicio")
        self.__evento_inicio = evento_inicio
        _validar(evento_fin, EventoMedicion, "evento_fin")
        self.__evento_fin = evento_fin
        _validar(unidad_tiempo, UnidadTiempo, "unidad_tiempo")
        self.__unidad_tiempo = unidad_tiempo
        _validar(usa_tiempo_habil, bool, "usa_tiempo_habil")
        self.__usa_tiempo_habil = usa_tiempo_habil

    def consultar(self) -> Mapping[str, object]:
        datos = dict(super().consultar())
        datos.update({
            'evento_inicio': self.__evento_inicio,
            'evento_fin': self.__evento_fin,
            'unidad_tiempo': self.__unidad_tiempo,
            'usa_tiempo_habil': self.__usa_tiempo_habil,
        })
        return _vista(datos)

    def _parametros_especificos(self) -> dict[str, object]:
        return {"evento_inicio": self.__evento_inicio.value, "evento_fin": self.__evento_fin.value,
                "unidad_tiempo": self.__unidad_tiempo.value, "usa_tiempo_habil": self.__usa_tiempo_habil}

    def _construir_filas(self, corte: datetime, calendario_habil=None) -> list[dict[str, object]]:
        if self.__usa_tiempo_habil and calendario_habil is None:
            raise ValueError("Debe proporcionar el calendario hábil institucional.")
        divisor = {UnidadTiempo.SEGUNDOS: 1, UnidadTiempo.MINUTOS: 60, UnidadTiempo.HORAS: 3600}[self.__unidad_tiempo]
        resultado = []
        for fila in self._filas_base("tiempos", corte):
            inicio = fila.get(self.__evento_inicio.value)
            fin = fila.get(self.__evento_fin.value)
            if inicio is None or fin is None or inicio > corte or fin > corte:
                continue
            if fin < inicio:
                raise ValueError("Un evento final no puede preceder al evento inicial.")
            segundos = calendario_habil(inicio, fin) if self.__usa_tiempo_habil else (fin-inicio).total_seconds()
            if segundos < 0:
                raise ValueError("El calendario devolvió una duración negativa.")
            resultado.append({"expediente": fila["expediente"], "duracion": segundos/divisor,
                              "unidad": self.__unidad_tiempo.value})
        return resultado


# HERENCIA: reutilización de los atributos y operaciones de la base.
class ReporteCargaTrabajo(Reporte):
    """Cuenta trámites o documentos por usuario o dependencia."""
    __slots__ = ('__agrupar_por', '__unidad_carga')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __agrupar_por: AgrupacionCarga
    __unidad_carga: UnidadCarga

    def __init__(self, *,
                 titulo: str,
                 filtros: FiltroReporte,
                 repositorio: RepositorioReportes,
                 columnas_seleccionadas: tuple[str, ...] = (),
                 orden_presentacion: tuple[str, ...] = (),
                 agrupar_por: AgrupacionCarga,
                 unidad_carga: UnidadCarga,
                 ) -> None:
        super().__init__(titulo=titulo, filtros=filtros, repositorio=repositorio, columnas_seleccionadas=columnas_seleccionadas, orden_presentacion=orden_presentacion)
        _validar(agrupar_por, AgrupacionCarga, "agrupar_por")
        self.__agrupar_por = agrupar_por
        _validar(unidad_carga, UnidadCarga, "unidad_carga")
        self.__unidad_carga = unidad_carga

    def consultar(self) -> Mapping[str, object]:
        datos = dict(super().consultar())
        datos.update({
            'agrupar_por': self.__agrupar_por,
            'unidad_carga': self.__unidad_carga,
        })
        return _vista(datos)

    def _parametros_especificos(self) -> dict[str, object]:
        return {"agrupar_por": self.__agrupar_por.value, "unidad_carga": self.__unidad_carga.value}

    def _construir_filas(self, corte: datetime, calendario_habil=None) -> list[dict[str, object]]:
        agrupaciones = {}
        for fila in self._filas_base("carga", corte):
            clave = str(fila[self.__agrupar_por.value])
            # El conjunto evita contar varias veces un trámite por sus documentos.
            agrupaciones.setdefault(clave, set()).add(fila[self.__unidad_carga.value])
        return [{"grupo": clave, "cantidad": len(ids), "unidad": self.__unidad_carga.value}
                for clave, ids in sorted(agrupaciones.items())]


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class ResultadoReporte:
    """Instantánea inmutable de un reporte generado y sus parámetros."""
    __slots__ = ('__fecha_generacion', '__fecha_corte', '__solicitante', '__origen_ejecucion', '__parametros_aplicados', '__filas')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __fecha_generacion: datetime
    __fecha_corte: datetime
    __solicitante: Usuario | None
    __origen_ejecucion: OrigenEjecucion
    __parametros_aplicados: dict[str, object]
    __filas: list[dict[str, object]]

    def __init__(self, *,
                 fecha_generacion: datetime,
                 fecha_corte: datetime,
                 solicitante: Usuario | None,
                 origen_ejecucion: OrigenEjecucion,
                 parametros_aplicados: dict[str, object],
                 filas: list[dict[str, object]],
                 ) -> None:
        _validar(fecha_generacion, datetime, "fecha_generacion")
        self.__fecha_generacion = fecha_generacion
        _validar(fecha_corte, datetime, "fecha_corte")
        self.__fecha_corte = fecha_corte
        _validar(solicitante, Usuario | None, "solicitante")
        self.__solicitante = solicitante
        _validar(origen_ejecucion, OrigenEjecucion, "origen_ejecucion")
        self.__origen_ejecucion = origen_ejecucion
        _validar(parametros_aplicados, dict[str, object], "parametros_aplicados")
        self.__parametros_aplicados = deepcopy(parametros_aplicados)
        _validar(filas, list[dict[str, object]], "filas")
        self.__filas = deepcopy(filas)
        if fecha_corte > fecha_generacion:
            raise ValueError("La fecha de corte no puede superar la fecha de generación.")

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'fecha_generacion': self.__fecha_generacion,
            'fecha_corte': self.__fecha_corte,
            'solicitante': self.__solicitante,
            'origen_ejecucion': self.__origen_ejecucion,
            'parametros_aplicados': self.__parametros_aplicados,
            'filas': self.__filas,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def fecha_corte(self) -> datetime:
        return self.__fecha_corte


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class ProgramacionReporte:
    """Ejecución periódica, diaria o semanal, de un reporte (RF 21)."""
    __slots__ = ('__id_programacion', '__reporte', '__frecuencia', '__zona_horaria', '__proxima_ejecucion', '__creada_por', '__activa')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_programacion: int
    __reporte: Reporte
    __frecuencia: FrecuenciaReporte
    __zona_horaria: str
    __proxima_ejecucion: datetime
    __creada_por: Usuario
    __activa: bool

    def __init__(self, *,
                 id_programacion: int,
                 reporte: Reporte,
                 frecuencia: FrecuenciaReporte,
                 zona_horaria: str,
                 proxima_ejecucion: datetime,
                 creada_por: Usuario,
                 activa: bool,
                 ) -> None:
        _validar(id_programacion, int, "id_programacion")
        self.__id_programacion = id_programacion
        _validar(reporte, Reporte, "reporte")
        self.__reporte = reporte
        _validar(frecuencia, FrecuenciaReporte, "frecuencia")
        self.__frecuencia = frecuencia
        _validar(zona_horaria, str, "zona_horaria")
        self.__zona_horaria = zona_horaria
        _validar(proxima_ejecucion, datetime, "proxima_ejecucion")
        self.__proxima_ejecucion = proxima_ejecucion
        _validar(creada_por, Usuario, "creada_por")
        self.__creada_por = creada_por
        _validar(activa, bool, "activa")
        self.__activa = activa
        ZoneInfo(zona_horaria)

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_programacion': self.__id_programacion,
            'reporte': self.__reporte,
            'frecuencia': self.__frecuencia,
            'zona_horaria': self.__zona_horaria,
            'proxima_ejecucion': self.__proxima_ejecucion,
            'creada_por': self.__creada_por,
            'activa': self.__activa,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def proxima_ejecucion(self) -> datetime:
        return self.__proxima_ejecucion

    def ejecutar_si_corresponde(self, instante: datetime | None = None,
                               calendario_habil: Callable[[datetime, datetime], float] | None = None) -> ResultadoReporte | None:
        instante = instante or ahora()
        if not self.__activa or instante < self.__proxima_ejecucion:
            return None
        resultado = self.__reporte.generar(self.__creada_por, OrigenEjecucion.PROGRAMADA,
                                           fecha_corte=instante, calendario_habil=calendario_habil)
        zona = ZoneInfo(self.__zona_horaria)
        siguiente = self.__proxima_ejecucion.astimezone(zona)
        paso = {FrecuenciaReporte.DIARIA: 1, FrecuenciaReporte.SEMANAL: 7}[self.__frecuencia]
        while siguiente <= instante:
            siguiente += timedelta(days=paso)
        self.__proxima_ejecucion = siguiente
        return resultado

    def desactivar(self) -> None:
        self.__activa = False


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class FiltroReporte:
    """Rango de fechas, dependencia, responsable y estado que acotan un reporte."""
    __slots__ = ('__fecha_desde', '__fecha_hasta', '__dependencia', '__responsable', '__estado_tramite')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __fecha_desde: date | None
    __fecha_hasta: date | None
    __dependencia: Dependencia | None
    __responsable: Usuario | None
    __estado_tramite: EstadoTramite | None

    def __init__(self, *,
                 fecha_desde: date | None = None,
                 fecha_hasta: date | None = None,
                 dependencia: Dependencia | None = None,
                 responsable: Usuario | None = None,
                 estado_tramite: EstadoTramite | None = None,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from flujo_y_seguimiento import Dependencia, EstadoTramite

        _validar(fecha_desde, date | None, "fecha_desde")
        self.__fecha_desde = fecha_desde
        _validar(fecha_hasta, date | None, "fecha_hasta")
        self.__fecha_hasta = fecha_hasta
        _validar(dependencia, Dependencia | None, "dependencia")
        self.__dependencia = dependencia
        _validar(responsable, Usuario | None, "responsable")
        self.__responsable = responsable
        _validar(estado_tramite, EstadoTramite | None, "estado_tramite")
        self.__estado_tramite = estado_tramite
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            raise ValueError("La fecha inicial no puede superar la fecha final.")

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'fecha_desde': self.__fecha_desde,
            'fecha_hasta': self.__fecha_hasta,
            'dependencia': self.__dependencia,
            'responsable': self.__responsable,
            'estado_tramite': self.__estado_tramite,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def fecha_desde(self) -> date | None:
        return self.__fecha_desde

    @fecha_desde.setter
    def fecha_desde(self, valor: date | None) -> None:
        _validar(valor, date | None, "fecha_desde")
        if valor and self.__fecha_hasta and valor > self.__fecha_hasta:
            raise ValueError("Rango de fechas inválido.")
        self.__fecha_desde = valor

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def fecha_hasta(self) -> date | None:
        return self.__fecha_hasta

    @fecha_hasta.setter
    def fecha_hasta(self, valor: date | None) -> None:
        _validar(valor, date | None, "fecha_hasta")
        if valor and self.__fecha_desde and self.__fecha_desde > valor:
            raise ValueError("Rango de fechas inválido.")
        self.__fecha_hasta = valor


def _columnas(filas: tuple[Mapping[str, object], ...]) -> list[str]:
    """Une las columnas de todas las filas, en el orden en que aparecen."""
    return list(dict.fromkeys(c for fila in filas for c in fila))


# ABSTRACCIÓN: contrato de operaciones para sus implementaciones.
class ExportadorReporte(ABC):
    """Contrato para exportar un resultado de reporte a un archivo."""
    __slots__ = ()

    @abstractmethod
    def exportar(self, resultado: ResultadoReporte, destino: Path) -> Path:
        raise NotImplementedError


# POLIMORFISMO: implementación del contrato de su clase base.
class ExportadorExcel(ExportadorReporte):
    """Exporta el resultado a una hoja de cálculo .xlsx."""
    __slots__ = ()

    def consultar(self) -> Mapping[str, object]:
        datos = {
        }
        return _vista(datos)

    def exportar(self, resultado: ResultadoReporte, destino: Path) -> Path:
        from openpyxl import Workbook
        destino = Path(destino)
        if destino.suffix.lower() != ".xlsx":
            raise ValueError("Use extensión .xlsx.")
        filas = resultado.consultar()["filas"]
        libro = Workbook()
        hoja = libro.active
        hoja.title = "Reporte"
        columnas = _columnas(filas)
        if columnas:
            hoja.append(columnas)
        for numero, fila in enumerate(filas, start=2):
            for indice, columna in enumerate(columnas, start=1):
                celda = hoja.cell(row=numero, column=indice, value=fila.get(columna))
                # El contenido documental se guarda como texto: no se ejecutan fórmulas involuntarias.
                if isinstance(celda.value, str) and celda.value.startswith(("=", "+", "-", "@", "\t", "\r")):
                    celda.data_type, celda.quotePrefix = "s", True
        libro.save(destino)
        return destino


# POLIMORFISMO: implementación del contrato de su clase base.
class ExportadorPDF(ExportadorReporte):
    """Exporta el resultado a un documento .pdf."""
    __slots__ = ()

    def consultar(self) -> Mapping[str, object]:
        datos = {
        }
        return _vista(datos)

    def exportar(self, resultado: ResultadoReporte, destino: Path) -> Path:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from xml.sax.saxutils import escape
        destino = Path(destino)
        if destino.suffix.lower() != ".pdf":
            raise ValueError("Use extensión .pdf.")
        datos = resultado.consultar()
        filas = datos["filas"]
        estilo = getSampleStyleSheet()
        elementos = [Paragraph(escape(str(datos["parametros_aplicados"].get("titulo", "Reporte SGD"))), estilo["Title"]),
            Paragraph("Fecha de corte: "+escape(datos["fecha_corte"].isoformat()), estilo["Normal"]), Spacer(1, 12)]
        if filas:
            columnas = _columnas(filas)
            tabla = [[Paragraph(escape(str(c)), estilo["BodyText"]) for c in columnas]]
            tabla += [[Paragraph(escape(str(fila.get(c, ""))), estilo["BodyText"]) for c in columnas] for fila in filas]
            t = Table(tabla, repeatRows=1, colWidths=[760/len(columnas)]*len(columnas))
            t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EDF7FD")),
                                  ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#D5E2EA")),
                                  ("VALIGN", (0,0), (-1,-1), "TOP")]))
            elementos.append(t)
        else:
            elementos.append(Paragraph("Sin resultados para los filtros seleccionados.", estilo["Normal"]))
        SimpleDocTemplate(str(destino), pagesize=landscape(A4), leftMargin=35, rightMargin=35).build(elementos)
        return destino
