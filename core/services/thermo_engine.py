"""
Sistema que gestiona las solicitudes a thermo de manera ordenada para evitar colapsos.

Modelo termodinámico por defecto: UNIFAC Dortmund (predictivo por contribución de
grupos, no requiere parámetros binarios experimentales), ideal para el análisis de
evaporadores.
"""

from typing import Any, List
from dataclasses import dataclass

import numpy as np

from thermo import CEOSGas, ChemicalConstantsPackage, FlashVL, PRMIX
from thermo.phases import GibbsExcessLiquid
from thermo.unifac import UNIFAC, DOUFIP2006, DOUFSG, load_group_assignments_DDBST
import thermo.unifac

from core.schemas.logs import Log
from core.schemas.engine import Composicion, Corriente, Evaporador


@dataclass
class ResultadosThermoService:
    exito: bool
    resultados: Any  # resultado de FlashVL.flash (EquilibriumState)


class ThermoService:
    """
    Clase que se encarga de gestionar las consultas a thermo de manera organizada y limpia.

    Estrategia de modelo termodinámico:
      - DEFAULT: UNIFAC Dortmund (predictivo por contribución de grupos).
      - NRTL / UNIQUAC / WILSON: reservados para cuando se disponga de parámetros
        binarios experimentales (aún no implementados).
    """

    @staticmethod
    def __ws_to_xs(fracciones_masa: List[float], MWs: List[float]) -> List[float]:
        """Convierte fracción másica a fracción molar usando pesos moleculares."""
        n = np.array(fracciones_masa) / np.array(MWs)
        return (n / n.sum()).tolist()

    @staticmethod
    def __build_unifac_liquid(constants, correlations, xs: List[float]) -> GibbsExcessLiquid:
        """Construye la fase líquida con UNIFAC Dortmund (version=1)."""
        load_group_assignments_DDBST()

        chemgroups = [
            thermo.unifac.DDBST_MODIFIED_UNIFAC_assignments[inchi_key]
            for inchi_key in constants.InChI_Keys
        ]

        ge = UNIFAC.from_subgroups(
            T=298.15,
            xs=xs,
            chemgroups=chemgroups,
            version=1,  # 1 = Dortmund (recomendado en industria)
            interaction_data=DOUFIP2006,
            subgroups=DOUFSG,
        )

        return GibbsExcessLiquid(
            VaporPressures=correlations.VaporPressures,
            VolumeLiquids=correlations.VolumeLiquids,
            HeatCapacityGases=correlations.HeatCapacityGases,
            GibbsExcessModel=ge,
            T=298.15,
            P=101325.0,
            zs=xs,
        )

    @classmethod
    def __build_flasher(cls, composicion: Composicion):
        """
        Construye un FlashVL listo para evaluar. Devuelve (flasher, xs).
        """
        sustancias = composicion.sustancias
        metodo = (composicion.metodo or "UNIFAC").upper().strip()

        # from_IDs devuelve (constants, correlations) ya combinados.
        constants, correlations = ChemicalConstantsPackage.from_IDs(sustancias)

        # UNIFAC trabaja en fracciones molares.
        xs = cls.__ws_to_xs(composicion.fraccion_masa, constants.MWs)

        # Fase gas: siempre EoS cúbica (Peng-Robinson).
        eos_kwargs = dict(
            Tcs=constants.Tcs,
            Pcs=constants.Pcs,
            omegas=constants.omegas,
        )
        gas = CEOSGas(PRMIX, eos_kwargs, HeatCapacityGases=correlations.HeatCapacityGases)

        # Fase líquida según el método (DEFAULT = UNIFAC).
        if metodo in ("NRTL", "UNIQUAC", "WILSON"):
            Log.warning(
                f"El método '{metodo}' requiere parámetros binarios experimentales; "
                "aún no está soportado. Usando UNIFAC por defecto.",
                show=True,
            )
            liquid = cls.__build_unifac_liquid(constants, correlations, xs)
        else:
            if metodo not in ("UNIFAC", ""):
                Log.warning(
                    f"Método '{metodo}' no reconocido. Usando UNIFAC por defecto.",
                    show=True,
                )
            liquid = cls.__build_unifac_liquid(constants, correlations, xs)

        return FlashVL(constants, correlations, gas=gas, liquid=liquid), xs

    @staticmethod
    def __evaluar_propiedades(
        flasher, xs: List[float], temperatura: float, presion: float
    ) -> ResultadosThermoService:
        try:
            res = flasher.flash(T=temperatura, P=presion, zs=xs)
            return ResultadosThermoService(exito=True, resultados=res)
        except Exception as e:
            Log.warning(f"Sistema de convergencia falló: {str(e)}")
            return ResultadosThermoService(exito=False, resultados=None)

    @classmethod
    def evaluar_corriente(cls, corriente: Corriente) -> ResultadosThermoService:
        """Método público principal para evaluar una corriente de la planta."""
        flasher, xs = cls.__build_flasher(corriente.composicion)
        return cls.__evaluar_propiedades(
            flasher=flasher,
            xs=xs,
            temperatura=corriente.temperatura,
            presion=corriente.presion,
        )

    @classmethod
    def evaluar_evaporador(cls, evp: Evaporador) -> ResultadosThermoService:
        """Método público principal para evaluar un equipo evaporador."""
        flasher, xs = cls.__build_flasher(evp.composicion)
        return cls.__evaluar_propiedades(
            flasher=flasher,
            xs=xs,
            temperatura=evp.temperatura,
            presion=evp.presion,
        )


if __name__ == "__main__":
    cmp = Composicion(
        sustancias=["water", "acetone"],
        fraccion_masa=[0.6, 0.4],
    )

    c1 = Corriente(
        "S1",
        composicion=cmp,
        temperatura=800.0,
        presion=101325.0,  # Presión en Pascales
        flujo_masico=10.0,
    )

    evp = Evaporador(
        nombre="E-101",
        nombres_puertos=["up", "down"],
        temperatura=850.0,
        presion=101325.0,
        masa_holgura=0.5,
        composicion=cmp,
    )

    rest = ThermoService.evaluar_corriente(c1)
    rest_evp = ThermoService.evaluar_evaporador(evp)

    print("¿Evaluación de corriente exitosa?:", rest.exito)
    if rest.exito:
        print(f" -> Fase: {rest.resultados.phase}")
        print(f" -> Entalpía molar: {rest.resultados.H():.2f} J/mol")

    print("¿Evaluación de evaporador exitosa?:", rest_evp.exito)
    if rest_evp.exito:
        print(f" -> Fase del evaporador: {rest_evp.resultados.phase}")