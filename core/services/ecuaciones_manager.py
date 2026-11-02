"""
Sistema que gestiona las variables y traducciones desde el grafo a las
matemáticas para que el sistema funciones de manera correcta
"""

from typing import List, Callable
from dataclasses import dataclass, field
import numpy as np

@dataclass
class VariableSolver:
    """
    Envoltorio de las variables a resolver del solver.
    Funciona como un puntero, Si el gestor cambia los valores
    el sistema de equipo muta de manera automática
    """
    nombre:str
    valor:float

class GestorSistemaEO:
    """
    Clase principal que gestiona las variables
    dentro del sistema
    """
    def __init__(self):

        self.variables: List[VariableSolver] = []
        self.funciones_residuo: List[Callable[[], float]] = []

    def registrar_variable(self, nombre:str, valor:float):
        """
        Equipo pide anotar una incógnita, 
        el gestor guarda y devuelve a equipo
        """
        var = VariableSolver(
            nombre=nombre,
            valor=valor
        )
        self.variables.append(var)
        return var

    def registrar_residuo(self, funcion_residuo:Callable[[], float])->None:
        """
        Anota una función que respresenta la fisica de los residuos
        """

        self.funciones_residuo.append(funcion_residuo)

    def get_array(self)->np.ndarray:
        """
        Entrega la función de array de las variables traducidas
        """

        return np.array([var.valor for var in self.variables], dtype=float)

    def actualizar_array(self, X:np.ndarray)->None:
        """
        Actualiza los valores de la estructura matemática de manera automática para
        cerrar el ciclo de procesamietno de Scipy
        """

        if len(X) != len(self.variables):
            raise ValueError(f"Scipy entregó tamaños de valores incorrectos")

        for var, nuevo_valor in zip(self.variables, X):
            var.valor = nuevo_valor

    def evaluar_sistema(self, X:np.ndarray)->np.ndarray:
        """
        Función objetivo que scipy llamará un montón de veces por
        segundo
        """

        self.actualizar_array(X)

        lista_errores = []

        for funcion in self.funciones_residuo:
            error = funcion()
            lista_errores.append(error)

        return np.array(lista_errores, dtype=float)


