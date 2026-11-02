"""Simulación de un tren de evaporación de múltiple efecto con arquitectura EO."""

from typing import Dict, List

from core.schemas.base import Conexion, Equipo, Fase, Sustancias
from core.schemas.engine import (
    Evaporador,
    FuenteMateria,
    IntercambiadorCalor,
    PurgaMateria,
    Valvula,
)
from core.schemas.planta import Planta
from core.schemas.streams import Calor, LineaMateria, LineaVapor

_KELVIN_0C = 273.15
_PRESION_ATMOSFERICA = 101325.0
_ALIMENTACION_KG_H = 5000.0


def construir_planta_mee() -> Planta:
    planta = Planta("Tren de Evaporación MEE - 3 Efectos")
    equipos = _crear_equipos()

    _registrar_equipos(planta, equipos)
    _conectar_efecto_1(planta, equipos)
    _conectar_efecto_2(planta, equipos)
    _conectar_efecto_3(planta, equipos)
    return planta


def _crear_equipos() -> Dict[str, Equipo]:
    return {
        "fuente_jarabe": FuenteMateria(
            nombre="SRC-JARABE",
            flujo_masico=_ALIMENTACION_KG_H,
            temperatura=_KELVIN_0C + 85.0,
            presion=151987.0,
            composicion={"water": 0.95, "glucose": 0.05},
        ),
        "fuente_vapor_caldera": FuenteMateria(
            nombre="SRC-VAPOR-VIVO",
            flujo_masico=1800.0,
            temperatura=None,
            presion=303975.0,
            composicion={"water": 1.0, "glucose": 0.0},
            fase=Fase.VAPOR,
            calidad=1.0,
        ),
        "cond_1": IntercambiadorCalor(nombre="COND-1"),
        "evap_1": Evaporador(
            nombre="EVAP-1",
            masa=500.0,
            presion=151987.0,
            temperatura=None,
            composicion=None,
        ),
        "valv_12": Valvula(nombre="VALV-1->2", presion_salida=_PRESION_ATMOSFERICA),
        "cond_2": IntercambiadorCalor(nombre="COND-2"),
        "evap_2": Evaporador(
            nombre="EVAP-2",
            masa=500.0,
            presion=_PRESION_ATMOSFERICA,
            temperatura=None,
            composicion=None,
        ),
        "valv_23": Valvula(nombre="VALV-2->3", presion_salida=50662.0),
        "cond_3": IntercambiadorCalor(nombre="COND-3"),
        "evap_3": Evaporador(
            nombre="EVAP-3",
            masa=500.0,
            presion=50662.0,
            temperatura=None,
            composicion=None,
        ),
        "sink_cond_1": PurgaMateria(nombre="SINK-COND-1"),
        "sink_cond_2": PurgaMateria(nombre="SINK-COND-2"),
        "sink_cond_3": PurgaMateria(nombre="SINK-COND-3"),
        "sink_vapor_final": PurgaMateria(nombre="SINK-VAPOR-FINAL"),
        "sink_producto": PurgaMateria(nombre="SINK-PRODUCTO-FINAL"),
    }


def _registrar_equipos(planta: Planta, equipos: Dict[str, Equipo]) -> None:
    for equipo in equipos.values():
        planta.añadir_nodo(equipo)


def _conectar(
    planta: Planta, origen: Equipo, destino: Equipo, linea: Conexion
) -> None:
    planta.añadir_conexion(origen.nombre, destino.nombre, linea)


def _conectar_efecto_1(planta: Planta, equipos: Dict[str, Equipo]) -> None:
    _conectar(
        planta,
        equipos["fuente_vapor_caldera"],
        equipos["cond_1"],
        LineaVapor(nombre="S-VaporVivo", temperatura=None, presion=None, flujo_masico=0.0),
    )
    _conectar(
        planta,
        equipos["cond_1"],
        equipos["sink_cond_1"],
        LineaMateria(nombre="S-Condensado-1", temperatura=None, presion=None, flujo_masico=0.0),
    )
    _conectar(
        planta,
        equipos["cond_1"],
        equipos["evap_1"],
        Calor(nombre="Q-1", flujo_calor=0.0),
    )
    _conectar(
        planta,
        equipos["fuente_jarabe"],
        equipos["evap_1"],
        LineaMateria(nombre="S-JarabeIn", temperatura=None, presion=None, flujo_masico=0.0),
    )
    _conectar(
        planta,
        equipos["evap_1"],
        equipos["cond_2"],
        LineaVapor(nombre="S-Vapor-E1", temperatura=None, presion=None, flujo_masico=0.0),
    )
    _conectar(
        planta,
        equipos["evap_1"],
        equipos["valv_12"],
        LineaMateria(nombre="S-Liq-E1", temperatura=None, presion=None, flujo_masico=0.0),
    )


