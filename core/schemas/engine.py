"""
Estructura de los equipos y sus interconecciones
"""
from core.schemas.base import Equipo

from dataclasses import dataclass, field
from typing import Dict

@dataclass
class IntercambiadorCalor(Equipo):
    """
    Clase que gestiona el comportamienton del intercambiador de calor (Condensador)
    """
    superficie_transferencia:float
    coeficiente_transferencia:float

@dataclass
class Evaporador(Equipo):
    """
    Clase que gestiona los datos del evaporador
    """

    # Propiedades internas del sistema
    temperatura:float
    presion:float
    masa:float
    composicion:Dict[str, float] = field(default_factory= lambda: dict)

@dataclass
class Valvula(Equipo):
    """
    Clase que gestiona las propiedades de la valvula
    """

    coeficiente_friccion:float
    diametro_boquilla:float



