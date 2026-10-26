from core.schemas.base import Composicion, Fase
from core.schemas.engine import (
    Evaporador,
    Fuente,
    IntercambiadorCalor,
    Sumidero,
)
from core.schemas.network import RedProceso
from core.schemas.streams import CargaTermica, Corriente


def construir_triple_efecto() -> RedProceso:
    red = RedProceso()

    ev = [Evaporador(nombre=f"E-10{i}", puertos=Evaporador.puertos_estandar(),
                     presion_operacion=p)
          for i, p in zip((1, 2, 3), (1.0e5, 5.0e4, 2.0e4))]

    ic = [IntercambiadorCalor(nombre=f"IC-10{i}",
                              puertos=IntercambiadorCalor.puertos_estandar(),
                              area=50.0, coeficiente_global=900.0)
          for i in (1, 2, 3)]

    # --- fronteras del proceso (los puertos se generan solos)
    vapor_vivo = Fuente(nombre="VAPOR-VIVO")
    alimentacion = Fuente(nombre="ALIM")
    cond_1 = Sumidero(nombre="COND-1")
    cond_2 = Sumidero(nombre="COND-2")
    cond_3 = Sumidero(nombre="COND-3")
    vapor_3 = Sumidero(nombre="VAPOR-3")
    licor = Sumidero(nombre="LICOR")

    red.agregar(*ev, *ic, vapor_vivo, alimentacion,
                cond_1, cond_2, cond_3, vapor_3, licor)

    comp = Composicion(fracciones={"water": 0.95, "glucose": 0.05})

    # --- cadena térmica
    red.conectar_materia("VAPOR-VIVO", "salida", "IC-101", "entrada_caliente",
                         Corriente(nombre="VV", comp=comp, temperatura=393.0,
                                   presion=2.0e5, flujo_masico=1.2,
                                   fase=Fase.VAPOR))
    red.conectar_energia("IC-101", "q", "E-101", "q",
                         CargaTermica(nombre="Q1"))
    red.conectar_materia("IC-101", "condensado", "COND-1", "entrada",
                         Corriente(nombre="C1", comp=comp, temperatura=393.0,
                                   presion=2.0e5, flujo_masico=0.0))

    # --- alimentación al primer efecto
    red.conectar_materia("ALIM", "salida", "E-101", "alimentacion",
                         Corriente(nombre="F", comp=comp, temperatura=298.0,
                                   presion=1.0e5, flujo_masico=5.0))

    # --- vapor de E1 condensa en IC2 y entrega Q2 a E2
    red.conectar_materia("E-101", "vapor", "IC-102", "entrada_caliente",
                         Corriente(nombre="V1", comp=comp, temperatura=373.0,
                                   presion=1.0e5, flujo_masico=0.0, fase=Fase.VAPOR))
    red.conectar_energia("IC-102", "q", "E-102", "q",
                         CargaTermica(nombre="Q2"))
    red.conectar_materia("IC-102", "condensado", "COND-2", "entrada",
                         Corriente(nombre="C2", comp=comp, temperatura=373.0,
                                   presion=1.0e5, flujo_masico=0.0))

    # --- vapor de E2 -> IC3 -> E3
    red.conectar_materia("E-102", "vapor", "IC-103", "entrada_caliente",
                         Corriente(nombre="V2", comp=comp, temperatura=354.0,
                                   presion=5.0e4, flujo_masico=0.0, fase=Fase.VAPOR))
    red.conectar_energia("IC-103", "q", "E-103", "q",
                         CargaTermica(nombre="Q3"))
    red.conectar_materia("IC-103", "condensado", "COND-3", "entrada",
                         Corriente(nombre="C3", comp=comp, temperatura=354.0,
                                   presion=5.0e4, flujo_masico=0.0))

    # --- licor: E1 -> E2 -> E3
    red.conectar_materia("E-101", "liquido", "E-102", "alimentacion",
                         Corriente(nombre="L1", comp=comp, temperatura=373.0,
                                   presion=1.0e5, flujo_masico=0.0))
    red.conectar_materia("E-102", "liquido", "E-103", "alimentacion",
                         Corriente(nombre="L2", comp=comp, temperatura=354.0,
                                   presion=5.0e4, flujo_masico=0.0))

    # --- salidas del último efecto
    red.conectar_materia("E-103", "vapor", "VAPOR-3", "entrada",
                         Corriente(nombre="V3", comp=comp, temperatura=333.0,
                                   presion=2.0e4, flujo_masico=0.0, fase=Fase.VAPOR))
    red.conectar_materia("E-103", "liquido", "LICOR", "entrada",
                         Corriente(nombre="L3", comp=comp, temperatura=333.0,
                                   presion=2.0e4, flujo_masico=0.0))

    return red



if __name__ == "__main__":
    red = construir_triple_efecto()

    print(f"Nodos: {red.g.number_of_nodes()}  Aristas: {red.g.number_of_edges()}")
    print()
    for eq in red.orden_resolucion():
        print(f"{type(eq).__name__:<20} {eq.nombre}")

    problemas = red.validar()
    print()
    if problemas:
        print(f"{len(problemas)} problema(s):")
        for p in problemas:
            print(f"  - {p}")
    else:
        print("Red válida: todos los puertos conectados.")