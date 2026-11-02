from scipy.optimize import differential_evolution, root

from core.schemas.base import Equipo, Fase, Conexion, TipoConexion
from core.schemas.engine import Evaporador, IntercambiadorCalor
from core.schemas.streams import LineaMateria
from core.services.ecuaciones_manager import GestorSistemaEO
from core.services.thermo_service import PropSimService
from scipy.optimize import least_squares
import numpy as np
import networkx as nx

class Planta:
    def __init__(self, nombre_planta: str):
        self.nombre = nombre_planta
        self.grafo = nx.DiGraph()

    def añadir_nodo(self, nodo: Equipo):
        self.grafo.add_node(nodo.nombre, data=nodo)

    def añadir_conexion(self, nodo_out: str, nodo_in: str, linea: Conexion):
        self.grafo.add_edge(nodo_out, nodo_in, data=linea)

    # =========================================================================
    # EL ORQUESTADOR: CONECTA EL GRAFO CON EL SOLVER MATEMÁTICO
    # =========================================================================
    def resolver_planta(self) -> None:
        print(f"\n--- Iniciando Resolución de Planta: {self.nombre} ---")
        gestor = GestorSistemaEO()
        termo = PropSimService()

        # 1. ORDEN TOPOLÓGICO
        try:
            orden_nodos = list(nx.topological_sort(self.grafo))
        except nx.NetworkXUnfeasible:
            print("⚠️ Advertencia: Reciclo detectado. Usando orden estándar.")
            orden_nodos = list(self.grafo.nodes)

        # 2. INCRIPCIÓN EO
        for nombre_nodo in orden_nodos:
            equipo: Equipo = self.grafo.nodes[nombre_nodo]['data']
            inlets = [edge_data['data'] for _, _, edge_data in self.grafo.in_edges(nombre_nodo, data=True)]
            outlets = [edge_data['data'] for _, _, edge_data in self.grafo.out_edges(nombre_nodo, data=True)]
            equipo.modelar_sistema(gestor, inlets, outlets, termo)

        print(f"Topología procesada. Sistema EO: {len(gestor.variables)} variables y {len(gestor.funciones_residuo)} ecuaciones.")
        
        if len(gestor.variables) != len(gestor.funciones_residuo):
            raise ValueError(f"Sistema no cuadrado: {len(gestor.variables)} vs {len(gestor.funciones_residuo)}.")
        
        # 3. LÍMITES INTELIGENTES (SMART BOUNDS)
        limites_inferiores = []
        limites_superiores = []
        
        for var in gestor.variables:
            nombre = var.nombre.lower()
            if "xg" in nombre or "x_glucose" in nombre:
                # Fracciones molares estrictamente entre 0 y casi 1
                limites_inferiores.append(0.0)
                limites_superiores.append(0.999)
            elif "t_out" in nombre or "temperatura" in nombre:
                # Temperaturas líquidas/vapor (ej. 10 °C a 300 °C)
                limites_inferiores.append(273.15 + 10.0)
                limites_superiores.append(273.15 + 300.0)
            else:
                # Flujos (F, L, V) y Calor (Q)
                limites_inferiores.append(0.0)
                limites_superiores.append(float('inf'))
                
        bounds_fisicos = (limites_inferiores, limites_superiores)

        print("Ejecutando SciPy Least-Squares con Límites Físicos Inteligentes...")
        
        # 4. RESOLUCIÓN FINA (Newton-Trust Region Reflective)
        solucion = least_squares(
            fun=gestor.evaluar_sistema,
            x0=gestor.get_array(),
            bounds=bounds_fisicos,
            loss='linear',          # Cambiamos a 'linear' para exigir precisión absoluta al final
            x_scale='jac',
            max_nfev=5000
        )

        # 5. EVALUACIÓN Y CIERRE
        # Eliminamos la restricción artificial de cost < 1.0 y confiamos en el ftol de SciPy
        if solucion.success: 
            print(f"✅ ¡Convergencia global exitosa! (Error Residual: {solucion.cost:.2e})")
            
            gestor.actualizar_array(solucion.x)
            gestor.evaluar_sistema(solucion.x)
            
            for nombre_nodo in orden_nodos:
                equipo: Equipo = self.grafo.nodes[nombre_nodo]['data']
                inlets = [edge_data['data'] for _, _, edge_data in self.grafo.in_edges(nombre_nodo, data=True)]
                outlets = [edge_data['data'] for _, _, edge_data in self.grafo.out_edges(nombre_nodo, data=True)]
                equipo.aplicar_resultados_finales(inlets, outlets, termo)
        else:
            print("❌ Fallo en la convergencia de la planta.")
            print(f"Mensaje del Solver: {solucion.message}")
            print(f"Error residual estancado en: {solucion.cost:.2e}")
            raise RuntimeError("La simulación no convergió. Revisa las condiciones de operación.")


if __name__ == "__main__":
    print("Pruebas interconexiones de nodos de planta")
    
    # NOTA: Evita usar el mismo nombre para dos nodos, NetworkX usa el nombre como ID único.
    evp_1 = Evaporador(
        nombre="E-101", temperatura=300, presion=101325, masa=1000,
        composicion={"water": 0.5, "glucose": 0.5}
    )

    evp_2 = Evaporador(
        nombre="E-102", temperatura=300, presion=101325, masa=1000,
        composicion={"water": 0.5, "glucose": 0.5}
    )

    s1 = LineaMateria(
        nombre="S1", temperatura=300, presion=101325, fase=Fase.LIQUIDO,
        composicion={"water": 0.5, "glucose": 0.5}, calidad=0, flujo_masico=100
    )

    planta = Planta("Planta Concentradora Biobío")

    planta.añadir_nodo(evp_1)
    planta.añadir_nodo(evp_2)
    planta.añadir_conexion(evp_1.nombre, evp_2.nombre, linea=s1)
    
    # Si añadieras todas las corrientes de entrada y purga, aquí llamarías:
    # planta.resolver_planta()