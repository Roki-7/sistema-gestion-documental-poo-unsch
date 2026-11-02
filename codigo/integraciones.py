"""07 · Integraciones · SGD–UNSCH.

Requerimientos: RF 15, 22.
Conserva las clases y atributos del análisis y de su diagrama.
El programa general es main.py; este módulo se importa desde allí.
"""
from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from collections.abc import Callable
from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from typing import Protocol
from typing import runtime_checkable
import hashlib
from typing import TYPE_CHECKING
from usuarios_y_seguridad import ahora, _texto, _validar, _vista

if TYPE_CHECKING:
    from registro_documental import ArchivoElectronico, Documento


@runtime_checkable
class ProveedorCredenciales(Protocol):
    def obtener(self) -> Mapping[str, str]: ...


def _validar_conexion(direccion_servicio: str, tiempo_espera_segundos: float) -> None:
    """Reglas comunes a los adaptadores de servicios institucionales externos."""
    if not direccion_servicio.startswith("https://"):
        raise ValueError("Configure una dirección HTTPS del servicio institucional.")
    if tiempo_espera_segundos <= 0:
        raise ValueError("El tiempo de espera debe ser positivo.")


class EstadoValidacionFirma(str, Enum):
    VALIDA = 'VALIDA'
    INVALIDA = 'INVALIDA'
    INDETERMINADA = 'INDETERMINADA'


class EstadoIntercambio(str, Enum):
    PENDIENTE = 'PENDIENTE'
    EN_PROCESO = 'EN_PROCESO'
    CONFIRMADO = 'CONFIRMADO'
    FALLIDO = 'FALLIDO'
    INDETERMINADO = 'INDETERMINADO'


