"""Equipos de proceso y su traducción a ecuaciones de balance."""

from dataclasses import dataclass
from functools import partial
from typing import List, Optional, Sequence, TypeVar

from core.schemas.base import (
    Conexion,
    Equipo,
    Fase,
    MezclaAguaGlucosa,
    PropiedadesQuimicas,
    Sustancias,
    TipoConexion,
)
from core.schemas.streams import Calor, LineaMateria, LineaVapor
from core.services.ecuaciones_manager import GestorSistemaEO
from core.services.thermo_service import PropSimService

_PRESION_ATMOSFERICA = 101325.0
_TEMPERATURA_REFERENCIA = 273.15
_TEMPERATURA_AMBIENTE = _TEMPERATURA_REFERENCIA + 25.0
_TEMPERATURA_EXPANSION = _TEMPERATURA_REFERENCIA + 80.0
_FLUJO_MASICO_SEMILLA = 1000.0
_CALOR_ESTIMADO_POR_DEFECTO = 1000.0
_FRACCION_GLUCOSA_GUESS = 0.05
_ESCALA_ENERGIA = 1e6
_ESCALA_ENTALPIA_EXPANSION = 1e3
_MW_AGUA = 0.018015
_COMPOSICION_SEMILLA = {
    Sustancias.WATER.value: 0.95,
    Sustancias.GLUCOSE.value: 0.05,
}

_ConexionT = TypeVar("_ConexionT", bound=Conexion)


def _lineas_materia(corrientes: Sequence[Conexion]) -> List[LineaMateria]:
    """Filtra las corrientes que transportan materia líquida."""
    return [
        corriente
        for corriente in corrientes
        if isinstance(corriente, LineaMateria)
        and corriente.tipo_conexion is TipoConexion.MATERIA
    ]


def _unica(corrientes: Sequence[_ConexionT], rol: str) -> _ConexionT:
    """Devuelve la primera corriente del rol pedido o falla con un mensaje claro."""
    if not corrientes:
        raise ValueError(f"El equipo requiere una corriente de {rol}.")
    return corrientes[0]


def _fraccion_molar_glucosa(corriente: LineaMateria) -> float:
    composicion = corriente.composicion or {}
    return composicion.get(Sustancias.GLUCOSE.value, 0.0)


def _completar_corriente(
    corriente: LineaMateria,
    *,
    temperatura: Optional[float] = None,
    con_composicion: bool = True,
) -> None:
    """Rellena las condiciones mínimas para que la termodinámica pueda resolver."""
    if corriente.presion is None and corriente.temperatura is None:
        corriente.presion = _PRESION_ATMOSFERICA
        corriente.temperatura = temperatura
    if con_composicion and corriente.composicion is None:
        corriente.composicion = dict(_COMPOSICION_SEMILLA)
    if not corriente.flujo_masico:
        corriente.flujo_masico = _FLUJO_MASICO_SEMILLA


