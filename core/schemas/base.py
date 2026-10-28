"""
Estructura base para la interconexión de clases
"""

from dataclasses import dataclass, field
from typing import List
from enum import Enum

@dataclass
class Equipo:
    """
    Estructura base de un equipo cualquiera
    """
    nombre:str

class TipoConexion(Enum):
    """
    Estructura enum para explicar el tipo de flujo
    """

    MATERIA = "MATERIA"
    ENERGIA = "ENERGIA"

@dataclass
class Conexion:
    """
    Estructrua que encapsula las propiedades generales de una conexión (correinte)
    """
    nombre:str
    tipo_conexion:TipoConexion

class Fase(Enum):
    """
    Estructura que indica 
    """
    LIQUIDO = "LIQUIDO"
    VAPOR = "VAPOR"
    ELV = "ELV"

