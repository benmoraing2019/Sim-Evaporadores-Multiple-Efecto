"""
Estructura de los equipos y sus interconecciones
"""
from core.schemas.base import Equipo, PropiedadesQuimicas

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
class Evaporador(Equipo, PropiedadesQuimicas):
    """
    Clase que gestiona los datos del evaporador
    """

    # Propiedades internas del sistema
    masa:float
    @property
    def propiedades_quimicas(self)->PropiedadesQuimicas:
        """
        Entrega la clase de propiedades quimcias ordenadas
        """

        return PropiedadesQuimicas(
            temperatura=self.temperatura,
            presion = self.presion,
            composicion= self.composicion,
            fase=self.fase,
            calidad=self.calidad,
            entalpia=self.entalpia
        )

@dataclass
class Valvula(Equipo):
    """
    Clase que gestiona las propiedades de la valvula
    """

    coeficiente_friccion:float
    diametro_boquilla:float



