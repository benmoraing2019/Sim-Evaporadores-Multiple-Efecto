"""Prueba de integración de una planta de evaporación de un solo efecto."""

from typing import Tuple

from core.schemas.base import Conexion, Equipo, Fase, Sustancias
from core.schemas.engine import (
    Evaporador,
    FuenteMateria,
    IntercambiadorCalor,
    PurgaMateria,
)
from core.schemas.planta import Planta
from core.schemas.streams import Calor, LineaMateria, LineaVapor

_KELVIN_0C = 273.15
_PRESION_ATMOSFERICA = 101325.0


def _conectar(
    planta: Planta, origen: Equipo, destino: Equipo, linea: Conexion
) -> None:
    planta.añadir_conexion(origen.nombre, destino.nombre, linea)


def _construir_planta() -> Tuple[Planta, Calor, LineaMateria]:
    planta = Planta("Planta Evaporadora Simple")

    fuente_jarabe = FuenteMateria(
        nombre="SRC-JARABE",
        flujo_masico=1000.0,
        temperatura=_KELVIN_0C + 85.0,
        presion=_PRESION_ATMOSFERICA,
        composicion={"water": 0.95, "glucose": 0.05},
    )
    fuente_vapor_caldera = FuenteMateria(
        nombre="SRC-VAPOR",
        flujo_masico=500.0,
        temperatura=None,
        presion=200000.0,
        composicion={"water": 1.0, "glucose": 0.0},
        fase=Fase.VAPOR,
        calidad=1.0,
    )
    condensador = IntercambiadorCalor(nombre="COND-101")
    evaporador = Evaporador(
        nombre="EVAP-101",
        masa=500.0,
        presion=_PRESION_ATMOSFERICA,
        temperatura=None,
        composicion=None,
    )
    purga_jarabe = PurgaMateria(nombre="SINK-JARABE")
    purga_vapor_evap = PurgaMateria(nombre="SINK-VAPOR-EVAP")
    purga_condensado = PurgaMateria(nombre="SINK-CONDENSADO")

    for equipo in (
        fuente_jarabe,
        fuente_vapor_caldera,
        condensador,
        evaporador,
        purga_jarabe,
        purga_vapor_evap,
        purga_condensado,
    ):
        planta.añadir_nodo(equipo)

    calor = Calor(nombre="Q-Energia", flujo_calor=0.0)
    _conectar(
        planta,
        fuente_vapor_caldera,
        condensador,
        LineaVapor(nombre="S-VaporVivo", temperatura=None, presion=None, flujo_masico=0.0),
    )
    _conectar(
        planta,
        condensador,
        purga_condensado,
        LineaMateria(nombre="S-Condensado", temperatura=None, presion=None, flujo_masico=0.0),
    )
    _conectar(planta, condensador, evaporador, calor)

    _conectar(
        planta,
        fuente_jarabe,
        evaporador,
        LineaMateria(nombre="S-JarabeIn", temperatura=None, presion=None, flujo_masico=0.0),
    )
    jarabe_salida = LineaMateria(
        nombre="S-JarabeOut", temperatura=None, presion=None, flujo_masico=0.0
    )
    _conectar(planta, evaporador, purga_jarabe, jarabe_salida)
    _conectar(
        planta,
        evaporador,
        purga_vapor_evap,
        LineaVapor(nombre="S-VaporOut", temperatura=None, presion=None, flujo_masico=0.0),
    )

    return planta, calor, jarabe_salida


def _imprimir_reporte(calor: Calor, jarabe: LineaMateria) -> None:
    temperatura_c = jarabe.temperatura - _KELVIN_0C
    fraccion_glucosa = jarabe.composicion[Sustancias.GLUCOSE.value]
    print("\n=== REPORTE DE PLANTA ===")
    print(f"Calor transferido por Condensador: {calor.flujo_calor:.2e} J/h")
    print(f"Jarabe concentrado: {jarabe.flujo_masico:.2f} kg/h a {temperatura_c:.2f} °C")
    print(f"Fracción molar final (Glucosa): {fraccion_glucosa:.4f}")


if __name__ == "__main__":
    planta, calor, jarabe_salida = _construir_planta()
    planta.resolver_planta()
    _imprimir_reporte(calor, jarabe_salida)