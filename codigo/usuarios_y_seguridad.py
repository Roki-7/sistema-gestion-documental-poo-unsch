"""02 · Usuarios y seguridad · SGD–UNSCH.

Requerimientos: RF 10, 11, 12.
Conserva las clases y atributos del análisis y de su diagrama.
El programa general es main.py; este módulo se importa desde allí.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from datetime import timezone
from enum import Enum
from types import MappingProxyType
from types import UnionType
from typing import get_args
from typing import get_origin
import re
import math
import sqlite3
from zoneinfo import ZoneInfo

# Las fechas se guardan en UTC; los usuarios consultan con la hora de Perú.
ZONA_HORARIA_INSTITUCIONAL = "America/Lima"


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def hora_local(instante: datetime) -> datetime:
    """El mismo instante expresado en la zona horaria de la universidad."""
    return instante.astimezone(ZoneInfo(ZONA_HORARIA_INSTITUCIONAL))


def fecha_local(instante: datetime) -> date:
    """Fecha calendario del instante en la zona horaria de la universidad."""
    return hora_local(instante).date()


def _texto(valor: str, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{campo}: escriba un texto no vacío.")
    return valor.strip()


def _correo(valor: str) -> str:
    valor = _texto(valor, "correo")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", valor):
        raise ValueError("Correo electrónico inválido.")
    return valor


def _validar(valor: object, tipo: object, campo: str) -> None:
    """Valida entradas del constructor; bool no cuenta como int."""
    origen, args = get_origin(tipo), get_args(tipo)
    if origen is UnionType:
        for opcion in args:
            try:
                _validar(valor, opcion, campo)
                return
            except (ValueError, TypeError):
                continue
        raise TypeError(f"{campo}: tipo incompatible con {tipo}.")
    if tipo is type(None):
        if valor is not None:
            raise TypeError(f"{campo}: se esperaba None.")
    elif origen in (list, set, frozenset, tuple, dict):
        if not isinstance(valor, origen):
            raise TypeError(f"{campo}: se esperaba {origen.__name__}.")
        if origen is dict:
            for k, v in valor.items():
                _validar(k, args[0], campo)
                _validar(v, args[1], campo)
        else:
            for i, v in enumerate(valor):
                esperado = args[0] if len(args) == 1 or args[-1] is Ellipsis else args[i]
                _validar(v, esperado, campo)
    elif tipo is date:
        if type(valor) is not date:
            raise TypeError(f"{campo}: se esperaba una fecha sin hora.")
    elif tipo in (int, bool):
        if type(valor) is not tipo:
            raise TypeError(f"{campo}: se esperaba {tipo.__name__}.")
    elif tipo is float:
        if type(valor) not in (int, float) or not math.isfinite(valor):
            raise TypeError(f"{campo}: se esperaba un número.")
    elif not isinstance(valor, tipo):
        raise TypeError(f"{campo}: tipo incompatible con {tipo}.")
    if isinstance(valor, datetime) and valor.utcoffset() is None:
        raise ValueError(f"{campo}: use una fecha con zona horaria.")
    if isinstance(valor, str) and not valor.strip():
        raise ValueError(f"{campo}: no puede estar vacío.")
    if isinstance(valor, int) and not isinstance(valor, bool) and valor < 0:
        raise ValueError(f"{campo}: no puede ser negativo.")


def _vista(valor: object) -> object:
    """Devuelve contenedores de lectura; mantiene las asociaciones entre objetos."""
    if isinstance(valor, dict):
        return MappingProxyType({k: _vista(v) for k, v in valor.items()})
    if isinstance(valor, (list, tuple)):
        return tuple(_vista(v) for v in valor)
    if isinstance(valor, (set, frozenset)):
        return frozenset(_vista(v) for v in valor)
    return valor


def _requerir(usuario: Usuario, permiso: Permiso) -> None:
    if not usuario.tiene_permiso(permiso):
        raise PermissionError(f"El usuario no tiene el permiso {permiso.value}.")


def preparar_base(conexion: sqlite3.Connection) -> None:
    """Crea las tablas sin confirmar una transacción que ya esté abierta."""
    conexion.execute("""CREATE TABLE IF NOT EXISTS expedientes (
        numero TEXT PRIMARY KEY CHECK(length(numero) = 8)
    )""")
    conexion.execute("""CREATE TABLE IF NOT EXISTS auditoria (
        id INTEGER PRIMARY KEY, usuario_id INTEGER NOT NULL, accion TEXT NOT NULL,
        fecha_hora TEXT NOT NULL, tipo_registro TEXT NOT NULL,
        registro_afectado TEXT NOT NULL, detalle TEXT
    )""")


def _insertar_sql(conexion: sqlite3.Connection, sentencia: str, datos: tuple) -> None:
    """Aísla esta escritura; conserva la transacción exterior si la hay."""
    conexion.execute("SAVEPOINT sgd_escritura")
    try:
        conexion.execute(sentencia, datos)
    except BaseException:
        conexion.execute("ROLLBACK TO SAVEPOINT sgd_escritura")
        conexion.execute("RELEASE SAVEPOINT sgd_escritura")
        raise
    else:
        conexion.execute("RELEASE SAVEPOINT sgd_escritura")


class TipoUsuario(str, Enum):
    INTERNO = 'INTERNO'
    EXTERNO = 'EXTERNO'


class Permiso(str, Enum):
    VISUALIZAR = 'VISUALIZAR'
    MODIFICAR = 'MODIFICAR'
    APROBAR = 'APROBAR'


class AccionAuditoria(str, Enum):
    ACCESO = 'ACCESO'
    CREACION = 'CREACION'
    MODIFICACION = 'MODIFICACION'
    ELIMINACION = 'ELIMINACION'


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class Usuario:
    """Persona interna o externa que actúa en el sistema según sus roles (RF 10)."""
    __slots__ = ('__id_usuario', '__nombres', '__apellidos', '__correo', '__tipo_usuario', '__roles')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_usuario: int
    __nombres: str
    __apellidos: str
    __correo: str
    __tipo_usuario: TipoUsuario
    __roles: list[Rol]

    def __init__(self, *,
                 id_usuario: int,
                 nombres: str,
                 apellidos: str,
                 correo: str,
                 tipo_usuario: TipoUsuario,
                 roles: list[Rol] | None = None,
                 ) -> None:
        _validar(id_usuario, int, "id_usuario")
        self.__id_usuario = id_usuario
        _validar(nombres, str, "nombres")
        self.__nombres = nombres
        _validar(apellidos, str, "apellidos")
        self.__apellidos = apellidos
        _validar(correo, str, "correo")
        self.__correo = correo
        _validar(tipo_usuario, TipoUsuario, "tipo_usuario")
        self.__tipo_usuario = tipo_usuario
        if roles is None:
            roles = []
        _validar(roles, list[Rol], "roles")
        self.__roles = list(roles)
        self.__correo = _correo(correo)
        if id_usuario <= 0:
            raise ValueError("id_usuario debe ser positivo.")

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_usuario': self.__id_usuario,
            'nombres': self.__nombres,
            'apellidos': self.__apellidos,
            'correo': self.__correo,
            'tipo_usuario': self.__tipo_usuario,
            'roles': self.__roles,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def id_usuario(self) -> int:
        return self.__id_usuario

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def nombre_completo(self) -> str:
        return f"{self.__nombres} {self.__apellidos}"

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def roles(self) -> tuple[Rol, ...]:
        return tuple(self.__roles)

    def tiene_permiso(self, permiso: Permiso) -> bool:
        return any(permiso in rol.permisos for rol in self.__roles)

    def asignar_rol(self, rol: Rol) -> None:
        _validar(rol, Rol, "rol")
        if all(r.codigo != rol.codigo for r in self.__roles):
            self.__roles.append(rol)

    def retirar_rol(self, codigo: str) -> None:
        self.__roles = [r for r in self.__roles if r.codigo != codigo]


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class Rol:
    """Conjunto de permisos que se asigna a los usuarios (RF 11)."""
    __slots__ = ('__codigo', '__nombre', '__permisos')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __codigo: str
    __nombre: str
    __permisos: set[Permiso]

    def __init__(self, *,
                 codigo: str,
                 nombre: str,
                 permisos: set[Permiso],
                 ) -> None:
        _validar(codigo, str, "codigo")
        self.__codigo = codigo
        _validar(nombre, str, "nombre")
        self.__nombre = nombre
        _validar(permisos, set[Permiso], "permisos")
        self.__permisos = set(permisos)

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'codigo': self.__codigo,
            'nombre': self.__nombre,
            'permisos': self.__permisos,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def codigo(self) -> str:
        return self.__codigo

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def nombre(self) -> str:
        return self.__nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        _validar(valor, str, "nombre")
        self.__nombre = valor

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def permisos(self) -> frozenset[Permiso]:
        return frozenset(self.__permisos)

    def agregar_permiso(self, permiso: Permiso) -> None:
        _validar(permiso, Permiso, "permiso")
        self.__permisos.add(permiso)

    def retirar_permiso(self, permiso: Permiso) -> None:
        self.__permisos.discard(permiso)


# ENCAPSULAMIENTO: atributos privados y operaciones con validación.
class RegistroAuditoria:
    """Evento inmutable del log de auditoría: quién hizo qué y sobre qué registro (RF 12)."""
    __slots__ = ('__id_auditoria', '__usuario', '__accion', '__fecha_hora', '__tipo_registro', '__id_registro_afectado', '__detalle')
    # Atributos privados: sus cambios pasan por operaciones con validación.
    __id_auditoria: int
    __usuario: Usuario
    __accion: AccionAuditoria
    __fecha_hora: datetime
    __tipo_registro: str
    __id_registro_afectado: str
    __detalle: str | None

    def __init__(self, *,
                 id_auditoria: int,
                 usuario: Usuario,
                 accion: AccionAuditoria,
                 fecha_hora: datetime | None = None,
                 tipo_registro: str,
                 id_registro_afectado: str,
                 detalle: str | None = None,
                 ) -> None:
        _validar(id_auditoria, int, "id_auditoria")
        self.__id_auditoria = id_auditoria
        _validar(usuario, Usuario, "usuario")
        self.__usuario = usuario
        _validar(accion, AccionAuditoria, "accion")
        self.__accion = accion
        if fecha_hora is None:
            fecha_hora = ahora()
        _validar(fecha_hora, datetime, "fecha_hora")
        self.__fecha_hora = fecha_hora
        _validar(tipo_registro, str, "tipo_registro")
        self.__tipo_registro = tipo_registro
        _validar(id_registro_afectado, str, "id_registro_afectado")
        self.__id_registro_afectado = id_registro_afectado
        _validar(detalle, str | None, "detalle")
        self.__detalle = detalle

    def consultar(self) -> Mapping[str, object]:
        datos = {
            'id_auditoria': self.__id_auditoria,
            'usuario': self.__usuario,
            'accion': self.__accion,
            'fecha_hora': self.__fecha_hora,
            'tipo_registro': self.__tipo_registro,
            'id_registro_afectado': self.__id_registro_afectado,
            'detalle': self.__detalle,
        }
        return _vista(datos)

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def id_auditoria(self) -> int:
        return self.__id_auditoria

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def accion(self) -> AccionAuditoria:
        return self.__accion

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def fecha_hora(self) -> datetime:
        return self.__fecha_hora

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def tipo_registro(self) -> str:
        return self.__tipo_registro

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def id_registro_afectado(self) -> str:
        return self.__id_registro_afectado

    # Propiedad pública: acceso controlado al dato privado.
    @property
    def detalle(self) -> str | None:
        return self.__detalle

    def persistir(self, conexion: sqlite3.Connection) -> None:
        preparar_base(conexion)
        _insertar_sql(conexion, "INSERT INTO auditoria VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.__id_auditoria, self.__usuario.id_usuario, self.__accion.value,
             self.__fecha_hora.isoformat(), self.__tipo_registro,
             self.__id_registro_afectado, self.__detalle))

    @classmethod
    def registrar(cls, conexion: sqlite3.Connection, usuario: Usuario, accion: AccionAuditoria,
                  tipo_registro: str, id_registro_afectado: str,
                  detalle: str | None = None) -> RegistroAuditoria:
        """Crea y guarda un evento; la base asigna el siguiente identificador.

        La capa de aplicación lo invoca después de cada operación confirmada.
        Los eventos guardados no se editan: una rectificación es un evento nuevo.
        """
        preparar_base(conexion)
        for _ in range(3):
            siguiente = conexion.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM auditoria").fetchone()[0]
            evento = cls(id_auditoria=siguiente, usuario=usuario, accion=accion,
                tipo_registro=tipo_registro, id_registro_afectado=id_registro_afectado, detalle=detalle)
            try:
                evento.persistir(conexion)
            except sqlite3.IntegrityError:
                # Otra conexión ocupó el mismo identificador; se vuelve a calcular.
                continue
            return evento
        raise RuntimeError("No se pudo registrar el evento de auditoría; vuelva a intentar.")