@dataclass
class Evaporador(MezclaAguaGlucosa, Equipo, PropiedadesQuimicas):
    """Separa el vapor generado y concentra el jarabe que lo acompaña."""

    masa: float

    def modelar_sistema(
        self,
        gestor: GestorSistemaEO,
        inlets: List[Conexion],
        outlets: List[Conexion],
        termo: PropSimService,
    ) -> None:
        self._seleccionar_corrientes(inlets, outlets)
        self._preparar_entrada(termo)
        self._registrar_incognitas(gestor)

        gestor.registrar_residuo(self._residuo_masa)
        gestor.registrar_residuo(self._residuo_soluto)
        gestor.registrar_residuo(partial(self._residuo_energia, termo))

    def aplicar_resultados_finales(
        self,
        inlets: List[Conexion],
        outlets: List[Conexion],
        termo: PropSimService,
    ) -> None:
        self._seleccionar_corrientes(inlets, outlets)
        self._actualizar_salidas(termo)

        self.temperatura = self._salida_liquido.temperatura
        self.composicion = self._salida_liquido.composicion
        self.entalpia = self._salida_liquido.entalpia
        self.fase = self._salida_liquido.fase

    def _seleccionar_corrientes(
        self, inlets: List[Conexion], outlets: List[Conexion]
    ) -> None:
        self._entrada = _unica(_lineas_materia(inlets), "alimentación de jarabe")
        self._calor = next((c for c in inlets if isinstance(c, Calor)), None)
        self._salida_liquido = _unica(_lineas_materia(outlets), "líquido concentrado")
        self._salida_vapor = _unica(
            [c for c in outlets if isinstance(c, LineaVapor)], "vapor generado"
        )

    def _preparar_entrada(self, termo: PropSimService) -> None:
        if self._entrada.entalpia is None:
            _completar_corriente(self._entrada)
            termo.simular_mezcla_jarabe(self._entrada)
        self._x_glucosa_entrada = _fraccion_molar_glucosa(self._entrada)

    def _registrar_incognitas(self, gestor: GestorSistemaEO) -> None:
        flujo_entrada = self._entrada.flujo_masico
        self._var_flujo_liquido = gestor.registrar_variable(
            f"{self.nombre}.flujo_L", flujo_entrada * 0.5
        )
        self._var_flujo_vapor = gestor.registrar_variable(
            f"{self.nombre}.flujo_V", flujo_entrada * 0.5
        )
        self._var_x_glucosa = gestor.registrar_variable(
            f"{self.nombre}.x_glucose", min(self._x_glucosa_entrada * 1.5, 0.99)
        )

    def _residuo_masa(self) -> float:
        return self._entrada.flujo_masico - (
            self._var_flujo_liquido.valor + self._var_flujo_vapor.valor
        )

    def _residuo_soluto(self) -> float:
        glucosa_entrada = self._entrada.flujo_masico * self._fraccion_molar_a_masica(
            self._x_glucosa_entrada
        )
        glucosa_salida = self._var_flujo_liquido.valor * self._fraccion_molar_a_masica(
            self._var_x_glucosa.valor
        )
        return glucosa_entrada - glucosa_salida

    def _residuo_energia(self, termo: PropSimService) -> float:
        self._actualizar_salidas(termo)
        calor_entrada = self._calor.flujo_calor if self._calor else 0.0
        entalpia_entrada = self._entalpia_entrada() + calor_entrada
        entalpia_salida = self._entalpia_liquido() + self._entalpia_vapor()
        return (entalpia_entrada - entalpia_salida) / _ESCALA_ENERGIA

    def _entalpia_entrada(self) -> float:
        flujo_molar = self._entrada.flujo_masico / self._peso_molecular_aparente(
            self._x_glucosa_entrada
        )
        return flujo_molar * self._entrada.entalpia

    def _entalpia_liquido(self) -> float:
        flujo_molar = self._var_flujo_liquido.valor / self._peso_molecular_aparente(
            self._var_x_glucosa.valor
        )
        return flujo_molar * self._salida_liquido.entalpia

    def _entalpia_vapor(self) -> float:
        return (self._var_flujo_vapor.valor / _MW_AGUA) * self._salida_vapor.entalpia

    def _actualizar_salidas(self, termo: PropSimService) -> None:
        self._salida_liquido.flujo_masico = self._var_flujo_liquido.valor
        self._salida_vapor.flujo_masico = self._var_flujo_vapor.valor

        self._salida_liquido.composicion = self._composicion_molar(self._var_x_glucosa.valor)
        self._salida_liquido.presion = self.presion
        termo.simular_mezcla_jarabe(self._salida_liquido)

        self._salida_vapor.composicion = self._composicion_molar(0.0)
        self._salida_vapor.temperatura = self._salida_liquido.temperatura
        self._salida_vapor.presion = self.presion
        termo.simular_vapor_saturado(self._salida_vapor)


