"""Orquestación del grafo de equipos y resolución simultánea del sistema."""

from typing import List, Tuple

import networkx as nx
from scipy.optimize import least_squares

from core.schemas.base import Conexion, Equipo, Fase
from core.schemas.engine import Evaporador
from core.schemas.streams import LineaMateria
from core.services.ecuaciones_manager import GestorSistemaEO
from core.services.thermo_service import PropSimService

_KELVIN_0C = 273.15
_CLAVES_FRACCION = ("xg", "x_glucose")
_CLAVES_TEMPERATURA = ("t_out", "temperatura")
_LIMITE_FRACCION = (0.0, 0.999)
_LIMITE_TEMPERATURA = (_KELVIN_0C + 10.0, _KELVIN_0C + 300.0)
_LIMITE_FLUJO = (0.0, float("inf"))


def _limites_de_variable(nombre: str) -> Tuple[float, float]:
    """Asigna un rango físico a cada incógnita según su nombre."""
    nombre = nombre.lower()
    if any(clave in nombre for clave in _CLAVES_FRACCION):
        return _LIMITE_FRACCION
    if any(clave in nombre for clave in _CLAVES_TEMPERATURA):
        return _LIMITE_TEMPERATURA
    return _LIMITE_FLUJO


class Planta:
    """Grafo de equipos que se resuelve como un único sistema de ecuaciones."""

    def __init__(self, nombre_planta: str) -> None:
        self.nombre = nombre_planta
        self.grafo = nx.DiGraph()

    def añadir_nodo(self, nodo: Equipo) -> None:
        self.grafo.add_node(nodo.nombre, data=nodo)

    def añadir_conexion(self, nodo_out: str, nodo_in: str, linea: Conexion) -> None:
        self.grafo.add_edge(nodo_out, nodo_in, data=linea)

    def resolver_planta(self) -> None:
        print(f"\n--- Iniciando Resolución de Planta: {self.nombre} ---")
        gestor = GestorSistemaEO()
        termo = PropSimService()
        orden = self._orden_de_resolucion()

        self._inscribir_equipos(gestor, termo, orden)
        print(
            "Topología procesada. "
            f"Sistema EO: {len(gestor.variables)} variables "
            f"y {len(gestor.funciones_residuo)} ecuaciones."
        )
        self._validar_sistema_cuadrado(gestor)

        solucion = self._resolver_sistema(gestor)
        self._aplicar_resultados(gestor, termo, orden, solucion)

    def _orden_de_resolucion(self) -> List[str]:
        try:
            return list(nx.topological_sort(self.grafo))
        except nx.NetworkXUnfeasible:
            print("Advertencia: se detectó un reciclo; se usará el orden de inserción.")
            return list(self.grafo.nodes)

    def _equipo(self, nombre: str) -> Equipo:
        return self.grafo.nodes[nombre]["data"]

    def _corrientes(self, nombre: str) -> Tuple[List[Conexion], List[Conexion]]:
        entradas = [
            datos["data"] for _, _, datos in self.grafo.in_edges(nombre, data=True)
        ]
        salidas = [
            datos["data"] for _, _, datos in self.grafo.out_edges(nombre, data=True)
        ]
        return entradas, salidas

    def _inscribir_equipos(
        self, gestor: GestorSistemaEO, termo: PropSimService, orden: List[str]
    ) -> None:
        for nombre in orden:
            entradas, salidas = self._corrientes(nombre)
            self._equipo(nombre).modelar_sistema(gestor, entradas, salidas, termo)

    @staticmethod
    def _validar_sistema_cuadrado(gestor: GestorSistemaEO) -> None:
        incognitas = len(gestor.variables)
        ecuaciones = len(gestor.funciones_residuo)
        if incognitas != ecuaciones:
            raise ValueError(
                f"Sistema no cuadrado: {incognitas} incógnitas y {ecuaciones} ecuaciones."
            )

    def _limites_fisicos(
        self, gestor: GestorSistemaEO
    ) -> Tuple[List[float], List[float]]:
        inferiores: List[float] = []
        superiores: List[float] = []
        for variable in gestor.variables:
            inferior, superior = _limites_de_variable(variable.nombre)
            inferiores.append(inferior)
            superiores.append(superior)
        return inferiores, superiores

    def _resolver_sistema(self, gestor: GestorSistemaEO):
        print("Ejecutando SciPy Least-Squares con límites físicos...")
        solucion = least_squares(
            fun=gestor.evaluar_sistema,
            x0=gestor.get_array(),
            bounds=self._limites_fisicos(gestor),
            loss="linear",
            x_scale="jac",
            max_nfev=5000,
        )
        if not solucion.success:
            print("Fallo en la convergencia de la planta.")
            print(f"Mensaje del Solver: {solucion.message}")
            print(f"Error residual estancado en: {solucion.cost:.2e}")
            raise RuntimeError(
                "La simulación no convergió. Revisa las condiciones de operación."
            )
        return solucion

    def _aplicar_resultados(
        self,
        gestor: GestorSistemaEO,
        termo: PropSimService,
        orden: List[str],
        solucion,
    ) -> None:
        print(f"Convergencia exitosa. Error residual: {solucion.cost:.2e}")
        gestor.actualizar_array(solucion.x)
        gestor.evaluar_sistema(solucion.x)

        for nombre in orden:
            entradas, salidas = self._corrientes(nombre)
            self._equipo(nombre).aplicar_resultados_finales(entradas, salidas, termo)


if __name__ == "__main__":
    print("Pruebas de interconexiones de nodos de planta")

    evaporador_1 = Evaporador(
        nombre="E-101",
        temperatura=300,
        presion=101325,
        masa=1000,
        composicion={"water": 0.5, "glucose": 0.5},
    )
    evaporador_2 = Evaporador(
        nombre="E-102",
        temperatura=300,
        presion=101325,
        masa=1000,
        composicion={"water": 0.5, "glucose": 0.5},
    )
    linea_1 = LineaMateria(
        nombre="S1",
        temperatura=300,
        presion=101325,
        fase=Fase.LIQUIDO,
        composicion={"water": 0.5, "glucose": 0.5},
        calidad=0,
        flujo_masico=100,
    )

    planta = Planta("Planta Concentradora Biobío")
    planta.añadir_nodo(evaporador_1)
    planta.añadir_nodo(evaporador_2)
    planta.añadir_conexion(evaporador_1.nombre, evaporador_2.nombre, linea=linea_1)