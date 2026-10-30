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


