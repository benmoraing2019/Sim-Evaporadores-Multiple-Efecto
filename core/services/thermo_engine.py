"""
Sistema que gestiona las solicitudes a thermo de manera ordenada para evitar colapsos
"""

from core.schemas.logs import Log
from core.schemas.engine import Composicion, Corriente, Evaporador

from typing import Any, List, Dict
from dataclasses import dataclass
from thermo import Mixture
import numpy as np


@dataclass
class ResultadosThermoService:
    exito: bool
    resultados: Mixture

class ThermoService:
    """
    Clase que se encarga de gestionar las consultas a thermo de manera organizada y limpia,
    para evitar la saturación de la API.
    """

    @staticmethod
    def __build_mixture(composicion: Composicion) -> Mixture:
        sustancias = composicion.sustancias 
        fracciones_masa = composicion.fraccion_masa
        
        # Instanciamos Mixture pasando los IDs y las fracciones másicas (ws)
        mix = Mixture(IDs=sustancias, ws=fracciones_masa)
        return mix

    @staticmethod
    def __evaluar_propiedades(mix: Mixture, temperatura: float, presion: float, fracciones: List[float]) -> ResultadosThermoService:
        try:
            mix.T = temperatura
            mix.P = presion
            mix.ws = fracciones 
            
            if hasattr(mix, 'calculate'):
                mix.calculate(T=temperatura, P=presion, ws=fracciones)

            return ResultadosThermoService(
                exito=True,
                resultados=mix
            )

        except Exception as e:
            Log.warning(f"Sistema de convergencia falló: {str(e)}")
            return ResultadosThermoService(
                exito=False,
                resultados=mix
            )

    @classmethod
    def evaluar_corriente(cls, corriente: Corriente) -> ResultadosThermoService:
        """
        Método público principal para evaluar una corriente de la planta.
        """
        mixture = cls.__build_mixture(corriente.composicion)

        resultados = cls.__evaluar_propiedades(
            mix=mixture,
            temperatura=corriente.temperatura,
            presion=corriente.presion,
            fracciones=corriente.composicion.fraccion_masa
        )

        return resultados

    @classmethod
    def evaluar_evaporador(cls, evp: Evaporador) -> ResultadosThermoService:
        """
        Método público principal para evaluar un equipo evaporador.
        """
        mix = cls.__build_mixture(evp.composicion)
        resultados = cls.__evaluar_propiedades(
            mix=mix,
            temperatura=evp.temperatura,
            presion=evp.presion,
            fracciones=evp.composicion.fraccion_masa
        )

        return resultados


if __name__ == "__main__":
    cmp = Composicion(
            sustancias=["water", "acetone"], # Corregido de "cetone" a "acetone"
            fraccion_masa=[0.6, 0.4],
            metodo="NRTL" # Corregido de "NLTR" a "NRTL"
        )
    c1 = Corriente(
        "S1",
        composicion=cmp,
        temperatura=300,
        presion=101325.0, # Presión en Pascales (recomendado para thermo)
        flujo_masico=10.0
    )

    evp = Evaporador(
        nombre="E-101",
        nombres_puertos=["up", "down"],
        temperatura=350.0,
        presion=101325.0,
        masa_holgura=0.5,
        composicion=cmp
    )

    # Al ser métodos de clase o estáticos, puedes llamarlos directamente desde la clase
    rest = ThermoService.evaluar_corriente(c1)
    rest_evp = ThermoService.evaluar_evaporador(evp)

    print("¿Evaluación de corriente exitosa?:", rest.exito)
    if rest.exito:
        print(f" -> Entalpía molar: {rest.resultados.H:.2f} J/mol")
        
    print("¿Evaluación de evaporador exitosa?:", rest_evp.exito)
    if rest_evp.exito:
        print(f" -> Fase del evaporador: {rest_evp.resultados.phase}")