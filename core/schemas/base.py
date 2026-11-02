"""Entidades base para modelar equipos, conexiones y propiedades de corrientes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from core.services.thermo_service import PropSimService
    from core.services.ecuaciones_manager import GestorSistemaEO


class TipoConexion(Enum):
    """Naturaleza del flujo que transporta una conexión."""

    MATERIA = "MATERIA"
    ENERGIA = "ENERGIA"
    VAPOR = "VAPOR"


class Sustancias(Enum):
    """Sustancias disponibles en la simulación."""

    WATER = "water"
    GLUCOSE = "glucose"

    @classmethod
    def obtener_nombres(cls) -> List[str]:
        """Nombres de todas las sustancias participantes."""
        return [sustancia.value for sustancia in cls]


@dataclass
class Conexion:
    """Corriente que transporta materia, energía o vapor entre equipos."""

    nombre: str
    tipo_conexion: TipoConexion | None = None


class Fase(Enum):
    """Estado físico de una corriente."""

    LIQUIDO = "LIQUIDO"
    VAPOR = "VAPOR"
    ELV = "ELV"


class MezclaAguaGlucosa:
    """Conversiones de composición para la mezcla binaria agua-glucosa."""

    MW_AGUA = 0.018015
    MW_GLUCOSA = 0.180156

    def _peso_molecular_aparente(self, x_glucosa: float) -> float:
        """Peso molecular aparente de la mezcla [kg/mol]."""
        return (1.0 - x_glucosa) * self.MW_AGUA + x_glucosa * self.MW_GLUCOSA

    def _fraccion_molar_a_masica(self, x_glucosa: float) -> float:
        """Convierte fracción molar de glucosa a fracción másica."""
        peso_molecular = self._peso_molecular_aparente(x_glucosa)
        if peso_molecular <= 0.0:
            return 0.0
        return x_glucosa * self.MW_GLUCOSA / peso_molecular

    @staticmethod
    def _composicion_molar(x_glucosa: float) -> Dict[str, float]:
        """Construye la composición molar normalizada a partir de su glucosa."""
        return {
            Sustancias.WATER.value: 1.0 - x_glucosa,
            Sustancias.GLUCOSE.value: x_glucosa,
        }


@dataclass(kw_only=True)
class PropiedadesQuimicas:
    """Propiedades termodinámicas compartidas por equipos y corrientes."""

    temperatura: float | None
    presion: float | None
    composicion: Dict[str, float] | None = field(default=None)
    fase: Fase | None = field(default=None)
    calidad: float | None = field(default=None)
    entalpia: float | None = field(default=None)

    @property
    def propiedades_quimicas(self) -> PropiedadesQuimicas:
        """Copia ordenada de las propiedades químicas de la corriente."""
        return PropiedadesQuimicas(
            temperatura=self.temperatura,
            presion=self.presion,
            composicion=self.composicion,
            fase=self.fase,
            calidad=self.calidad,
            entalpia=self.entalpia,
        )


@dataclass
class Equipo(ABC):
    """Interfaz que todo nodo de la planta debe implementar."""

    nombre: str

    @abstractmethod
    def modelar_sistema(
        self,
        gestor: GestorSistemaEO,
        inlets: List[Conexion],
        outlets: List[Conexion],
        thermo: PropSimService,
    ) -> None:
        """Traduce la física del equipo en variables y residuos del sistema."""

    @abstractmethod
    def aplicar_resultados_finales(
        self,
        inlets: List[Conexion],
        outlets: List[Conexion],
        thermo: PropSimService,
    ) -> None:
        """Fija los valores convergidos en las corrientes y en el propio equipo."""