from dataclasses import dataclass, field
from enum import Enum, IntEnum
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
import networkx as nx
import numpy as np


Array = np.ndarray


class Direccion(IntEnum):
    ENTRADA = 1
    SALIDA = -1

class TipoFlujo(str, Enum):
    MATERIA = "materia"
    ENERGIA = "energia"

class Fase(str, Enum):
    """
    Sistema que maneja la información del estado de fase que posee una mezcla
    """

    LIQUIDO:str = "LIQUIDO"
    VAPOR:str = "VAPOR"
    BIFASICO:str = "BIFASICO"

@dataclass(frozen=True, slots=True)
class Composicion:
    """
    Fracciones molares por componente. Inmutable
    """
    fracciones: dict[str, float]
    metodo:str = "UNIFAC"

    def __post_init__(self)->None:

        if not self.fracciones:
            raise ValueError("Composicion no puede estar vacía")

        if any(x<0.0 for x in self.fracciones.values()):
            raise ValueError("Las fracciones molares no pueden ser negativas")

        suma = sum(self.fracciones.values())
        if not np.isclose(suma, 1.0, rtol=1e-6, atol=1e-9):
            raise ValueError(
                f"Las fracciones molares deben sumar 1.0 (suma={suma:.6f})"
            )

    def componentes(self) -> list[str]:
        return list(self.fracciones)

    def valores(self)->list[float]:
        return list(self.fracciones.values())

@dataclass(slots=True)
class Puerto:
    """
    Puerto de conexión de un equipo
    """

    nombre:str
    direccion:Direccion
    tipo:TipoFlujo = TipoFlujo.MATERIA

    conexion:tuple[str, str] | None = field(default=None, init=False, repr=False)
    _padre: str | None = field(default=None, init=False, repr=False)

    @property
    def codigo(self)->str:
        """
        Identificador del puerto
        """

        if self._padre is None:
            raise RuntimeError(f"El puerto '{self.nombre}' no pertenece a ningún equipo ")
        return f"{self._padre}.{self.nombre}"

    @property
    def conectado(self)->bool:
        return self.conexion is not None

@dataclass(kw_only=True)
class Equipo(ABC):
    """Contrato común: nombre, puertos y capacidad de calcular."""
    nombre: str
    puertos: list[Puerto]

    def __post_init__(self) -> None:
        vistos: set[tuple[str, TipoFlujo]] = set()
        for p in self.puertos:
            if p._padre is not None:
                raise ValueError(
                    f"El puerto '{p.nombre}' ya pertenece al equipo '{p._padre}'"
                )
            clave = (p.nombre, p.tipo)
            if clave in vistos:
                raise ValueError(f"Puerto duplicado '{p.nombre}' ({p.tipo}) en '{self.nombre}'")
            vistos.add(clave)
            p._padre = self.nombre

    # --- consultas de puertos ------------------------------------------
    def puerto(self, nombre: str, tipo: TipoFlujo | None = None) -> Puerto:
        if tipo is not None:
            for p in self.puertos:
                if p.nombre == nombre and p.tipo is tipo:
                    return p
        else:
            for p in self.puertos:
                if p.nombre == nombre:
                    return p
        raise KeyError(f"'{self.nombre}' no tiene un puerto '{nombre}' ({tipo})")

    def puertos_de(self, tipo: TipoFlujo) -> list[Puerto]:
        return [p for p in self.puertos if p.tipo is tipo]

    # --- contrato de cálculo -------------------------------------------
    @abstractmethod
    def calcular(self) -> None:
        """Resuelve el estado de salida del equipo a partir de sus entradas."""
        ...

if __name__ == "__main__":
    port_1 = Puerto(
        nombre="IN-01",
        direccion=Direccion.ENTRADA
    )

    port_2 = Puerto(
        nombre="OUT-01",
        direccion=Direccion.SALIDA
    )

    @dataclass(kw_only=True)
    class EquipoDemo(Equipo):
        def calcular(self) -> None:
            return None

    eqp = EquipoDemo(
        nombre="E-101",
        puertos=[
            port_1,
            port_2
        ]
    )

    print(eqp.puertos[0].codigo)