"""
main.py
Simulación Completa de un Tren de Evaporación de Múltiple Efecto (3 Efectos)
usando la Arquitectura Orientada a Ecuaciones (EO) con Grafos de NetworkX.
"""
from core.schemas.base import Fase, TipoConexion
from core.schemas.streams import LineaMateria, LineaVapor, Calor
from core.schemas.engine import (
    Evaporador, 
    FuenteMateria, 
    PurgaMateria, 
    IntercambiadorCalor, 
    Valvula
)
from core.schemas.planta import Planta

def construir_planta_mee() -> Planta:
    planta = Planta("Tren de Evaporación MEE - 3 Efectos")

    # =========================================================================
    # 1. DEFINICIÓN DE EQUIPOS (Nodos Operativos)
    # =========================================================================
    # Fuentes
    fuente_jarabe = FuenteMateria(
        nombre="SRC-JARABE", flujo_masico=5000.0, temperatura=273.15 + 85.0, 
        presion=151987.0, composicion={"water": 0.95, "glucose": 0.05}
    )
    fuente_vapor_caldera = FuenteMateria(
        nombre="SRC-VAPOR-VIVO", flujo_masico=1800.0, temperatura=None,
        presion=303975.0, # 3 atm
        composicion={"water": 1.0, "glucose": 0.0}, fase=Fase.VAPOR, calidad=1.0
    )

    # Efecto 1 (Alta Presión: 1.5 atm)
    cond_1 = IntercambiadorCalor(nombre="COND-1")
    evap_1 = Evaporador(nombre="EVAP-1", masa=500.0, presion=151987.0, temperatura=None, composicion=None)
    valv_12 = Valvula(nombre="VALV-1->2", presion_salida=101325.0)

    # Efecto 2 (Presión Atmosférica: 1.0 atm)
    cond_2 = IntercambiadorCalor(nombre="COND-2")
    evap_2 = Evaporador(nombre="EVAP-2", masa=500.0, presion=101325.0, temperatura=None, composicion=None)
    valv_23 = Valvula(nombre="VALV-2->3", presion_salida=50662.0)

    # Efecto 3 (Vacío: 0.5 atm)
    cond_3 = IntercambiadorCalor(nombre="COND-3")
    evap_3 = Evaporador(nombre="EVAP-3", masa=500.0, presion=50662.0, temperatura=None, composicion=None)

    # Purgas (Sumideros)
    sink_cond_1 = PurgaMateria(nombre="SINK-COND-1")
    sink_cond_2 = PurgaMateria(nombre="SINK-COND-2")
    sink_cond_3 = PurgaMateria(nombre="SINK-COND-3")
    sink_vapor_final = PurgaMateria(nombre="SINK-VAPOR-FINAL")
    sink_producto = PurgaMateria(nombre="SINK-PRODUCTO-FINAL")

    # Registrar Nodos
    nodos = [
        fuente_jarabe, fuente_vapor_caldera, 
        cond_1, evap_1, valv_12,
        cond_2, evap_2, valv_23,
        cond_3, evap_3,
        sink_cond_1, sink_cond_2, sink_cond_3, sink_vapor_final, sink_producto
    ]
    for nodo in nodos:
        planta.añadir_nodo(nodo)

    # =========================================================================
    # 2. TOPOLOGÍA Y CONEXIONES (Aristas)
    # =========================================================================
    
    # --- EFECTO 1 ---
    s_vap_vivo = LineaVapor("S-VaporVivo", temperatura=None, presion=None, flujo_masico=0.0)
    s_cond_1 = LineaMateria("S-Condensado-1", temperatura=None, presion=None, flujo_masico=0.0)
    q_1 = Calor("Q-1", flujo_calor=0.0)
    
    planta.añadir_conexion(fuente_vapor_caldera.nombre, cond_1.nombre, s_vap_vivo)
    planta.añadir_conexion(cond_1.nombre, sink_cond_1.nombre, s_cond_1)
    planta.añadir_conexion(cond_1.nombre, evap_1.nombre, q_1)

    s_jarabe_in = LineaMateria("S-JarabeIn", temperatura=None, presion=None, flujo_masico=0.0)
    planta.añadir_conexion(fuente_jarabe.nombre, evap_1.nombre, s_jarabe_in)

    # --- EFECTO 1 AL EFECTO 2 ---
    s_vap_1 = LineaVapor("S-Vapor-E1", temperatura=None, presion=None, flujo_masico=0.0)
    s_liq_1 = LineaMateria("S-Liq-E1", temperatura=None, presion=None, flujo_masico=0.0)
    
    planta.añadir_conexion(evap_1.nombre, cond_2.nombre, s_vap_1) # El vapor de 1 calienta a 2
    planta.añadir_conexion(evap_1.nombre, valv_12.nombre, s_liq_1) # El líquido de 1 pasa por válvula

    # --- EFECTO 2 ---
    s_cond_2 = LineaMateria("S-Condensado-2", temperatura=None, presion=None, flujo_masico=0.0)
    q_2 = Calor("Q-2", flujo_calor=0.0)
    s_liq_1_flash = LineaMateria("S-Liq-E1-Flashed", temperatura=None, presion=None, flujo_masico=0.0)
    
    planta.añadir_conexion(cond_2.nombre, sink_cond_2.nombre, s_cond_2)
    planta.añadir_conexion(cond_2.nombre, evap_2.nombre, q_2)
    planta.añadir_conexion(valv_12.nombre, evap_2.nombre, s_liq_1_flash)

    # --- EFECTO 2 AL EFECTO 3 ---
    s_vap_2 = LineaVapor("S-Vapor-E2", temperatura=None, presion=None, flujo_masico=0.0)
    s_liq_2 = LineaMateria("S-Liq-E2", temperatura=None, presion=None, flujo_masico=0.0)
    
    planta.añadir_conexion(evap_2.nombre, cond_3.nombre, s_vap_2) # El vapor de 2 calienta a 3
    planta.añadir_conexion(evap_2.nombre, valv_23.nombre, s_liq_2) # El líquido de 2 pasa por válvula

    # --- EFECTO 3 ---
    s_cond_3 = LineaMateria("S-Condensado-3", temperatura=None, presion=None, flujo_masico=0.0)
    q_3 = Calor("Q-3", flujo_calor=0.0)
    s_liq_2_flash = LineaMateria("S-Liq-E2-Flashed", temperatura=None, presion=None, flujo_masico=0.0)
    
    s_vap_3 = LineaVapor("S-Vapor-Final", temperatura=None, presion=None, flujo_masico=0.0)
    s_liq_3 = LineaMateria("S-Producto-Final", temperatura=None, presion=None, flujo_masico=0.0)

    planta.añadir_conexion(cond_3.nombre, sink_cond_3.nombre, s_cond_3)
    planta.añadir_conexion(cond_3.nombre, evap_3.nombre, q_3)
    planta.añadir_conexion(valv_23.nombre, evap_3.nombre, s_liq_2_flash)
    
    planta.añadir_conexion(evap_3.nombre, sink_vapor_final.nombre, s_vap_3)
    planta.añadir_conexion(evap_3.nombre, sink_producto.nombre, s_liq_3)

    return planta

