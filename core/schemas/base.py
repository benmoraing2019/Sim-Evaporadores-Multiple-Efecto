"""
Estructura base para la interconexión de clases
"""

from __future__ import annotations
from abc import ABC, abstractmethod

from dataclasses import dataclass, field, asdict
from typing import Dict, List, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from core.services.thermo_service import PropSimService
    from core.services.ecuaciones_manager import GestorSistemaEO


class TipoConexion(Enum):
    """
    Estructura enum para explicar el tipo de flujo
    """

    MATERIA = "MATERIA"
    ENERGIA = "ENERGIA"
    VAPOR = "VAPOR"

class Sustancias(Enum):
    """
    Contiene los nombres de las sustancias participantes en los cálculos de la simulación
    """
    WATER = "water"
    GLUCOSE = "glucose"

    @classmethod
    def obtener_nombres(cls) -> List[str]:
        """
        Entrega la lista de los nombres (valores) de las sustancias participantes.
        Retorna: ['water', 'glucose']
        """
        return [sustancia.value for sustancia in cls]

@dataclass
class Conexion:
    """
    Estructrua que encapsula las propiedades generales de una conexión (correinte)
    """
    nombre:str
    tipo_conexion:TipoConexion = None

class Fase(Enum):
    """
    Estructura que indica 
    """
    LIQUIDO = "LIQUIDO"
    VAPOR = "VAPOR"
    ELV = "ELV"

@dataclass(kw_only=True)
class PropiedadesQuimicas:
    """
    Gestiona las propiedades químicas de varias sustancias
    """

    temperatura:float
    presion:float
    composicion:Dict[str, float] | None = field(default= None)
    fase:Fase | None = field(default=None)
    calidad:float | None = field(default = None)
    entalpia:float | None = field(default= None)

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
class Equipo(ABC):
    """
    Estructura base de un equipo cualquiera
    """
    nombre:str

    @abstractmethod
    def modelar_sistema(
        self,
        gestor:GestorSistemaEO,
        inlets: List[Conexion],
        outlets:List[Conexion],
        thermo:PropSimService
    )->None:
        """
        [MÉTODO OBLIGATORIO]
        Aquí el equipo debe traducir su física al sistema numérico.
        
        Pasos a seguir al heredar:
        1. Identificar corrientes (inlets/outlets).
        2. Inscribir variables en el gestor: var = gestor.registrar_variable(...)
        3. Definir funciones anidadas (closures) para los residuos (masa, energía, etc.).
        4. Inscribir los residuos: gestor.registrar_residuo(funcion)
        """
        pass

    @abstractmethod
    def aplicar_resultados_finales(
        self,
        inlets:List[Conexion],
        outlets:List[Conexion],
        thermo: PropSimService
    )->None:
        """
        [MÉTODO OBLIGATORIO]
        Se ejecuta después de que el Solver converge exitosamente.
        Sirve para tomar los valores finales de las variables (var.valor)
        y fijarlos definitivamente en los dataclasses de las corrientes
        y atributos internos del equipo.
        """
        pass