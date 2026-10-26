"""
Estructura de las corrientes que simulan el proceso
"""

from __future__ import annotations
from dataclasses import dataclass

from core.schemas.base import Composicion, Fase

@dataclass(slots=True, eq=False)
class Corriente:
    """
    Flujo de material (arista de materia)
    """

    nombre:str
    comp:Composicion

    temperatura:float
    presion:float
    flujo_masico:float

    fase:Fase = Fase.LIQUIDO
    calidad:float | None = None
    entalpia:float| None = None

    def __post_init__(self):
        if self.presion <=0:
            raise ValueError(f"La presión debe ser positiva: {self.presion}")
        if self.flujo_masico < 0:
            raise ValueError(f"El flujo másico no debe ser negativo: {self.flujo_masico}")
        if self.fase is Fase.BIFASICO and self.calidad is None:
            raise ValueError(f"Una corriente bifasica requiere definido el parametro 'calidad': {self.calidad}")

@dataclass(slots=True, eq=False)
class CargaTermica:
    """
    Flujo energético (arista energía). Q en W, None = Incógnita
    """

    nombre:str
    Q:float | None = None