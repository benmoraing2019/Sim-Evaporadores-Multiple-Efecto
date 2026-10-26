"""
Clases que modelan y estructuran los datos internos del modelo
"""

from __future__ import annotations
from dataclasses import dataclass, field
from core.schemas.base import Direccion, Equipo, Puerto, TipoFlujo

def _p(
        nombre:str,
        d:Direccion,
        t:TipoFlujo = TipoFlujo.MATERIA
)->Puerto:

    return Puerto(
        nombre=nombre,
        direccion=d, 
        tipo= t
    )

@dataclass(kw_only=True)
class IntercambiadorCalor(Equipo):
    """
    Condensador que entrega energía al evaporador para el proceso
    """

    area:float
    coeficiente_global:float

    @property
    def calor_transferido(self)->float | None:
        q = self.puerto("q", TipoFlujo.ENERGIA)
        if q.conexion is None:
            return None

        return q.conexion

    def calcular(self) -> None:
        raise NotImplementedError(f"{type(self).__name__}.calcular() no implementado")

    @staticmethod
    def puertos_estandar()-> list[Puerto]:
        return [
            _p("entrada_caliente", Direccion.ENTRADA),
            _p("condensado", Direccion.SALIDA),
            _p("q", Direccion.SALIDA, TipoFlujo.ENERGIA)
        ]

@dataclass(kw_only=True)
class Evaporador(Equipo):
    """
    Cuerpo de evaporación, recibe la energía Q y separa vapor y licor
    """

    presion_operacion:float
    area: float | None = None

    def calcular(self) -> None:
        raise NotImplementedError(f"{type(self).__name__}.calcular() no implementado")

    @staticmethod
    def puertos_estandar()->list[Puerto]:
        return [
            _p("alimentacion", Direccion.ENTRADA),
            _p("q", Direccion.ENTRADA, TipoFlujo.ENERGIA),
            _p("vapor", Direccion.SALIDA),
            _p("liquido", Direccion.SALIDA)
        ]

@dataclass(kw_only=True)
class CondensadorFinal(Equipo):
    """Condensador total al vacío (último efecto)."""
    area: float
    coeficiente_global: float

    def calcular(self) -> None:
        raise NotImplementedError(f"{type(self).__name__}.calcular() no implementado")

    @staticmethod
    def puertos_estandar() -> list[Puerto]:
        return [
            _p("vapor", Direccion.ENTRADA),
            _p("condensado", Direccion.SALIDA),
            _p("agua_entrada", Direccion.ENTRADA),
            _p("agua_salida", Direccion.SALIDA),
        ]


@dataclass(kw_only=True)
class Fuente(Equipo):
    """
    Frontera de entrada del proceso.

    Aporta una corriente al flowsheet sin resolver ningún balance: es una
    condición de frontera. El estado de la corriente NO se guarda aquí, sino
    en la arista de materia que sale de este nodo (fuente única de verdad).

    Los puertos se generan solos; solo pásalos si necesitas nombres propios.
    """

    puertos: list[Puerto] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.puertos:
            self.puertos = self.puertos_estandar()
        super().__post_init__()

    def calcular(self) -> None:
        """No hay nada que resolver: la corriente llega impuesta."""
        return None

    @staticmethod
    def puertos_estandar() -> list[Puerto]:
        return [_p("salida", Direccion.SALIDA)]


@dataclass(kw_only=True)
class Sumidero(Equipo):
    """
    Frontera de salida del proceso.

    Recibe corrientes que abandonan el flowsheet (producto, condensado,
    purga, vapor al vacío). No resuelve balances; solo cierra el grafo para
    que la red quede débilmente conexa y `RedProceso.validar()` pase.

    Los puertos se generan solos; solo pásalos si necesitas nombres propios.
    """

    puertos: list[Puerto] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.puertos:
            self.puertos = self.puertos_estandar()
        super().__post_init__()

    def calcular(self) -> None:
        """No hay nada que resolver: la corriente abandona el sistema."""
        return None

    @staticmethod
    def puertos_estandar() -> list[Puerto]:
        return [_p("entrada", Direccion.ENTRADA)]


@dataclass(kw_only=True)
class Divisor(Equipo):
    """Nodo auxiliar: reparte una corriente en N."""
    n_salidas: int = 2
    puertos: list[Puerto] = field(default_factory=list)

    def calcular(self) -> None:
        raise NotImplementedError(f"{type(self).__name__}.calcular() no implementado")

    def __post_init__(self) -> None:
        if not self.puertos:
            self.puertos = self.puertos_estandar(self.n_salidas)
        super().__post_init__()

    @staticmethod
    def puertos_estandar(n_salidas: int = 2) -> list[Puerto]:
        return (
            [_p("entrada", Direccion.ENTRADA)]
            + [_p(f"salida_{i}", Direccion.SALIDA) for i in range(n_salidas)]
        )

if __name__ == "__main__":
    ic = IntercambiadorCalor(
        nombre="IC-101",
        puertos=IntercambiadorCalor.puertos_estandar(),
        area=20,
        coeficiente_global=0.1
    )

    print(ic.calor_transferido)
