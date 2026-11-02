from core.schemas.base import Fase, TipoConexion
from core.schemas.streams import LineaMateria, LineaVapor, Calor
from core.schemas.engine import Evaporador, FuenteMateria, PurgaMateria, IntercambiadorCalor
from core.schemas.planta import Planta  # Ajusta la ruta a tu clase Planta

if __name__ == "__main__":
    # 1. INSTANCIAR LA PLANTA
    planta = Planta("Planta Evaporadora Simple")

    # 2. DEFINIR LOS EQUIPOS (Nodos)
    fuente_jarabe = FuenteMateria(
        nombre="SRC-JARABE", flujo_masico=1000.0, temperatura=273.15 + 85.0, 
        presion=101325.0, composicion={"water": 0.95, "glucose": 0.05}
    )
    
    fuente_vapor_caldera = FuenteMateria(
        nombre="SRC-VAPOR", flujo_masico=500.0, temperatura=None, # T se calcula por saturación
        presion=200000.0, composicion={"water": 1.0, "glucose": 0.0}, fase=Fase.VAPOR, calidad=1.0
    )

    condensador = IntercambiadorCalor(nombre="COND-101")
    
    evaporador = Evaporador(
        nombre="EVAP-101", masa=500.0, presion=101325.0, 
        temperatura=None, composicion=None
    )

    purga_jarabe = PurgaMateria(nombre="SINK-JARABE")
    purga_vapor_evap = PurgaMateria(nombre="SINK-VAPOR-EVAP")
    purga_condensado = PurgaMateria(nombre="SINK-CONDENSADO")

    # 3. AÑADIR NODOS AL GRAFO
    for equipo in [fuente_jarabe, fuente_vapor_caldera, condensador, evaporador, 
                   purga_jarabe, purga_vapor_evap, purga_condensado]:
        planta.añadir_nodo(equipo)

    # 4. CREAR LAS CORRIENTES (Aristas) Y CONECTAR
    
    # A) Circuito de Calentamiento
    s_vapor_vivo = LineaVapor(
        nombre="S-VaporVivo", temperatura=None, presion=None, flujo_masico=0.0
    )
    s_condensado = LineaMateria(
        nombre="S-Condensado", temperatura=None, presion=None, flujo_masico=0.0
    )
    q_calor = Calor(nombre="Q-Energia", flujo_calor=0.0)
    
    planta.añadir_conexion(fuente_vapor_caldera.nombre, condensador.nombre, s_vapor_vivo)
    planta.añadir_conexion(condensador.nombre, purga_condensado.nombre, s_condensado)
    planta.añadir_conexion(condensador.nombre, evaporador.nombre, q_calor)

    # B) Circuito de Proceso (Jarabe)
    s_jarabe_in = LineaMateria(
        nombre="S-JarabeIn", temperatura=None, presion=None, flujo_masico=0.0
    )
    s_jarabe_out = LineaMateria(
        nombre="S-JarabeOut", temperatura=None, presion=None, flujo_masico=0.0
    )
    s_vapor_out = LineaVapor(
        nombre="S-VaporOut", temperatura=None, presion=None, flujo_masico=0.0
    )

    planta.añadir_conexion(fuente_jarabe.nombre, evaporador.nombre, s_jarabe_in)
    planta.añadir_conexion(evaporador.nombre, purga_jarabe.nombre, s_jarabe_out)
    planta.añadir_conexion(evaporador.nombre, purga_vapor_evap.nombre, s_vapor_out)
    # 5. ¡MAGIA EO! RESOLVER TODO EL SISTEMA SIMULTÁNEAMENTE
    planta.resolver_planta()

    # 6. LEER RESULTADOS DESDE LAS CORRIENTES DEL GRAFO
    print("\n=== REPORTE DE PLANTA ===")
    print(f"Calor transferido por Condensador: {q_calor.flujo_calor:.2e} J/h")
    print(f"Jarabe concentrado: {s_jarabe_out.flujo_masico:.2f} kg/h a {s_jarabe_out.temperatura - 273.15:.2f} °C")
    print(f"Fracción molar final (Glucosa): {s_jarabe_out.composicion['glucose']:.4f}")