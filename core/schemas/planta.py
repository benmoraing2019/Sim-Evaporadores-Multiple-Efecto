"""
Sistema que gestiona la planta y las interconexiones con el grafo
"""
from core.schemas.base import Equipo, Fase, Conexion, TipoConexion
from core.schemas.engine import Evaporador, IntercambiadorCalor
from core.schemas.streams import LineaCalor, LineaMateria, ServicioFuente, ServicioPurga, ServicioVapor

import networkx as nx

class Planta:
    """
    Clase que gestiona las interacciones y conexiones de la planta a través de la estrutura
    de grafos (nodo y aristas) dirigidos
    """

    def __init__(self, nombre_planta:str):
        self.nombre = nombre_planta
        self.grafo = nx.DiGraph()


    def añadir_nodo(self, nodo:Equipo):
        """
        Añade un equipo com:o nodo al grafo
        """

        self.grafo.add_node(nodo.nombre, data = nodo)

    def añadir_conexion(self, nodo_out:str, nodo_in:str, linea:Conexion):
        """
        Añade conexión arista entre nodo, manteniendo paralabra clave para almacenar
        la información del dataclass que define la linea
        """

        self.grafo.add_edge(nodo_out, nodo_in, data = linea)

if __name__ == "__main__":
    print("Pruebas interconexiones de nodos de planta")
    evp_1 = Evaporador(
        nombre="E-101",
        temperatura=300,
        presion=101325,
        masa=1000,
        composicion={
            "water":0.5,
            "glucosa":0.5
        }
    )

    evp_2 = Evaporador(
        nombre="E-101",
        temperatura=300,
        presion=101325,
        masa=1000,
        composicion={
            "water":0.5,
            "glucosa":0.5
        }
    )

    s1 = LineaMateria(
        nombre="S1",
        temperatura= 300,
        presion=101325,
        fase=Fase.LIQUIDO,
        composicion={
            "water":0.5,
            "glucosa":0.5
        },
        calidad=0,
        flujo_masico=100
    )

    planta = Planta("Prueba 1")

    planta.añadir_nodo(evp_1)
    planta.añadir_nodo(evp_2)

    planta.añadir_conexion(evp_1.nombre, evp_2.nombre, linea=s1)