class DireccionIntercambio(str, Enum):
    ENVIO = 'ENVIO'
    RECEPCION = 'RECEPCION'


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class ValidacionFirma:
    """Resultado de consultar la validez de las firmas digitales de un archivo (RF 15)."""
    __slots__ = ('__id_validacion', '__archivo', '__huella_archivo', '__algoritmo_huella', '__fecha_consulta', '__servicio_utilizado', '__referencia_respuesta', '__resultados_firmas', '__consulta_completada', '__detalle_consulta')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_validacion: int
    __archivo: ArchivoElectronico
    __huella_archivo: str
    __algoritmo_huella: str
    __fecha_consulta: datetime
    __servicio_utilizado: str
    __referencia_respuesta: str | None
    __resultados_firmas: list[ResultadoFirma]
    __consulta_completada: bool
    __detalle_consulta: str | None

    def __init__(self, *,
                 id_validacion: int,
                 archivo: ArchivoElectronico,
                 huella_archivo: str,
                 algoritmo_huella: str,
                 fecha_consulta: datetime,
                 servicio_utilizado: str,
                 referencia_respuesta: str | None = None,
                 resultados_firmas: list[ResultadoFirma] | None = None,
                 consulta_completada: bool = False,
                 detalle_consulta: str | None = None,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from registro_documental import ArchivoElectronico

        _validar(id_validacion, int, "id_validacion")
        self.__id_validacion = id_validacion
        _validar(archivo, ArchivoElectronico, "archivo")
        self.__archivo = archivo
        _validar(huella_archivo, str, "huella_archivo")
        self.__huella_archivo = huella_archivo
        _validar(algoritmo_huella, str, "algoritmo_huella")
        self.__algoritmo_huella = algoritmo_huella
        _validar(fecha_consulta, datetime, "fecha_consulta")
        self.__fecha_consulta = fecha_consulta
        _validar(servicio_utilizado, str, "servicio_utilizado")
        self.__servicio_utilizado = servicio_utilizado
        _validar(referencia_respuesta, str | None, "referencia_respuesta")
        self.__referencia_respuesta = referencia_respuesta
        if resultados_firmas is None:
            resultados_firmas = []
        _validar(resultados_firmas, list[ResultadoFirma], "resultados_firmas")
        self.__resultados_firmas = list(resultados_firmas)
        _validar(consulta_completada, bool, "consulta_completada")
        self.__consulta_completada = consulta_completada
        _validar(detalle_consulta, str | None, "detalle_consulta")
        self.__detalle_consulta = detalle_consulta

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_validacion': self.__id_validacion,
            'archivo': self.__archivo,
            'huella_archivo': self.__huella_archivo,
            'algoritmo_huella': self.__algoritmo_huella,
            'fecha_consulta': self.__fecha_consulta,
            'servicio_utilizado': self.__servicio_utilizado,
            'referencia_respuesta': self.__referencia_respuesta,
            'resultados_firmas': self.__resultados_firmas,
            'consulta_completada': self.__consulta_completada,
            'detalle_consulta': self.__detalle_consulta,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def fecha_consulta(self) -> datetime:
        return self.__fecha_consulta

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def resultados_firmas(self) -> tuple[ResultadoFirma, ...]:
        return tuple(self.__resultados_firmas)

    def es_valida(self) -> bool:
        # Un archivo sin firmas o una consulta fallida nunca se consideran válidos.
        return (self.__consulta_completada and bool(self.__resultados_firmas)
                and all(f.estado is EstadoValidacionFirma.VALIDA for f in self.__resultados_firmas))

    def corresponde_al_contenido(self, contenido: bytes) -> bool:
        return hashlib.sha256(contenido).hexdigest() == self.__huella_archivo


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class ResultadoFirma:
    """Estado de validación de una firma individual."""
    __slots__ = ('__referencia_firma', '__identificacion_firmante', '__estado', '__detalle_resultado')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __referencia_firma: str
    __identificacion_firmante: str | None
    __estado: EstadoValidacionFirma
    __detalle_resultado: str | None

    def __init__(self, *,
                 referencia_firma: str,
                 identificacion_firmante: str | None = None,
                 estado: EstadoValidacionFirma,
                 detalle_resultado: str | None = None,
                 ) -> None:
        _validar(referencia_firma, str, "referencia_firma")
        self.__referencia_firma = referencia_firma
        _validar(identificacion_firmante, str | None, "identificacion_firmante")
        self.__identificacion_firmante = identificacion_firmante
        _validar(estado, EstadoValidacionFirma, "estado")
        self.__estado = estado
        _validar(detalle_resultado, str | None, "detalle_resultado")
        self.__detalle_resultado = detalle_resultado

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'referencia_firma': self.__referencia_firma,
            'identificacion_firmante': self.__identificacion_firmante,
            'estado': self.__estado,
            'detalle_resultado': self.__detalle_resultado,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def estado(self) -> EstadoValidacionFirma:
        return self.__estado


# ABSTRACCIÓN: contrato de operaciones para sus implementaciones.
class ServicioValidacionFirma(ABC):
    """Contrato del servicio de validación de firmas digitales."""
    __slots__ = ()

    @abstractmethod
    def validar(self, archivo: ArchivoElectronico, contenido: bytes,
                id_validacion: int, transporte: Callable | None = None) -> ValidacionFirma:
        raise NotImplementedError


# POLIMORFISMO: implementación del contrato de su clase base.
class AdaptadorValidacionFirma(ServicioValidacionFirma):
    """Conecta el sistema con el servicio de firmas de la universidad."""
    __slots__ = ('__direccion_servicio', '__tiempo_espera_segundos', '__proveedor_credenciales')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __direccion_servicio: str
    __tiempo_espera_segundos: float
    __proveedor_credenciales: ProveedorCredenciales | None

    def __init__(self, *,
                 direccion_servicio: str,
                 tiempo_espera_segundos: float = 30.0,
                 proveedor_credenciales: ProveedorCredenciales | None = None,
                 ) -> None:
        _validar(direccion_servicio, str, "direccion_servicio")
        self.__direccion_servicio = direccion_servicio
        _validar(tiempo_espera_segundos, float, "tiempo_espera_segundos")
        self.__tiempo_espera_segundos = tiempo_espera_segundos
        _validar(proveedor_credenciales, ProveedorCredenciales | None, "proveedor_credenciales")
        self.__proveedor_credenciales = proveedor_credenciales
        _validar_conexion(direccion_servicio, tiempo_espera_segundos)

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'direccion_servicio': self.__direccion_servicio,
            'tiempo_espera_segundos': self.__tiempo_espera_segundos,
            'proveedor_credenciales': self.__proveedor_credenciales,
        }
        return _vista(datos)

    def validar(self, archivo: ArchivoElectronico, contenido: bytes,
                id_validacion: int, transporte: Callable | None = None) -> ValidacionFirma:
        """El transporte normaliza el contrato institucional; no inventa un endpoint PIDE."""

        if transporte is None:
            raise RuntimeError("Falta conectar el transporte del servicio de validación de la universidad.")
        if archivo.fecha_eliminacion is not None:
            raise ValueError("El archivo fue eliminado.")
        if not isinstance(contenido, bytes) or not contenido:
            raise ValueError("Proporcione los bytes reales del archivo.")
        huella = hashlib.sha256(contenido).hexdigest()
        credenciales = dict(self.__proveedor_credenciales.obtener()) if self.__proveedor_credenciales else {}
        referencia, resultados, completada, detalle = None, [], False, None
        try:
            respuesta = transporte(self.__direccion_servicio,
                {"contenido": contenido, "sha256": huella}, self.__tiempo_espera_segundos, credenciales)
            # Respuesta interna normalizada; su traducción corresponde al transporte.
            if respuesta.get("consulta_completada") is not True or not isinstance(respuesta.get("firmas"), list):
                raise ValueError("Respuesta de validación incompleta.")
            for firma in respuesta["firmas"]:
                resultados.append(ResultadoFirma(referencia_firma=firma["referencia"],
                    identificacion_firmante=firma.get("firmante"),
                    estado=EstadoValidacionFirma(firma["estado"]), detalle_resultado=firma.get("detalle")))
            referencia = respuesta.get("referencia")
            if referencia is not None:
                referencia = _texto(referencia, "referencia")
            completada = True
        except Exception as exc:
            detalle, resultados = f"No se completó la validación: {type(exc).__name__}", []
        return ValidacionFirma(id_validacion=id_validacion, archivo=archivo,
            huella_archivo=huella, algoritmo_huella="SHA-256", fecha_consulta=ahora(),
            servicio_utilizado=self.__direccion_servicio, referencia_respuesta=referencia,
            resultados_firmas=resultados, consulta_completada=completada, detalle_consulta=detalle)


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class EntidadInteroperante:
    """Entidad pública con la que se intercambian documentos (RF 22)."""
    __slots__ = ('__codigo', '__nombre')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __codigo: str
    __nombre: str

    def __init__(self, *,
                 codigo: str,
                 nombre: str,
                 ) -> None:
        _validar(codigo, str, "codigo")
        self.__codigo = codigo
        _validar(nombre, str, "nombre")
        self.__nombre = nombre

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'codigo': self.__codigo,
            'nombre': self.__nombre,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def codigo(self) -> str:
        return self.__codigo


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class IntercambioDocumentario:
    """Envío o recepción de un documento a través de la PIDE (RF 22)."""
    __slots__ = ('__id_intercambio', '__id_correlacion', '__direccion', '__documento', '__entidad_origen', '__entidad_destino', '__fecha_inicio', '__fecha_confirmacion', '__estado', '__referencia_externa', '__detalle_resultado')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_intercambio: int
    __id_correlacion: str
    __direccion: DireccionIntercambio
    __documento: Documento
    __entidad_origen: EntidadInteroperante
    __entidad_destino: EntidadInteroperante
    __fecha_inicio: datetime
    __fecha_confirmacion: datetime | None
    __estado: EstadoIntercambio
    __referencia_externa: str | None
    __detalle_resultado: str | None

    def __init__(self, *,
                 id_intercambio: int,
                 id_correlacion: str,
                 direccion: DireccionIntercambio,
                 documento: Documento,
                 entidad_origen: EntidadInteroperante,
                 entidad_destino: EntidadInteroperante,
                 fecha_inicio: datetime | None = None,
                 fecha_confirmacion: datetime | None = None,
                 estado: EstadoIntercambio = EstadoIntercambio.PENDIENTE,
                 referencia_externa: str | None = None,
                 detalle_resultado: str | None = None,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from registro_documental import Documento

        _validar(id_intercambio, int, "id_intercambio")
        self.__id_intercambio = id_intercambio
        _validar(id_correlacion, str, "id_correlacion")
        self.__id_correlacion = id_correlacion
        _validar(direccion, DireccionIntercambio, "direccion")
        self.__direccion = direccion
        _validar(documento, Documento, "documento")
        self.__documento = documento
        _validar(entidad_origen, EntidadInteroperante, "entidad_origen")
        self.__entidad_origen = entidad_origen
        _validar(entidad_destino, EntidadInteroperante, "entidad_destino")
        self.__entidad_destino = entidad_destino
        if fecha_inicio is None:
            fecha_inicio = ahora()
        _validar(fecha_inicio, datetime, "fecha_inicio")
        self.__fecha_inicio = fecha_inicio
        _validar(fecha_confirmacion, datetime | None, "fecha_confirmacion")
        self.__fecha_confirmacion = fecha_confirmacion
        _validar(estado, EstadoIntercambio, "estado")
        self.__estado = estado
        _validar(referencia_externa, str | None, "referencia_externa")
        self.__referencia_externa = referencia_externa
        _validar(detalle_resultado, str | None, "detalle_resultado")
        self.__detalle_resultado = detalle_resultado

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_intercambio': self.__id_intercambio,
            'id_correlacion': self.__id_correlacion,
            'direccion': self.__direccion,
            'documento': self.__documento,
            'entidad_origen': self.__entidad_origen,
            'entidad_destino': self.__entidad_destino,
            'fecha_inicio': self.__fecha_inicio,
            'fecha_confirmacion': self.__fecha_confirmacion,
            'estado': self.__estado,
            'referencia_externa': self.__referencia_externa,
            'detalle_resultado': self.__detalle_resultado,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def estado(self) -> EstadoIntercambio:
        return self.__estado

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def referencia_externa(self) -> str | None:
        return self.__referencia_externa

    def iniciar(self) -> None:
        if self.__estado is not EstadoIntercambio.PENDIENTE:
            raise ValueError("El intercambio ya se inició; no se reenvía sin conciliación.")
        self.__estado = EstadoIntercambio.EN_PROCESO

    def confirmar(self, referencia: str) -> None:
        if self.__estado is not EstadoIntercambio.EN_PROCESO:
            raise ValueError("El intercambio no está en proceso.")
        referencia = _texto(referencia, "referencia externa")
        self.__referencia_externa, self.__fecha_confirmacion = referencia, ahora()
        self.__estado = EstadoIntercambio.CONFIRMADO

    def registrar_fallo(self, detalle: str, indeterminado: bool = False) -> None:
        if self.__estado is not EstadoIntercambio.EN_PROCESO:
            raise ValueError("El intercambio no está en proceso.")
        self.__detalle_resultado = _texto(detalle, "detalle")
        self.__estado = EstadoIntercambio.INDETERMINADO if indeterminado else EstadoIntercambio.FALLIDO


# ABSTRACCIÓN: contrato de operaciones para sus implementaciones.
class ServicioInteroperabilidad(ABC):
    """Contrato del servicio de interoperabilidad entre entidades."""
    __slots__ = ()

    @abstractmethod
    def intercambiar(self, intercambio: IntercambioDocumentario,
                     transporte: Callable | None = None) -> IntercambioDocumentario:
        raise NotImplementedError


# POLIMORFISMO: implementación del contrato de su clase base.
class AdaptadorPIDE(ServicioInteroperabilidad):
    """Conecta el sistema con la Plataforma de Interoperabilidad del Estado."""
    __slots__ = ('__direccion_servicio', '__tiempo_espera_segundos', '__proveedor_credenciales')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __direccion_servicio: str
    __tiempo_espera_segundos: float
    __proveedor_credenciales: ProveedorCredenciales | None

    def __init__(self, *,
                 direccion_servicio: str,
                 tiempo_espera_segundos: float = 30.0,
                 proveedor_credenciales: ProveedorCredenciales | None = None,
                 ) -> None:
        _validar(direccion_servicio, str, "direccion_servicio")
        self.__direccion_servicio = direccion_servicio
        _validar(tiempo_espera_segundos, float, "tiempo_espera_segundos")
        self.__tiempo_espera_segundos = tiempo_espera_segundos
        _validar(proveedor_credenciales, ProveedorCredenciales | None, "proveedor_credenciales")
        self.__proveedor_credenciales = proveedor_credenciales
        _validar_conexion(direccion_servicio, tiempo_espera_segundos)

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'direccion_servicio': self.__direccion_servicio,
            'tiempo_espera_segundos': self.__tiempo_espera_segundos,
            'proveedor_credenciales': self.__proveedor_credenciales,
        }
        return _vista(datos)

    def intercambiar(self, intercambio: IntercambioDocumentario,
                     transporte: Callable | None = None) -> IntercambioDocumentario:
        if transporte is None:
            raise RuntimeError("Falta el contrato y el transporte del servicio de interoperabilidad.")
        credenciales = dict(self.__proveedor_credenciales.obtener()) if self.__proveedor_credenciales else {}
        intercambio.iniciar()
        datos = intercambio.consultar()
        solicitud = {"id_correlacion": datos["id_correlacion"],
                     "direccion": datos["direccion"].value,
                     "expediente": str(datos["documento"].numero_expediente),
                     "entidad_origen": datos["entidad_origen"].codigo,
                     "entidad_destino": datos["entidad_destino"].codigo}
        try:
            respuesta = transporte(self.__direccion_servicio, solicitud,
                                   self.__tiempo_espera_segundos, credenciales)
            if respuesta.get("id_correlacion") != datos["id_correlacion"]:
                raise ValueError("La respuesta corresponde a otra solicitud.")
            if respuesta.get("confirmado") is True:
                intercambio.confirmar(respuesta["referencia"])
            elif respuesta.get("rechazado") is True:
                intercambio.registrar_fallo("El servicio rechazó la operación.")
            else:
                intercambio.registrar_fallo("Respuesta sin confirmación concluyente.", indeterminado=True)
        except Exception as exc:
            if intercambio.estado is EstadoIntercambio.EN_PROCESO:
                intercambio.registrar_fallo(type(exc).__name__, indeterminado=True)
        return intercambio