@dataclass
class Mezclador(MezclaAguaGlucosa, Equipo):
    """Une varias corrientes de materia en una única salida adiabática."""

    def modelar_sistema(
        self,
        gestor: GestorSistemaEO,
        inlets: List[Conexion],
        outlets: List[Conexion],
        termo: PropSimService,
    ) -> None:
        self._seleccionar_corrientes(inlets, outlets)
        self._preparar_entradas(termo)
        self._registrar_incognitas(gestor)

        gestor.registrar_residuo(self._residuo_masa)
        gestor.registrar_residuo(self._residuo_soluto)
        gestor.registrar_residuo(partial(self._residuo_energia, termo))

    def aplicar_resultados_finales(
        self,
        inlets: List[Conexion],
        outlets: List[Conexion],
        termo: PropSimService,
    ) -> None:
        self._seleccionar_corrientes(inlets, outlets)
        self._salida.flujo_masico = self._var_flujo.valor
        self._actualizar_salida(termo)

    def _seleccionar_corrientes(
        self, inlets: List[Conexion], outlets: List[Conexion]
    ) -> None:
        self._entradas = _lineas_materia(inlets)
        self._salida = _unica(_lineas_materia(outlets), "mezcla")

    def _preparar_entradas(self, termo: PropSimService) -> None:
        for corriente in self._entradas:
            if corriente.entalpia is None:
                termo.simular_mezcla_jarabe(corriente)

    def _registrar_incognitas(self, gestor: GestorSistemaEO) -> None:
        flujo_entrada = sum(c.flujo_masico for c in self._entradas)
        self._presion_salida = min(
            (c.presion for c in self._entradas if c.presion is not None),
            default=_PRESION_ATMOSFERICA,
        )
        self._var_flujo = gestor.registrar_variable(
            f"{self.nombre}.flujo_out", flujo_entrada or 100.0
        )
        self._var_x_glucosa = gestor.registrar_variable(
            f"{self.nombre}.xg_out", _FRACCION_GLUCOSA_GUESS
        )
        self._var_temperatura = gestor.registrar_variable(
            f"{self.nombre}.T_out", _TEMPERATURA_AMBIENTE
        )

    def _residuo_masa(self) -> float:
        return self._var_flujo.valor - sum(c.flujo_masico for c in self._entradas)

    def _residuo_soluto(self) -> float:
        glucosa_entrada = sum(
            corriente.flujo_masico
            * self._fraccion_molar_a_masica(_fraccion_molar_glucosa(corriente))
            for corriente in self._entradas
        )
        glucosa_salida = self._var_flujo.valor * self._fraccion_molar_a_masica(
            self._var_x_glucosa.valor
        )
        return glucosa_salida - glucosa_entrada

    def _residuo_energia(self, termo: PropSimService) -> float:
        self._actualizar_salida(termo)
        entalpia_entrada = sum(
            self._flujo_molar(corriente) * corriente.entalpia
            for corriente in self._entradas
        )
        flujo_molar_salida = self._var_flujo.valor / self._peso_molecular_aparente(
            self._var_x_glucosa.valor
        )
        return flujo_molar_salida * self._salida.entalpia - entalpia_entrada

    def _flujo_molar(self, corriente: LineaMateria) -> float:
        return corriente.flujo_masico / self._peso_molecular_aparente(
            _fraccion_molar_glucosa(corriente)
        )

    def _actualizar_salida(self, termo: PropSimService) -> None:
        self._salida.composicion = self._composicion_molar(self._var_x_glucosa.valor)
        self._salida.presion = self._presion_salida
        self._salida.temperatura = self._var_temperatura.valor
        termo.simular_mezcla_jarabe(self._salida)


