"""
Sistema que gestiona las interacciones entre los nodos (equipos) del sistemma
"""

from core.schemas.base import Fase, Conexion, TipoConexion

from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class CorrienteMateria(Conexion):
    """
    Contiene las propiedades quim
    """
    tipo_conexion:TipoConexion = field(default= TipoConexion.MATERIA)

    # Propiedades quimicas 
    temperatura:float
    presion:float
    flujo_masico:float
    composicion:Dict[str, float] = field(default_factory= lambda: dict)
    entalpia:float | None = None

@dataclass
class CorrienteCalor(Conexion):
    """
    Gestiona las interacciones por transferencia de calor entre nodos
    """
    tipo_conexion:TipoConexion = field(default= TipoConexion.ENERGIA)
    flujo_calor:float

