"""
Clases que modelan y estructuran los datos internos del modelo
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
import networkx as nx
import numpy as np


Array = np.ndarray



@dataclass
class Equipo:
    """
    Clase que define las propiedades generales de cualquier equipo
    """
    nombre: str
    nombres_puertos: List[str]
    # Al poner init=False, Python no lo pide en el __init__ y se evitan conflictos de herencia
    puertos: Dict[str, str] = field(init=False, default_factory=dict)

    def __post_init__(self):
        self.puertos = {name_port: f"{self.nombre}.{name_port}" for name_port in self.nombres_puertos}

@dataclass
class Composicion:
    """Gestiona composición y modelo de la sustancia a simular."""
    sustancias: List[str]
    fraccion_masa: List[float]
    metodo: str

    def validar(self):
        """Validación útil para evitar errores numéricos en SciPy."""
        if not np.isclose(sum(self.fraccion_masa), 1.0, atol=1e-3):
            raise ValueError("Las fracciones de masa deben sumar 1.0")

    def __post_init__(self):
        self.validar()

@dataclass
class Corriente:
    """
    Representa el estado termodinámico y de transporte en una conexión.
    Esta clase se almacenará directamente en los atributos de las aristas de NetworkX.
    """
    nombre: str
    composicion: Composicion
    temperatura: float  # K o °C
    presion: float      # Pa o bar
    flujo_masico: float # kg/s

@dataclass
class IntercambiadorCalor(Equipo):
    """Propiedades de transferencia de calor."""
    superficie: float
    constante_transferencia: float  # U global

@dataclass
class Evaporador(Equipo):
    """
    Modelo de equipo unitario (Nodo). 
    Nota que ya no lleva objetos 'Corriente' fijos adentro; 
    las corrientes viven en las aristas del grafo que conectan este nodo.
    """
    # Variables de estado o diseño del equipo
    temperatura: float
    presion: float
    masa_holgura: float  # Holduro de líquido en el evaporador
    composicion: Composicion
    intercambiador: Optional[IntercambiadorCalor] = None

@dataclass
class Valvula(Equipo):
    """Válvula de laminación / caída de presión."""
    coeficiente_descarga: float
    presion_salida: Optional[float] = None

@dataclass
class EspecificacionConexion:
    """
    Empaqueta toda la información necesaria para conectar dos puntos del sistema.
    Evita funciones con mil argumentos individuales.
    """
    id_conexion: str
    equipo_origen: str
    puerto_origen: str
    equipo_destino: str
    puerto_destino: str
    corriente: Corriente

class SistemaEvaporacionGraph:
    def __init__(self, nombre:str):
        self.name = nombre
        self.graph = nx.DiGraph()
        pass

    def agregar_equipo(self, equipo:Equipo):
        """
        Agrega un nodo de un grafo
        """
        self.graph.add_node(
            equipo.nombre,
            objeto=equipo
        )

    def agregar_conexion(self, spec:EspecificacionConexion):
        """
        Genera la conexión de un equipo utilizando la clase "EspecificacionConexion"
        """

        if not self.graph.has_node(spec.equipo_origen) or not self.graph.has_node(spec.equipo_destino):
            raise ValueError(f"No exite el equipo {spec.equipo_origen} o No existe el equipo {spec.equipo_destino}")

        self.graph.add_edge(
            spec.equipo_origen,
            spec.equipo_destino,
            id_conexion = spec.id_conexion,
            corriente = spec.corriente,
            puerto_origen= spec.puerto_origen,
            puerto_destino = spec.puerto_destino
        )

if __name__ == "__main__":
    print("Generando composición")

    comp = Composicion(
        sustancias=["water", "cetona"],
        fraccion_masa=[0.4, 0.6],
        metodo="NRTL" # Corregido de NLTR a NRTL
    )

    print("Generando evaporador 1")

    evp1 = Evaporador(
        nombre="E101",
        nombres_puertos=["up", "down"],
        temperatura=300.0,
        presion=0.5,
        masa_holgura=10.0,
        composicion=comp
    )

    evp2 = Evaporador(
        nombre="E102",
        nombres_puertos=["up", "down"],
        temperatura=300.0,
        presion=0.5,
        masa_holgura=10.0,
        composicion=comp
    )

    fd = Corriente(
        "S1",
        composicion=comp,
        temperatura=320.0,
        presion=0.8,
        flujo_masico=3.0
    )

    system = SistemaEvaporacionGraph("Sistema_evaporacion")
    system.agregar_equipo(evp1)
    system.agregar_equipo(evp2)

    conexion = EspecificacionConexion(
        id_conexion=fd.nombre,
        equipo_origen=evp1.nombre,
        equipo_destino=evp2.nombre,
        puerto_origen=evp1.puertos["up"],
        puerto_destino=evp2.puertos["down"],
        corriente=fd
    )

    system.agregar_conexion(conexion)

    print(evp2.puertos["up"])
    print("¡Sistema y conexión inicializados con éxito!")