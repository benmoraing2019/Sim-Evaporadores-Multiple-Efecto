"""Propiedades termodinámicas de corrientes puras y de la mezcla agua-glucosa."""

from typing import Dict

import CoolProp.CoolProp as CP

from core.schemas.base import Fase, PropiedadesQuimicas, Sustancias


class PropSimService:
    """Completa las propiedades termodinámicas faltantes de una corriente."""

    MW_AGUA = 18.015
    MW_GLUCOSA = 180.156
    T_REFERENCIA = 273.15
    CP_AGUA = 4186.0
    CP_GLUCOSA = 1255.0
    FLUIDO = "Water"

    def _asegurar_composicion(self, propiedades: PropiedadesQuimicas) -> None:
        """Asume agua pura cuando la corriente no declara composición."""
        if propiedades.composicion is None:
            propiedades.composicion = {
                Sustancias.WATER.value: 1.0,
                Sustancias.GLUCOSE.value: 0.0,
            }

    @staticmethod
    def _fraccion_molar(composicion: Dict[str, float], sustancia: Sustancias) -> float:
        return composicion.get(sustancia.value, 0.0)

    def _fraccion_masica_glucosa(self, composicion: Dict[str, float]) -> float:
        """Convierte la composición molar en fracción másica de glucosa."""
        x_agua = self._fraccion_molar(composicion, Sustancias.WATER)
        x_glucosa = self._fraccion_molar(composicion, Sustancias.GLUCOSE)

        masa_molar = x_agua * self.MW_AGUA + x_glucosa * self.MW_GLUCOSA
        if masa_molar <= 0.0:
            return 0.0
        return x_glucosa * self.MW_GLUCOSA / masa_molar

    def _peso_molecular_mezcla(self, composicion: Dict[str, float]) -> float:
        """Peso molecular aparente de la mezcla [kg/mol]."""
        x_agua = self._fraccion_molar(composicion, Sustancias.WATER)
        x_glucosa = self._fraccion_molar(composicion, Sustancias.GLUCOSE)
        return (x_agua * self.MW_AGUA + x_glucosa * self.MW_GLUCOSA) / 1000.0

    def _entalpia_molar(self, entalpia_masica: float) -> float:
        """Convierte entalpía másica [J/kg] a molar [J/mol] para el agua."""
        return entalpia_masica * self.MW_AGUA / 1000.0

    def _temperatura_saturacion(self, presion: float, calidad: float) -> float:
        return CP.PropsSI("T", "P", presion, "Q", calidad, self.FLUIDO)

    def _presion_saturacion(self, temperatura: float, calidad: float) -> float:
        return CP.PropsSI("P", "T", temperatura, "Q", calidad, self.FLUIDO)

    def _entalpia_saturada(self, presion: float, calidad: float) -> float:
        return CP.PropsSI("H", "P", presion, "Q", calidad, self.FLUIDO)

    @staticmethod
    def _aumento_ebulloscopico(w_glucosa: float) -> float:
        """Aumento ebulloscópico empírico del jarabe [K]."""
        return 1.78 * w_glucosa + 6.22 * w_glucosa**2

    def _cp_mezcla(self, w_glucosa: float) -> float:
        """Calor específico de la mezcla por regla de mezclado [J/kg-K]."""
        return w_glucosa * self.CP_GLUCOSA + (1.0 - w_glucosa) * self.CP_AGUA

    @staticmethod
    def _fase_por_calidad(calidad: float) -> Fase:
        if calidad == 0.0:
            return Fase.LIQUIDO
        if calidad == 1.0:
            return Fase.VAPOR
        return Fase.ELV

    def simular_vapor_saturado(self, prop: PropiedadesQuimicas) -> PropiedadesQuimicas:
        """Calcula vapor saturado (calidad 1) a partir de presión o temperatura."""
        self._asegurar_composicion(prop)

        if prop.presion is not None:
            prop.temperatura = self._temperatura_saturacion(prop.presion, 1.0)
        elif prop.temperatura is not None:
            prop.presion = self._presion_saturacion(prop.temperatura, 1.0)
        else:
            raise ValueError("Para simular vapor saturado debes definir presión o temperatura.")

        prop.entalpia = self._entalpia_molar(self._entalpia_saturada(prop.presion, 1.0))
        prop.fase = Fase.VAPOR
        prop.calidad = 1.0
        return prop

    def simular_mezcla_jarabe(self, prop: PropiedadesQuimicas) -> PropiedadesQuimicas:
        """Calcula el jarabe en ebullición incluyendo el aumento ebulloscópico."""
        self._asegurar_composicion(prop)
        w_glucosa = self._fraccion_masica_glucosa(prop.composicion)
        bpe = self._aumento_ebulloscopico(w_glucosa)

        if prop.presion is not None:
            prop.temperatura = self._temperatura_saturacion(prop.presion, 0.0) + bpe
        elif prop.temperatura is not None:
            prop.presion = self._presion_saturacion(prop.temperatura - bpe, 0.0)
        else:
            raise ValueError("Para simular la mezcla debes definir presión o temperatura.")

        entalpia_masica = self._cp_mezcla(w_glucosa) * (prop.temperatura - self.T_REFERENCIA)
        prop.entalpia = entalpia_masica * self._peso_molecular_mezcla(prop.composicion)

        prop.fase = Fase.LIQUIDO
        prop.calidad = 0.0
        return prop

    def simular_agua_saturada(self, prop: PropiedadesQuimicas) -> PropiedadesQuimicas:
        """Calcula agua pura saturada; sin calidad asume líquido saturado."""
        self._asegurar_composicion(prop)
        if prop.calidad is None:
            prop.calidad = 0.0

        if prop.presion is not None:
            prop.temperatura = self._temperatura_saturacion(prop.presion, prop.calidad)
        elif prop.temperatura is not None:
            prop.presion = self._presion_saturacion(prop.temperatura, prop.calidad)
        else:
            raise ValueError("Para simular agua saturada debes definir presión o temperatura.")

        prop.entalpia = self._entalpia_molar(self._entalpia_saturada(prop.presion, prop.calidad))
        prop.fase = self._fase_por_calidad(prop.calidad)
        return prop