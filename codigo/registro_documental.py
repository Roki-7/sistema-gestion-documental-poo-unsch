"""01 · Registro documental · SGD–UNSCH.

Requerimientos: RF 01, 02, 03, 05, 06.
Conserva las clases y atributos del análisis y de su diagrama.
El programa general es main.py; este módulo se importa desde allí.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from datetime import datetime
from enum import Enum
from pathlib import Path
import re
import secrets
import sqlite3
from typing import TYPE_CHECKING
from usuarios_y_seguridad import Permiso, Usuario, ahora, hora_local, preparar_base, _insertar_sql, _requerir, _texto, _validar, _vista
from flujo_y_seguimiento import AmbitoTramite, EstadoTramite
from busqueda_y_archivo import EstadoDocumento

if TYPE_CHECKING:
    from flujo_y_seguimiento import CambioEstadoTramite, Dependencia, Derivacion, SolicitudVistoBueno
    from busqueda_y_archivo import Archivador, Desarchivamiento, PoliticaConservacion, RegistroArchivamiento, RegistroEliminacion, ResultadoEliminacion


class ModoRegistro(str, Enum):
    MANUAL = 'MANUAL'
    AUTOMATIZADO = 'AUTOMATIZADO'


# Compartida con el grupo 3; se define una sola vez aquí.
# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class Tramite:
    """Expediente que agrupa los documentos de una solicitud y controla su estado (grupos 01 y 03)."""
    __slots__ = ('__numero_expediente', '__fecha_hora_registro', '__fecha_recepcion', '__remitente', '__destinatario', '__asunto', '__estado', '__categoria', '__tipo_documento', '__prioridad', '__documentos', '__ambito', '__es_academico')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __numero_expediente: NumeroExpediente
    __fecha_hora_registro: datetime
    __fecha_recepcion: datetime | None
    __remitente: Usuario
    __destinatario: Dependencia
    __asunto: str
    __estado: EstadoTramite
    __categoria: Categoria
    __tipo_documento: TipoDocumento
    __prioridad: Prioridad
    __documentos: list[Documento]
    __ambito: AmbitoTramite
    __es_academico: bool

    def __init__(self, *,
                 numero_expediente: NumeroExpediente,
                 fecha_hora_registro: datetime | None = None,
                 fecha_recepcion: datetime | None = None,
                 remitente: Usuario,
                 destinatario: Dependencia,
                 asunto: str,
                 estado: EstadoTramite = EstadoTramite.REGISTRADO,
                 categoria: Categoria,
                 tipo_documento: TipoDocumento,
                 prioridad: Prioridad,
                 documentos: list[Documento] | None = None,
                 ambito: AmbitoTramite = AmbitoTramite.INTERNO,
                 es_academico: bool = False,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from flujo_y_seguimiento import Dependencia

        _validar(numero_expediente, NumeroExpediente, "numero_expediente")
        self.__numero_expediente = numero_expediente
        if fecha_hora_registro is None:
            fecha_hora_registro = ahora()
        _validar(fecha_hora_registro, datetime, "fecha_hora_registro")
        self.__fecha_hora_registro = fecha_hora_registro
        _validar(fecha_recepcion, datetime | None, "fecha_recepcion")
        self.__fecha_recepcion = fecha_recepcion
        _validar(remitente, Usuario, "remitente")
        self.__remitente = remitente
        _validar(destinatario, Dependencia, "destinatario")
        self.__destinatario = destinatario
        _validar(asunto, str, "asunto")
        self.__asunto = asunto
        _validar(estado, EstadoTramite, "estado")
        self.__estado = estado
        _validar(categoria, Categoria, "categoria")
        self.__categoria = categoria
        _validar(tipo_documento, TipoDocumento, "tipo_documento")
        self.__tipo_documento = tipo_documento
        _validar(prioridad, Prioridad, "prioridad")
        self.__prioridad = prioridad
        if documentos is None:
            documentos = []
        _validar(documentos, list[Documento], "documentos")
        self.__documentos = list(documentos)
        _validar(ambito, AmbitoTramite, "ambito")
        self.__ambito = ambito
        _validar(es_academico, bool, "es_academico")
        self.__es_academico = es_academico
        if self.__fecha_recepcion and self.__fecha_recepcion < self.__fecha_hora_registro:
            raise ValueError("La recepción no puede preceder al registro.")
        if self.__documentos:
            raise ValueError("Cree el trámite sin documentos y agréguelos con agregar_documento().")

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'numero_expediente': self.__numero_expediente,
            'fecha_hora_registro': self.__fecha_hora_registro,
            'fecha_recepcion': self.__fecha_recepcion,
            'remitente': self.__remitente,
            'destinatario': self.__destinatario,
            'asunto': self.__asunto,
            'estado': self.__estado,
            'categoria': self.__categoria,
            'tipo_documento': self.__tipo_documento,
            'prioridad': self.__prioridad,
            'documentos': self.__documentos,
            'ambito': self.__ambito,
            'es_academico': self.__es_academico,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def cantidad_folios(self) -> int:
        return sum(d.consultar()["cantidad_folios"] for d in self.__documentos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def estado(self) -> EstadoTramite:
        return self.__estado

    def agregar_documento(self, documento: Documento, actor: Usuario) -> None:
        _requerir(actor, Permiso.MODIFICAR)
        if self.__estado is EstadoTramite.FINALIZADO:
            raise ValueError("Un trámite finalizado no admite documentos nuevos.")
        if documento.consultar()["tramite"] is not self:
            raise ValueError("El documento pertenece a otro trámite.")
        if documento in self.__documentos:
            raise ValueError("El documento ya está registrado.")
        self.__documentos.append(documento)

    def clasificar(self, categoria: Categoria, tipo_documento: TipoDocumento,
                   prioridad: Prioridad, actor: Usuario) -> None:
        _requerir(actor, Permiso.MODIFICAR)
        if self.__estado is EstadoTramite.FINALIZADO:
            raise ValueError("El trámite ya finalizó.")
        _validar(categoria, Categoria, "categoria")
        _validar(tipo_documento, TipoDocumento, "tipo_documento")
        _validar(prioridad, Prioridad, "prioridad")
        self.__categoria, self.__tipo_documento, self.__prioridad = categoria, tipo_documento, prioridad

    def cambiar_estado(self, nuevo: EstadoTramite, actor: Usuario, id_cambio: int,
                       motivo: str | None = None) -> CambioEstadoTramite:
        # Importación diferida: evita la dependencia circular entre módulos.
        from flujo_y_seguimiento import CambioEstadoTramite

        _requerir(actor, Permiso.MODIFICAR)
        _validar(nuevo, EstadoTramite, "nuevo estado")
        transiciones = {
            EstadoTramite.REGISTRADO: {EstadoTramite.EN_ATENCION},
            EstadoTramite.EN_ATENCION: {EstadoTramite.OBSERVADO, EstadoTramite.PENDIENTE_VISTO_BUENO, EstadoTramite.FINALIZADO},
            EstadoTramite.OBSERVADO: {EstadoTramite.EN_ATENCION},
            EstadoTramite.PENDIENTE_VISTO_BUENO: {EstadoTramite.EN_ATENCION, EstadoTramite.OBSERVADO},
            EstadoTramite.FINALIZADO: set(),
        }
        if nuevo not in transiciones[self.__estado]:
            raise ValueError(f"Transición inválida: {self.__estado.value} → {nuevo.value}.")
        if nuevo is EstadoTramite.PENDIENTE_VISTO_BUENO:
            raise ValueError("Use solicitar_visto_bueno() para registrar al jefe destinatario.")
        if self.__estado is EstadoTramite.PENDIENTE_VISTO_BUENO:
            raise ValueError("El jefe debe resolver la solicitud pendiente.")
        if nuevo is EstadoTramite.OBSERVADO:
            motivo = _texto(motivo, "motivo de observación")
        cambio = CambioEstadoTramite(id_cambio=id_cambio, tramite=self,
            estado_anterior=self.__estado, estado_nuevo=nuevo, actor=actor, motivo=motivo)
        if self.__estado is EstadoTramite.REGISTRADO and nuevo is EstadoTramite.EN_ATENCION:
            if self.__fecha_recepcion is None:
                self.__fecha_recepcion = cambio.consultar()["fecha_hora"]
        self.__estado = nuevo
        return cambio

    def recepcionar(self, actor: Usuario, id_cambio: int) -> CambioEstadoTramite:
        if self.__fecha_recepcion is not None or self.__estado is not EstadoTramite.REGISTRADO:
            raise ValueError("El trámite ya fue recepcionado o no está registrado.")
        return self.cambiar_estado(EstadoTramite.EN_ATENCION, actor, id_cambio)

    def solicitar_visto_bueno(self, dependencia: Dependencia, solicitante: Usuario,
                             id_solicitud: int, id_cambio: int) -> tuple[SolicitudVistoBueno, CambioEstadoTramite]:
        # Importación diferida: evita la dependencia circular entre módulos.
        from flujo_y_seguimiento import CambioEstadoTramite, SolicitudVistoBueno

        _requerir(solicitante, Permiso.MODIFICAR)
        if self.__estado is not EstadoTramite.EN_ATENCION:
            raise ValueError("El trámite debe estar en atención.")
        jefe = dependencia.consultar()["jefe"]
        if jefe is None:
            raise ValueError("La dependencia no tiene jefe designado.")
        solicitud = SolicitudVistoBueno(id_solicitud=id_solicitud, tramite=self,
            dependencia=dependencia, solicitante=solicitante, jefe_destinatario=jefe)
        cambio = CambioEstadoTramite(id_cambio=id_cambio, tramite=self,
            estado_anterior=self.__estado, estado_nuevo=EstadoTramite.PENDIENTE_VISTO_BUENO,
            actor=solicitante, motivo="Solicitud de visto bueno")
        self.__estado = EstadoTramite.PENDIENTE_VISTO_BUENO
        return solicitud, cambio

    def resolver_visto_bueno(self, solicitud: SolicitudVistoBueno, actor: Usuario,
                            aprobado: bool, id_cambio: int, motivo: str) -> CambioEstadoTramite:
        # Importación diferida: evita la dependencia circular entre módulos.
        from flujo_y_seguimiento import CambioEstadoTramite

        _requerir(actor, Permiso.APROBAR)
        _validar(aprobado, bool, "aprobado")
        if solicitud.consultar()["tramite"] is not self or self.__estado is not EstadoTramite.PENDIENTE_VISTO_BUENO:
            raise ValueError("La solicitud no corresponde a este trámite pendiente.")
        nuevo = EstadoTramite.EN_ATENCION if aprobado else EstadoTramite.OBSERVADO
        cambio = CambioEstadoTramite(id_cambio=id_cambio, tramite=self,
            estado_anterior=self.__estado, estado_nuevo=nuevo, actor=actor,
            motivo=_texto(motivo, "motivo"))
        solicitud._resolver(actor, aprobado, motivo)
        self.__estado = nuevo
        return cambio

    def generar_cargo(self, entidad: str, medio_notificacion: str) -> Cargo:
        if self.__ambito is not AmbitoTramite.EXTERNO:
            raise ValueError("El cargo corresponde a trámites externos; para internos use el expediente.")
        return Cargo(nombres_apellidos_solicitante=self.__remitente.nombre_completo,
            numero_expediente=str(self.__numero_expediente), fecha_hora_registro=self.__fecha_hora_registro,
            cantidad_folios=self.cantidad_folios, entidad=entidad,
            oficina_que_recibe=self.__destinatario.consultar()["nombre"],
            asunto=self.__asunto, medio_notificacion=medio_notificacion)

    def hoja_de_ruta(self, derivaciones: tuple[Derivacion, ...]) -> tuple[Mapping[str, object], ...]:
        return tuple(d.consultar() for d in sorted(derivaciones,
            key=lambda d: d.consultar()["fecha_hora"]) if d.consultar()["tramite"] is self)


    def actualizar_destinatario(self, derivacion: Derivacion, actor: Usuario) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from flujo_y_seguimiento import EstadoDerivacion

        _requerir(actor, Permiso.MODIFICAR)
        if derivacion.consultar()["tramite"] is not self or derivacion.estado is not EstadoDerivacion.ACEPTADA:
            raise ValueError("Se requiere una derivación aceptada del mismo trámite.")
        self.__destinatario = derivacion.consultar()["area_destino"]


# Compartida con el grupo 5; se define una sola vez aquí.
# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class Documento:
    """Documento de un trámite, con sus archivos y su situación archivística (grupos 01 y 05)."""
    __slots__ = ('__modo_registro', '__cantidad_folios', '__tramite', '__archivos', '__estado', '__archivador', '__politica_conservacion', '__fecha_inicio_computo')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __modo_registro: ModoRegistro
    __cantidad_folios: int
    __tramite: Tramite
    __archivos: list[ArchivoElectronico]
    __estado: EstadoDocumento
    __archivador: Archivador | None
    __politica_conservacion: PoliticaConservacion | None
    __fecha_inicio_computo: date | None

    def __init__(self, *,
                 modo_registro: ModoRegistro,
                 cantidad_folios: int,
                 tramite: Tramite,
                 archivos: list[ArchivoElectronico] | None = None,
                 estado: EstadoDocumento = EstadoDocumento.ACTIVO,
                 archivador: Archivador | None = None,
                 politica_conservacion: PoliticaConservacion | None = None,
                 fecha_inicio_computo: date | None = None,
                 ) -> None:
        # Importación diferida: evita la dependencia circular entre módulos.
        from busqueda_y_archivo import Archivador, PoliticaConservacion

        _validar(modo_registro, ModoRegistro, "modo_registro")
        self.__modo_registro = modo_registro
        _validar(cantidad_folios, int, "cantidad_folios")
        self.__cantidad_folios = cantidad_folios
        _validar(tramite, Tramite, "tramite")
        self.__tramite = tramite
        if archivos is None:
            archivos = []
        _validar(archivos, list[ArchivoElectronico], "archivos")
        self.__archivos = list(archivos)
        _validar(estado, EstadoDocumento, "estado")
        self.__estado = estado
        _validar(archivador, Archivador | None, "archivador")
        self.__archivador = archivador
        _validar(politica_conservacion, PoliticaConservacion | None, "politica_conservacion")
        self.__politica_conservacion = politica_conservacion
        _validar(fecha_inicio_computo, date | None, "fecha_inicio_computo")
        self.__fecha_inicio_computo = fecha_inicio_computo
        if cantidad_folios <= 0:
            raise ValueError("La cantidad de folios debe ser positiva.")
        estados_en_archivo = {EstadoDocumento.ARCHIVADO, EstadoDocumento.ELIMINACION_PENDIENTE}
        if estado in estados_en_archivo and archivador is None:
            raise ValueError("Un documento archivado o pendiente de eliminación necesita archivador.")
        if estado not in estados_en_archivo and archivador is not None:
            raise ValueError("Un documento activo o eliminado no tiene archivador actual.")

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'modo_registro': self.__modo_registro,
            'cantidad_folios': self.__cantidad_folios,
            'tramite': self.__tramite,
            'archivos': self.__archivos,
            'estado': self.__estado,
            'archivador': self.__archivador,
            'politica_conservacion': self.__politica_conservacion,
            'fecha_inicio_computo': self.__fecha_inicio_computo,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def numero_expediente(self) -> NumeroExpediente:
        return self.__tramite.consultar()["numero_expediente"]

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def estado(self) -> EstadoDocumento:
        return self.__estado

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def archivador(self) -> Archivador | None:
        return self.__archivador

    def adjuntar_archivo(self, archivo: ArchivoElectronico, actor: Usuario) -> None:
        _requerir(actor, Permiso.MODIFICAR)
        if self.__estado is not EstadoDocumento.ACTIVO:
            raise ValueError("Solo se adjuntan archivos a documentos activos.")
        if archivo.fecha_eliminacion is not None:
            raise ValueError("El archivo fue eliminado.")
        if archivo in self.__archivos:
            raise ValueError("El archivo ya está adjunto.")
        self.__archivos.append(archivo)

    def archivar(self, archivador: Archivador, usuario: Usuario, id_registro: int,
                 politica: PoliticaConservacion | None = None,
                 fecha_inicio: date | None = None) -> RegistroArchivamiento:
        # Importación diferida: evita la dependencia circular entre módulos.
        from busqueda_y_archivo import RegistroArchivamiento, PoliticaConservacion

        _requerir(usuario, Permiso.MODIFICAR)
        if self.__estado is not EstadoDocumento.ACTIVO:
            raise ValueError("Solo un documento activo puede archivarse.")
        _validar(fecha_inicio, date | None, "fecha_inicio")
        _validar(politica, PoliticaConservacion | None, "politica")
        if politica is not None and politica is not self.__politica_conservacion and fecha_inicio is None:
            raise ValueError("Indique la fecha del evento que inicia el cómputo del plazo.")
        politica = politica if politica is not None else self.__politica_conservacion
        fecha_inicio = fecha_inicio if fecha_inicio is not None else self.__fecha_inicio_computo
        if politica is not None and fecha_inicio is None:
            raise ValueError("La política necesita una fecha de inicio de cómputo.")
        registro = RegistroArchivamiento(id_archivamiento=id_registro, documento=self,
            archivador=archivador, usuario=usuario, fecha_hora=ahora(), politica_aplicada=politica)
        self.__archivador = archivador
        self.__politica_conservacion = politica
        self.__fecha_inicio_computo = fecha_inicio
        self.__estado = EstadoDocumento.ARCHIVADO
        return registro

    def desarchivar(self, usuario: Usuario, motivo: str, id_registro: int) -> Desarchivamiento:
        # Importación diferida: evita la dependencia circular entre módulos.
        from busqueda_y_archivo import Desarchivamiento

        _requerir(usuario, Permiso.MODIFICAR)
        if self.__estado is not EstadoDocumento.ARCHIVADO or self.__archivador is None:
            raise ValueError("El documento no está archivado.")
        registro = Desarchivamiento(id_desarchivo=id_registro, documento=self,
            archivador_origen=self.__archivador, usuario=usuario, fecha_hora=ahora(),
            motivo=_texto(motivo, "motivo de desarchivamiento"))
        self.__estado, self.__archivador = EstadoDocumento.ACTIVO, None
        return registro

    def solicitar_eliminacion(self, usuario: Usuario, autorizada: bool,
                             fecha: date | None = None) -> None:
        _requerir(usuario, Permiso.APROBAR)
        _validar(autorizada, bool, "autorizada")
        if not autorizada:
            raise PermissionError("Se requiere autorización de eliminación.")
        if self.__estado is not EstadoDocumento.ARCHIVADO:
            raise ValueError("El documento debe estar archivado.")
        if self.__politica_conservacion is None or self.__fecha_inicio_computo is None:
            raise ValueError("Falta la política de conservación o su fecha inicial.")
        if not self.__politica_conservacion.plazo_cumplido(self.__fecha_inicio_computo, fecha or date.today()):
            raise ValueError("El plazo no venció o la conservación es permanente.")
        self.__estado = EstadoDocumento.ELIMINACION_PENDIENTE


    def confirmar_eliminacion(self, actor: Usuario) -> None:
        _requerir(actor, Permiso.APROBAR)
        if self.__estado is not EstadoDocumento.ELIMINACION_PENDIENTE:
            raise ValueError("No hay una eliminación pendiente.")
        # Un documento solo físico se elimina como registro; si tiene archivos,
        # TI debe confirmar antes la eliminación de cada uno en el servidor.
        if any(a.fecha_eliminacion is None for a in self.__archivos):
            raise ValueError("TI debe confirmar la eliminación de todos los archivos.")
        self.__estado, self.__archivador = EstadoDocumento.ELIMINADO, None


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class NumeroExpediente:
    """Objeto valor con el número único AA + seis dígitos del expediente (RF 02)."""
    __slots__ = ('__valor',)
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __valor: str

    def __init__(self, *,
                 valor: str,
                 ) -> None:
        _validar(valor, str, "valor")
        self.__valor = valor
        if not re.fullmatch(r"[0-9]{8}", valor):
            raise ValueError("El expediente debe tener 8 dígitos: AA + seis dígitos.")

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'valor': self.__valor,
        }
        return _vista(datos)

    def __str__(self) -> str:
        return self.__valor

    def __eq__(self, otro: object) -> bool:
        # Objeto valor: dos instancias representan el mismo número si su valor coincide.
        if not isinstance(otro, NumeroExpediente):
            return NotImplemented
        return self.__valor == otro.__valor

    def __hash__(self) -> int:
        return hash(self.__valor)

    @classmethod
    def generar(cls, conexion: sqlite3.Connection, fecha: date | None = None) -> NumeroExpediente:
        """Reserva AA+6 en SQLite y respeta una transacción exterior del llamador."""

        fecha = date.today() if fecha is None else fecha
        _validar(fecha, date, "fecha")
        preparar_base(conexion)
        for _ in range(10000):
            numero = f"{fecha.year % 100:02d}{secrets.randbelow(1_000_000):06d}"
            try:
                _insertar_sql(conexion, "INSERT INTO expedientes(numero) VALUES (?)", (numero,))
            except sqlite3.IntegrityError:
                continue
            return cls(valor=numero)
        raise RuntimeError("No se pudo reservar un número único; vuelva a intentar.")


# Compartida con el grupo 5; se define una sola vez aquí.
# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class ArchivoElectronico:
    """Archivo digital de un documento y su ubicación en el servidor (grupos 01 y 05)."""
    __slots__ = ('__nombre', '__formato', '__ruta_almacenamiento', '__fecha_eliminacion')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __nombre: str
    __formato: str
    __ruta_almacenamiento: str
    __fecha_eliminacion: datetime | None

    def __init__(self, *,
                 nombre: str,
                 formato: str,
                 ruta_almacenamiento: str,
                 fecha_eliminacion: datetime | None = None,
                 ) -> None:
        _validar(nombre, str, "nombre")
        self.__nombre = nombre
        _validar(formato, str, "formato")
        self.__formato = formato
        _validar(ruta_almacenamiento, str, "ruta_almacenamiento")
        self.__ruta_almacenamiento = ruta_almacenamiento
        _validar(fecha_eliminacion, datetime | None, "fecha_eliminacion")
        self.__fecha_eliminacion = fecha_eliminacion
        extension = Path(nombre).suffix.lower().lstrip(".")
        if extension != formato.lower().lstrip("."):
            raise ValueError("El formato debe coincidir con la extensión del archivo.")

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'nombre': self.__nombre,
            'formato': self.__formato,
            'ruta_almacenamiento': self.__ruta_almacenamiento,
            'fecha_eliminacion': self.__fecha_eliminacion,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def fecha_eliminacion(self) -> datetime | None:
        return self.__fecha_eliminacion

    def leer(self, raiz_permitida: Path) -> bytes:
        if self.__fecha_eliminacion is not None:
            raise ValueError("El archivo fue eliminado.")
        raiz = Path(raiz_permitida).resolve()
        ruta = Path(self.__ruta_almacenamiento).resolve()
        if not ruta.is_relative_to(raiz):
            raise ValueError("El archivo está fuera del directorio configurado.")
        return ruta.read_bytes()

    def registrar_eliminacion(self, documento: Documento, ejecutor: Usuario,
                             id_registro: int, motivo: str, resultado: ResultadoEliminacion,
                             detalle: str | None = None) -> RegistroEliminacion:
        """Registra la confirmación de TI. No borra archivos del servidor."""
        # Importación diferida: evita la dependencia circular entre módulos.
        from busqueda_y_archivo import RegistroEliminacion, ResultadoEliminacion

        _requerir(ejecutor, Permiso.APROBAR)
        if documento.estado is not EstadoDocumento.ELIMINACION_PENDIENTE:
            raise ValueError("La eliminación del documento no está autorizada.")
        if self not in documento.consultar()["archivos"]:
            raise ValueError("El archivo no corresponde al documento.")
        if self.__fecha_eliminacion is not None:
            raise ValueError("La eliminación ya fue confirmada.")
        registro = RegistroEliminacion(id_eliminacion=id_registro, archivo=self,
            ejecutor=ejecutor, fecha_hora=ahora(), motivo=_texto(motivo, "motivo"),
            resultado=resultado, detalle_resultado=detalle)
        if resultado is ResultadoEliminacion.CONFIRMADA:
            self.__fecha_eliminacion = registro.consultar()["fecha_hora"]
        return registro


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class Cargo:
    """Constancia de recepción que se entrega al remitente de un trámite externo (RF 03)."""
    __slots__ = ('__nombres_apellidos_solicitante', '__numero_expediente', '__fecha_hora_registro', '__cantidad_folios', '__entidad', '__oficina_que_recibe', '__asunto', '__medio_notificacion')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __nombres_apellidos_solicitante: str
    __numero_expediente: str
    __fecha_hora_registro: datetime
    __cantidad_folios: int
    __entidad: str
    __oficina_que_recibe: str
    __asunto: str
    __medio_notificacion: str

    def __init__(self, *,
                 nombres_apellidos_solicitante: str,
                 numero_expediente: str,
                 fecha_hora_registro: datetime,
                 cantidad_folios: int,
                 entidad: str,
                 oficina_que_recibe: str,
                 asunto: str,
                 medio_notificacion: str,
                 ) -> None:
        _validar(nombres_apellidos_solicitante, str, "nombres_apellidos_solicitante")
        self.__nombres_apellidos_solicitante = nombres_apellidos_solicitante
        _validar(numero_expediente, str, "numero_expediente")
        self.__numero_expediente = numero_expediente
        _validar(fecha_hora_registro, datetime, "fecha_hora_registro")
        self.__fecha_hora_registro = fecha_hora_registro
        _validar(cantidad_folios, int, "cantidad_folios")
        self.__cantidad_folios = cantidad_folios
        _validar(entidad, str, "entidad")
        self.__entidad = entidad
        _validar(oficina_que_recibe, str, "oficina_que_recibe")
        self.__oficina_que_recibe = oficina_que_recibe
        _validar(asunto, str, "asunto")
        self.__asunto = asunto
        _validar(medio_notificacion, str, "medio_notificacion")
        self.__medio_notificacion = medio_notificacion

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'nombres_apellidos_solicitante': self.__nombres_apellidos_solicitante,
            'numero_expediente': self.__numero_expediente,
            'fecha_hora_registro': self.__fecha_hora_registro,
            'cantidad_folios': self.__cantidad_folios,
            'entidad': self.__entidad,
            'oficina_que_recibe': self.__oficina_que_recibe,
            'asunto': self.__asunto,
            'medio_notificacion': self.__medio_notificacion,
        }
        return _vista(datos)

    def texto(self) -> str:
        """Contenido del cargo; el diseño institucional se aplicará al conocer su plantilla."""
        def mostrar(valor: object) -> object:
            # El ciudadano recibe la fecha y hora de Perú, no la hora UTC almacenada.
            return hora_local(valor).strftime("%d/%m/%Y %H:%M") if isinstance(valor, datetime) else valor
        return "\n".join(f"{clave.replace('_', ' ').capitalize()}: {mostrar(valor)}"
                         for clave, valor in self.consultar().items())


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class Categoria:
    """Clasificación temática del trámite (RF 05)."""
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


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class TipoDocumento:
    """Tipo documental del trámite, por ejemplo solicitud u oficio (RF 05)."""
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


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class Prioridad:
    """Nivel de prioridad con el que se atiende el trámite (RF 05)."""
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