@dataclass
class FuenteMateria(Equipo, PropiedadesQuimicas):
    """Impone las condiciones de una corriente de suministro."""

    flujo_masico: float

    def modelar_sistema(
        self,
        gestor: GestorSistemaEO,
        inlets: List[Conexion],
        outlets: List[Conexion],
        termo: PropSimService,
    ) -> None:
        self._salida = _unica(outlets, "salida de la fuente")
        self._simular(termo)
        self._propagar_salida()

        self._var_flujo = gestor.registrar_variable(
            f"{self.nombre}.F_out", self.flujo_masico
        )
        self._var_temperatura = gestor.registrar_variable(
            f"{self.nombre}.T_out", self.temperatura
        )

        gestor.registrar_residuo(self._residuo_masa)
        gestor.registrar_residuo(self._residuo_temperatura)

    def aplicar_resultados_finales(
        self,
        inlets: List[Conexion],
        outlets: List[Conexion],
        termo: PropSimService,
    ) -> None:
        self._salida = _unica(outlets, "salida de la fuente")
        self._salida.flujo_masico = self._var_flujo.valor
        self._salida.temperatura = self._var_temperatura.valor
        self._propagar_estado()

    def _simular(self, termo: PropSimService) -> None:
        if self.entalpia is not None:
            return
        if self.fase is Fase.VAPOR:
            termo.simular_vapor_saturado(self)
        else:
            termo.simular_mezcla_jarabe(self)

    def _propagar_salida(self) -> None:
        self._salida.flujo_masico = self.flujo_masico
        self._salida.temperatura = self.temperatura
        self._propagar_estado()

    def _propagar_estado(self) -> None:
        self._salida.presion = self.presion
        self._salida.composicion = self.composicion
        self._salida.entalpia = self.entalpia
        self._salida.calidad = self.calidad
        self._salida.fase = self.fase

    def _residuo_masa(self) -> float:
        return self._var_flujo.valor - self.flujo_masico

    def _residuo_temperatura(self) -> float:
        self._salida.flujo_masico = self._var_flujo.valor
        self._salida.temperatura = self._var_temperatura.valor
        return self._var_temperatura.valor - self.temperatura


@dataclass
class PurgaMateria(Equipo):
    """Sumidero que cierra el grafo sin añadir ecuaciones."""

    def modelar_sistema(
        self,
        gestor: GestorSistemaEO,
        inlets: List[Conexion],
        outlets: List[Conexion],
        termo: PropSimService,
    ) -> None:
        return None

    def aplicar_resultados_finales(
        self,
        inlets: List[Conexion],
        outlets: List[Conexion],
        termo: PropSimService,
    ) -> None:
        return None


@dataclass
class Valvula(Equipo):
    """Expansión isentálpica que reduce la presión del jarabe."""

    presion_salida: float

    def modelar_sistema(
        self,
        gestor: GestorSistemaEO,
        inlets: List[Conexion],
        outlets: List[Conexion],
        termo: PropSimService,
    ) -> None:
        self._seleccionar_corrientes(inlets, outlets)
        self._preparar_entrada(termo)

        self._var_flujo = gestor.registrar_variable(
            f"{self.nombre}.F_out", self._entrada.flujo_masico
        )
        self._var_temperatura = gestor.registrar_variable(
            f"{self.nombre}.T_out", self._entrada.temperatura
        )

        gestor.registrar_residuo(self._residuo_masa)
        gestor.registrar_residuo(partial(self._residuo_energia, termo))

    def aplicar_resultados_finales(
        self,
        inlets: List[Conexion],
        outlets: List[Conexion],
        termo: PropSimService,
    ) -> None:
        self._seleccionar_corrientes(inlets, outlets)
        self._actualizar_salida(termo)

    def _seleccionar_corrientes(
        self, inlets: List[Conexion], outlets: List[Conexion]
    ) -> None:
        self._entrada = _unica(_lineas_materia(inlets), "entrada")
        self._salida = _unica(_lineas_materia(outlets), "salida")

    def _preparar_entrada(self, termo: PropSimService) -> None:
        if self._entrada.entalpia is not None:
            return
        _completar_corriente(self._entrada, temperatura=_TEMPERATURA_EXPANSION)
        termo.simular_mezcla_jarabe(self._entrada)

    def _residuo_masa(self) -> float:
        return self._var_flujo.valor - self._entrada.flujo_masico

    def _residuo_energia(self, termo: PropSimService) -> float:
        self._actualizar_salida(termo)
        return (self._salida.entalpia - self._entrada.entalpia) / _ESCALA_ENTALPIA_EXPANSION

    def _actualizar_salida(self, termo: PropSimService) -> None:
        self._salida.flujo_masico = self._var_flujo.valor
        self._salida.presion = self.presion_salida
        self._salida.temperatura = self._var_temperatura.valor
        self._salida.composicion = self._entrada.composicion
        termo.simular_mezcla_jarabe(self._salida)


