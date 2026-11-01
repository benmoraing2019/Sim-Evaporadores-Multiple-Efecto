"""
Sistema que gestiona las interacciones entre los nodos (equipos) del sistemma
"""

from core.schemas.base import Fase, Conexion, TipoConexion, Equipo, PropiedadesQuimicas

from dataclasses import dataclass, field
from typing import List, Dict, ClassVar

@dataclass
class LineaMateria(Conexion, PropiedadesQuimicas):
    """
    Contiene las propiedades quim
    """

    tipo_conexion:ClassVar[TipoConexion] = TipoConexion.MATERIA

    # Propiedades quimicas
    flujo_masico:float

@dataclass
class LineaVapor(LineaMateria):
    """
    Sistema que gestiona los flujos de vapor de servicio en la simulación
    """
    tipo_conexion:ClassVar[TipoConexion] = TipoConexion.VAPOR


@dataclass
class Calor(Conexion):
    """
    Gestiona las interacciones por transferencia de calor entre nodos
    """
    flujo_calor:float
    tipo_conexion:ClassVar[TipoConexion] = TipoConexion.ENERGIA


@dataclass
class Caldera(Equipo):
    """
    Nodo de servicio de vapor
    """

    # Condiciones
    temperatura:float | None = None
    presion:float | None = None

@dataclass
class ServicioPurga(Equipo):
    """
    Servicio encargado de la purga de materiales del grafo
    """

@dataclass
class ServicioFuente(Equipo):
    """
    Nodo de fuente de materia
    """
    correinte_fuente:LineaMateria


