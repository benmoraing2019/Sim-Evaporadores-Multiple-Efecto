from typing import Dict
import CoolProp.CoolProp as CP
from core.schemas.base import PropiedadesQuimicas, Fase, Sustancias

class PropSimService:
    """
    Servicio de simulación de propiedades termodinámicas puros (Stateless).
    Se encarga exclusivamente de rellenar los datos faltantes en objetos PropiedadesQuimicas.
    """

    def __init__(self) -> None:
        self.MW_water = 18.015      # g/mol
        self.MW_glucose = 180.156   # g/mol
        self.T_ref = 273.15         # Referencia para entalpía (0 °C)

    def _asegurar_composicion(self, propiedades: PropiedadesQuimicas) -> None:
        """
        Si la composición es None, asume automáticamente que es una corriente de agua pura.
        """
        if propiedades.composicion is None:
            propiedades.composicion = {
                Sustancias.WATER.value: 1.0, 
                Sustancias.GLUCOSE.value: 0.0
            }

    def _get_fraccion_masica(self, composicion: Dict[str, float]) -> float:
        """Convierte composición molar a fracción másica de soluto."""
        
        # Uso seguro de las claves mediante el Enum
        x_w = composicion.get(Sustancias.WATER.value, 0.0)
        x_g = composicion.get(Sustancias.GLUCOSE.value, 0.0)
        
        m_w = x_w * self.MW_water
        m_g = x_g * self.MW_glucose
        
        masa_total = m_w + m_g
        return (m_g / masa_total) if masa_total > 0 else 0.0

    def simular_vapor_saturado(self, prop: PropiedadesQuimicas) -> PropiedadesQuimicas:
        """
        Calcula las propiedades de un vapor saturado (ej. vapor de caldera).
        Requiere que al menos 'temperatura' o 'presion' esté definido.
        """
        self._asegurar_composicion(prop)
        
        if prop.presion is not None:
            # Presión conocida, calcular T
            prop.temperatura = CP.PropsSI("T", "P", prop.presion, "Q", 1.0, "Water")
        elif prop.temperatura is not None:
            # Temperatura conocida, calcular P
            prop.presion = CP.PropsSI("P", "T", prop.temperatura, "Q", 1.0, "Water")
        else:
            raise ValueError("Para simular vapor saturado, debes definir Presión o Temperatura.")

        # Calcular Entalpía (J/kg -> J/mol)
        H_masica = CP.PropsSI("H", "P", prop.presion, "Q", 1.0, "Water")
        prop.entalpia = H_masica * (self.MW_water / 1000.0)
        
        prop.fase = Fase.VAPOR
        prop.calidad = 1.0
        
        return prop

    def simular_mezcla_jarabe(self, prop: PropiedadesQuimicas) -> PropiedadesQuimicas:
        """
        Calcula las propiedades del líquido en ebullición (jarabe).
        Calcula T a partir de P (o viceversa) usando Aumento Ebullioscópico (BPE).
        """
        self._asegurar_composicion(prop)
        w_g = self._get_fraccion_masica(prop.composicion)
        
        # BPE empírico
        bpe = 1.78 * w_g + 6.22 * (w_g ** 2)

        if prop.presion is not None:
            # Presión conocida: Calculamos la T de saturación base y le sumamos el BPE
            t_sat_pura = CP.PropsSI("T", "P", prop.presion, "Q", 0.0, "Water")
            prop.temperatura = t_sat_pura + bpe
            
        elif prop.temperatura is not None:
            # Temperatura de la mezcla conocida: Restamos el BPE para hallar la P de saturación del agua
            t_sat_pura = prop.temperatura - bpe
            prop.presion = CP.PropsSI("P", "T", t_sat_pura, "Q", 0.0, "Water")
            
        else:
            raise ValueError("Para simular la mezcla, debes definir Presión o Temperatura.")

        # Cálculo de Entalpía del Jarabe (Regla de Cp)
        Cp_agua = 4186.0
        Cp_azucar = 1255.0
        Cp_mezcla = w_g * Cp_azucar + (1.0 - w_g) * Cp_agua
        
        H_masica = Cp_mezcla * (prop.temperatura - self.T_ref)
        
        # Conversión a molar
        x_w = prop.composicion.get(Sustancias.WATER.value, 0.0)
        x_g = prop.composicion.get(Sustancias.GLUCOSE.value, 0.0)
        MW_mezcla = (x_w * self.MW_water + x_g * self.MW_glucose) / 1000.0
        
        prop.entalpia = H_masica * MW_mezcla
        prop.fase = Fase.LIQUIDO
        prop.calidad = 0.0
        
        return prop

    def simular_agua_saturada(self, prop: PropiedadesQuimicas) -> PropiedadesQuimicas:
        """
        Calcula las propiedades de agua pura saturada (fase determinada por prop.calidad).
        Si prop.calidad es None, asume calidad = 0.0 (Líquido saturado, ej. condensado).
        """
        self._asegurar_composicion(prop)
        
        if prop.calidad is None:
            prop.calidad = 0.0  # Asumimos líquido saturado por defecto (condensado)
            
        if prop.presion is not None:
            prop.temperatura = CP.PropsSI("T", "P", prop.presion, "Q", prop.calidad, "Water")
        elif prop.temperatura is not None:
            prop.presion = CP.PropsSI("P", "T", prop.temperatura, "Q", prop.calidad, "Water")
        else:
            raise ValueError("Para simular agua saturada, debes definir Presión o Temperatura.")

        H_masica = CP.PropsSI("H", "P", prop.presion, "Q", prop.calidad, "Water")
        prop.entalpia = H_masica * (self.MW_water / 1000.0)
        
        prop.fase = Fase.LIQUIDO if prop.calidad == 0.0 else Fase.VAPOR if prop.calidad == 1.0 else Fase.ELV
        
        return prop