def generar_reporte(planta: Planta):
    """Extrae la data de los nodos post-convergencia para un reporte industrial"""
    e1 = planta.grafo.nodes["EVAP-1"]["data"]
    e2 = planta.grafo.nodes["EVAP-2"]["data"]
    e3 = planta.grafo.nodes["EVAP-3"]["data"]
    
    c1 = planta.grafo.nodes["SRC-VAPOR-VIVO"]["data"]
    prod = next(c['data'] for u,v,c in planta.grafo.in_edges("SINK-PRODUCTO-FINAL", data=True))
    vap_total = sum([
        next(c['data'] for u,v,c in planta.grafo.in_edges("COND-2", data=True) if isinstance(c['data'], LineaVapor)).flujo_masico,
        next(c['data'] for u,v,c in planta.grafo.in_edges("COND-3", data=True) if isinstance(c['data'], LineaVapor)).flujo_masico,
        next(c['data'] for u,v,c in planta.grafo.in_edges("SINK-VAPOR-FINAL", data=True)).flujo_masico
    ])

    print("\n" + "="*50)
    print(" REPORTE TÉCNICO: TREN MEE (3 EFECTOS)")
    print("="*50)
    
    print("\n[PERFIL DE TEMPERATURAS Y BPE]")
    for i, e in enumerate([e1, e2, e3], 1):
        print(f" Efecto {i} | Presión: {e.presion/101325:.2f} atm | Temp Ebullición: {e.temperatura - 273.15:.2f} °C | x_glucosa: {e.composicion['glucose']:.4f}")

    print("\n[RENDIMIENTO GLOBAL]")
    print(f" Alimentación Inicial  : 5000.00 kg/h")
    print(f" Vapor Vivo Consumido  : {c1.flujo_masico:.2f} kg/h")
    print(f" Agua Evaporada Total  : {vap_total:.2f} kg/h")
    print(f" Jarabe Concentrado    : {prod.flujo_masico:.2f} kg/h")
    print(f" Economía de Vapor     : {vap_total / c1.flujo_masico:.2f} kg agua evaporada / kg vapor vivo")
    print("="*50 + "\n")

if __name__ == "__main__":
    # 1. Construir
    planta_mee = construir_planta_mee()
    
    # 2. Resolver (SciPy hará el balance simultáneo de la matriz gigante)
    planta_mee.resolver_planta()
    
    # 3. Reportar
    generar_reporte(planta_mee)