@dataclass
class IntercambiadorCalor(Equipo):
    """Condensa vapor de servicio y entrega el calor latente al proceso."""

    def modelar_sistema(
        self,
        gestor: GestorSistemaEO,
        inlets: List[Conexion],
        outlets: List[Conexion],
        termo: PropSimService,
    ) -> None:
        self._seleccionar_corrientes(inlets, outlets)
        self._preparar_vapor(termo)

        self._var_calor = gestor.registrar_variable(
            f"{self.nombre}.Q_lib_MW", self._calor_estimado()
        )
        gestor.registrar_residuo(partial(self._residuo_energia, termo))

    def aplicar_resultados_finales(
        self,
        inlets: List[Conexion],
        outlets: List[Conexion],
        termo: PropSimService,
    ) -> None:
        self._seleccionar_corrientes(inlets, outlets)
        self._salida_liquido.composicion = self._entrada_vapor.composicion
        self._actualizar_condensado(termo)
        self._salida_calor.flujo_calor = self._var_calor.valor * _ESCALA_ENERGIA

    def _seleccionar_corrientes(
        self, inlets: List[Conexion], outlets: List[Conexion]
    ) -> None:
        self._entrada_vapor = _unica(
            [c for c in inlets if isinstance(c, LineaVapor)], "vapor de servicio"
        )
        self._salida_liquido = _unica(_lineas_materia(outlets), "condensado")
        self._salida_calor = _unica(
            [c for c in outlets if isinstance(c, Calor)], "calor entregado"
        )

    def _preparar_vapor(self, termo: PropSimService) -> None:
        if self._entrada_vapor.entalpia is not None:
            return
        _completar_corriente(self._entrada_vapor, con_composicion=False)
        termo.simular_vapor_saturado(self._entrada_vapor)

    def _calor_estimado(self) -> float:
        flujo_vapor = self._entrada_vapor.flujo_masico
        if flujo_vapor > 0:
            return flujo_vapor * 2.2
        return _CALOR_ESTIMADO_POR_DEFECTO

    def _residuo_energia(self, termo: PropSimService) -> float:
        self._actualizar_condensado(termo)
        calor_liberado = self._var_calor.valor * _ESCALA_ENERGIA
        self._salida_calor.flujo_calor = calor_liberado

        flujo_molar = self._entrada_vapor.flujo_masico / _MW_AGUA
        entalpia_entrada = flujo_molar * self._entrada_vapor.entalpia
        entalpia_salida = flujo_molar * self._salida_liquido.entalpia
        return (entalpia_entrada - entalpia_salida - calor_liberado) / _ESCALA_ENERGIA

    def _actualizar_condensado(self, termo: PropSimService) -> None:
        self._salida_liquido.flujo_masico = self._entrada_vapor.flujo_masico
        self._salida_liquido.presion = self._entrada_vapor.presion
        self._salida_liquido.calidad = 0.0
        termo.simular_agua_saturada(self._salida_liquido)