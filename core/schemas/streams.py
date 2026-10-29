"""
Sistema que gestiona las interacciones entre los nodos (equipos) del sistemma
"""

from core.schemas.base import Fase, Conexion, TipoConexion, Equipo

from dataclasses import dataclass, field
from typing import List, Dict, ClassVar

@dataclass
class LineaMateria(Conexion):
    """
    Contiene las propiedades quim
    """

    tipo_conexion:ClassVar[TipoConexion] = TipoConexion.MATERIA

    # Propiedades quimicas 
    temperatura:float
    presion:float
    flujo_masico:float
    composicion:Dict[str, float] = field(default_factory= lambda: dict)

    fase:Fase = None
    calidad:float | None = None
    entalpia:float | None = None

@dataclass
class LineaCalor(Conexion):
    """
    Gestiona las interacciones por transferencia de calor entre nodos
    """
    flujo_calor:float
    tipo_conexion:ClassVar[TipoConexion] = TipoConexion.ENERGIA

@dataclass
class LineaVapor(Conexion):
    """
    Línea que transporta vapor
    """

    temperatura:float
    presion:float
    fase:Fase
    tipo_conexion:ClassVar[TipoConexion] = TipoConexion.MATERIA
    entalpia:float | None = None
    calidad:float | None = None


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