if __name__ == "__main__":
    # Instanciamos el servicio calculadora
    sim_service = PropSimService()

    print("=== PRUEBA 1: Vapor de Caldera (Presión dada, Composición None) ===")
    prop_caldera = PropiedadesQuimicas(
        presion=200000.0,  # 200 kPa
        temperatura=None,
        composicion=None   # El servicio debe inyectar agua pura
    )
    res_caldera = sim_service.simular_vapor_saturado(prop_caldera)
    print(f"Temperatura calculada: {res_caldera.temperatura - 273.15:.2f} °C")
    print(f"Entalpía calculada:    {res_caldera.entalpia:.2f} J/mol")
    print(f"Fase asignada:         {res_caldera.fase.value}")
    print(f"Composición inyectada: {res_caldera.composicion}\n")


    print("=== PRUEBA 2: Mezcla en Evaporador (Temperatura dada, P incógnita) ===")
    prop_evaporador = PropiedadesQuimicas(
        presion=None,
        temperatura=273.15 + 90.0,  # Queremos que el jarabe hierva a 90 °C
        composicion={"water": 0.85, "glucose": 0.15}
    )
    res_evaporador = sim_service.simular_mezcla_jarabe(prop_evaporador)
    print(f"Presión calculada:     {res_evaporador.presion / 1000:.2f} kPa")
    print(f"Entalpía calculada:    {res_evaporador.entalpia:.2f} J/mol")
    print(f"Fase asignada:         {res_evaporador.fase.value}\n")


    print("=== PRUEBA 3: Condensado en Intercambiador (Presión dada, Calidad None) ===")
    prop_condensado = PropiedadesQuimicas(
        presion=150000.0,  # 150 kPa
        temperatura=None,
        composicion=None
    )
    res_condensado = sim_service.simular_agua_saturada(prop_condensado)
    print(f"Temperatura calculada: {res_condensado.temperatura - 273.15:.2f} °C")
    print(f"Entalpía calculada:    {res_condensado.entalpia:.2f} J/mol")
    print(f"Calidad inyectada:     {res_condensado.calidad}")
    print(f"Fase asignada:         {res_condensado.fase.value}")