def _conectar_efecto_2(planta: Planta, equipos: Dict[str, Equipo]) -> None:
    _conectar(
        planta,
        equipos["cond_2"],
        equipos["sink_cond_2"],
        LineaMateria(nombre="S-Condensado-2", temperatura=None, presion=None, flujo_masico=0.0),
    )
    _conectar(
        planta,
        equipos["cond_2"],
        equipos["evap_2"],
        Calor(nombre="Q-2", flujo_calor=0.0),
    )
    _conectar(
        planta,
        equipos["valv_12"],
        equipos["evap_2"],
        LineaMateria(
            nombre="S-Liq-E1-Flashed", temperatura=None, presion=None, flujo_masico=0.0
        ),
    )
    _conectar(
        planta,
        equipos["evap_2"],
        equipos["cond_3"],
        LineaVapor(nombre="S-Vapor-E2", temperatura=None, presion=None, flujo_masico=0.0),
    )
    _conectar(
        planta,
        equipos["evap_2"],
        equipos["valv_23"],
        LineaMateria(nombre="S-Liq-E2", temperatura=None, presion=None, flujo_masico=0.0),
    )


def _conectar_efecto_3(planta: Planta, equipos: Dict[str, Equipo]) -> None:
    _conectar(
        planta,
        equipos["cond_3"],
        equipos["sink_cond_3"],
        LineaMateria(nombre="S-Condensado-3", temperatura=None, presion=None, flujo_masico=0.0),
    )
    _conectar(
        planta,
        equipos["cond_3"],
        equipos["evap_3"],
        Calor(nombre="Q-3", flujo_calor=0.0),
    )
    _conectar(
        planta,
        equipos["valv_23"],
        equipos["evap_3"],
        LineaMateria(
            nombre="S-Liq-E2-Flashed", temperatura=None, presion=None, flujo_masico=0.0
        ),
    )
    _conectar(
        planta,
        equipos["evap_3"],
        equipos["sink_vapor_final"],
        LineaVapor(nombre="S-Vapor-Final", temperatura=None, presion=None, flujo_masico=0.0),
    )
    _conectar(
        planta,
        equipos["evap_3"],
        equipos["sink_producto"],
        LineaMateria(
            nombre="S-Producto-Final", temperatura=None, presion=None, flujo_masico=0.0
        ),
    )


def _entradas(planta: Planta, nodo: str) -> List[Conexion]:
    return [
        datos["data"] for _, _, datos in planta.grafo.in_edges(nodo, data=True)
    ]


def _primera_entrada_materia(planta: Planta, nodo: str) -> LineaMateria:
    return next(
        corriente for corriente in _entradas(planta, nodo) if isinstance(corriente, LineaMateria)
    )


def _primera_entrada_vapor(planta: Planta, nodo: str) -> LineaVapor:
    return next(
        corriente for corriente in _entradas(planta, nodo) if isinstance(corriente, LineaVapor)
    )


def _vapor_evaporado_total(planta: Planta) -> float:
    nodos_con_vapor = ("COND-2", "COND-3", "SINK-VAPOR-FINAL")
    return sum(
        _primera_entrada_vapor(planta, nodo).flujo_masico for nodo in nodos_con_vapor
    )


def _imprimir_perfil_termico(efectos: List[Evaporador]) -> None:
    print("\n[PERFIL DE TEMPERATURAS Y BPE]")
    for numero, efecto in enumerate(efectos, start=1):
        presion_atm = efecto.presion / _PRESION_ATMOSFERICA
        temperatura_c = efecto.temperatura - _KELVIN_0C
        fraccion_glucosa = efecto.composicion[Sustancias.GLUCOSE.value]
        print(
            f" Efecto {numero} | Presión: {presion_atm:.2f} atm | "
            f"Temp Ebullición: {temperatura_c:.2f} °C | x_glucosa: {fraccion_glucosa:.4f}"
        )


def _imprimir_rendimiento(
    vapor_vivo: FuenteMateria, vapor_evaporado: float, producto: LineaMateria
) -> None:
    economia = vapor_evaporado / vapor_vivo.flujo_masico
    print("\n[RENDIMIENTO GLOBAL]")
    print(f" Alimentación Inicial  : {_ALIMENTACION_KG_H:.2f} kg/h")
    print(f" Vapor Vivo Consumido  : {vapor_vivo.flujo_masico:.2f} kg/h")
    print(f" Agua Evaporada Total  : {vapor_evaporado:.2f} kg/h")
    print(f" Jarabe Concentrado    : {producto.flujo_masico:.2f} kg/h")
    print(f" Economía de Vapor     : {economia:.2f} kg agua evaporada / kg vapor vivo")


def generar_reporte(planta: Planta) -> None:
    efectos = [
        planta.grafo.nodes[nombre]["data"]
        for nombre in ("EVAP-1", "EVAP-2", "EVAP-3")
    ]
    vapor_vivo = planta.grafo.nodes["SRC-VAPOR-VIVO"]["data"]
    producto = _primera_entrada_materia(planta, "SINK-PRODUCTO-FINAL")
    vapor_evaporado = _vapor_evaporado_total(planta)

    print("\n" + "=" * 50)
    print(" REPORTE TÉCNICO: TREN MEE (3 EFECTOS)")
    print("=" * 50)
    _imprimir_perfil_termico(efectos)
    _imprimir_rendimiento(vapor_vivo, vapor_evaporado, producto)
    print("=" * 50 + "\n")


if __name__ == "__main__":
    planta_mee = construir_planta_mee()
    planta_mee.resolver_planta()
    generar_reporte(planta_mee)