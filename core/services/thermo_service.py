"""
Servicio de simulación termodinamica por nodos y componentes
se tomarán las siguientes recomendaciones:
    - El gas de evaporación en el evaporador solamente será vapor de agua
    - La mezcla líquida es jarabe (agua y azucar)
"""

from typing import List

from core.schemas.base import Fase
from core.schemas.streams import Caldera, LineaMateria, ServicioFuente, ServicioPurga, LineaVapor
from core.schemas.engine import Evaporador, IntercambiadorCalor

import CoolProp.CoolProp as CP


class ServicioCaldera:
    """
    Servicio de simulación de vapor
    """
    def __init__(self):
        pass

    @staticmethod
    def sim_caldera(caldera:Caldera)->LineaVapor:
        """
        Simula la caldera para generar la línea de vapor
        """

        if caldera.temperatura:
            entalpia = CP.PropsSI("H", "T", caldera.temperatura, "Q", 1.0, "Water")
            caldera.presion = CP.PropsSI("P", "T", caldera.temperatura, "Q", 1.0, "Water")
        
        elif caldera.presion:
            entalpia = CP.PropsSI("H", "P", caldera.presion, "Q", 1.0, "Water")
            caldera.temperatura = CP.PropsSI("T", "P", caldera.presion, "Q", 1.0, "Water")
        else:
            raise ValueError("No se ha definifo al menos 1 parámetro del nodo caldera")
            

        vapor = LineaVapor(
            nombre=f"S-{caldera.nombre}-out",
            temperatura=caldera.temperatura,
            presion=caldera.presion,
            fase=Fase.ELV,
            entalpia=entalpia,
            calidad=1.0

        )

        return vapor

class ServicioSimQuimica:
    """
    Servicio de simulación de propiedades quimcias presentes
    """

    def __init__(self, componentes:List[str])->None:
        self.componentes = componentes
        pass


if __name__ == "__main__":
    # Prueba de la simulación de la caldera

    caldera = Caldera(
        nombre="C101",
        temperatura=340
    )

    sv = ServicioCaldera()
    s1 = sv.sim_caldera(caldera)

    print(s1)

        



