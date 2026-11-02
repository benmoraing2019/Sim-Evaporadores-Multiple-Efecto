"""Variables y residuos que conectan el grafo de equipos con el solver numérico."""

from dataclasses import dataclass
from typing import Callable, List

import numpy as np


@dataclass
class VariableSolver:
    """Incógnita compartida entre el gestor y el equipo que la registró."""

    nombre: str
    valor: float


class GestorSistemaEO:
    """Registra las incógnitas y las ecuaciones de balance del sistema."""

    def __init__(self) -> None:
        self.variables: List[VariableSolver] = []
        self.funciones_residuo: List[Callable[[], float]] = []

    def registrar_variable(self, nombre: str, valor: float) -> VariableSolver:
        """Registra una incógnita y devuelve la referencia compartida con el equipo."""
        variable = VariableSolver(nombre=nombre, valor=valor)
        self.variables.append(variable)
        return variable

    def registrar_residuo(self, funcion_residuo: Callable[[], float]) -> None:
        """Registra una ecuación de balance que el solver debe anular."""
        self.funciones_residuo.append(funcion_residuo)

    def get_array(self) -> np.ndarray:
        """Valores actuales de las incógnitas como vector numérico."""
        return np.array([variable.valor for variable in self.variables], dtype=float)

    def actualizar_array(self, valores: np.ndarray) -> None:
        """Actualiza las incógnitas con el vector entregado por el solver."""
        if len(valores) != len(self.variables):
            raise ValueError(
                f"El solver entregó {len(valores)} valores para {len(self.variables)} variables."
            )

        for variable, nuevo_valor in zip(self.variables, valores):
            variable.valor = float(nuevo_valor)

    def evaluar_sistema(self, valores: np.ndarray) -> np.ndarray:
        """Evalúa todos los residuos para un vector de incógnitas."""
        self.actualizar_array(valores)
        return np.array(
            [funcion_residuo() for funcion_residuo in self.funciones_residuo],
            dtype=float,
        )


