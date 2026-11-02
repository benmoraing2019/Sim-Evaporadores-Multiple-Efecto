"""Corrientes de materia, vapor y calor que conectan los nodos de la planta."""

from dataclasses import dataclass
from typing import ClassVar

from core.schemas.base import Conexion, Equipo, PropiedadesQuimicas, TipoConexion


@dataclass
class LineaMateria(Conexion, PropiedadesQuimicas):
    """Corriente de materia con propiedades termodinámicas."""

    tipo_conexion: ClassVar[TipoConexion] = TipoConexion.MATERIA

    flujo_masico: float


@dataclass
class LineaVapor(LineaMateria):
    """Corriente de vapor de servicio."""

    tipo_conexion: ClassVar[TipoConexion] = TipoConexion.VAPOR


@dataclass
class Calor(Conexion):
    """Transferencia de energía térmica entre dos equipos."""

    flujo_calor: float
    tipo_conexion: ClassVar[TipoConexion] = TipoConexion.ENERGIA


@dataclass
class Caldera(Equipo):
    """Nodo proveedor de vapor de servicio."""

    temperatura: float | None = None
    presion: float | None = None


@dataclass
class ServicioPurga(Equipo):
    """Nodo sumidero que retira materia del grafo."""


@dataclass
class ServicioFuente(Equipo):
    """Nodo que entrega una corriente de materia al grafo."""

    corriente_fuente: LineaMateria


