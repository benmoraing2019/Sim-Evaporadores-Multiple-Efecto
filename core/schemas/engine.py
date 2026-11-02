"""
Estructura de los equipos y sus interconecciones
"""
from dataclasses import dataclass
from typing import List

# Solo importamos de base.py lo que vive físicamente allí
from core.schemas.base import Equipo, PropiedadesQuimicas, Conexion, TipoConexion
from core.schemas.base import Fase
from core.schemas.streams import LineaMateria, LineaVapor, Calor

# Importamos las herramientas (Servicios) desde su propia carpeta
from core.services.ecuaciones_manager import GestorSistemaEO
from core.services.thermo_service import PropSimService

@dataclass
class IntercambiadorCalor(Equipo):
    """
    Clase que gestiona el comportamienton del intercambiador de calor (Condensador)
    """
    superficie_transferencia:float
    coeficiente_transferencia:float

@dataclass
class Evaporador(Equipo, PropiedadesQuimicas):
    """
    Clase que gestiona los datos del evaporador
    """

    masa:float

    def _fraccion_molar_masica(self, x_g:float)->float:
        """
        Convierte una fracción molar a másica
        """

        mw_w = 0.018015
        mw_g = 0.180156

        x_w = 1.0 - x_g

        masa_total = (x_w * mw_w) + (x_g * mw_g)
        return (x_g * mw_g) / masa_total if masa_total > 0 else 0.0

    def _peso_molecular_aparente(self, x_g: float) -> float:
        """Calcula el peso molecular de la mezcla en kg/mol."""
        return (1.0 - x_g) * 0.018015 + x_g * 0.180156

    def modelar_sistema(
            self, 
            gestor:GestorSistemaEO, 
            inlets:List[Conexion], 
            outlets:List[Conexion], 
            termo:PropSimService
    ):
        mat_in = next(
            c for c in inlets if isinstance(c, LineaMateria) and c.tipo_conexion == TipoConexion.MATERIA
        )

        calor_in = next(
            (c for c in inlets if isinstance(c, Calor)), None
        )

        liq_out = next(
            c for c in outlets if isinstance(c, LineaMateria) and c.tipo_conexion == TipoConexion.MATERIA
        )
        vap_out = next(
            c for c in outlets if isinstance(c, LineaVapor)
        )

        if mat_in.entalpia is None:
            # --- INYECCIÓN DE SEMILLAS (Defensa EO) ---
            if mat_in.presion is None and mat_in.temperatura is None:
                mat_in.presion = 101325.0
            if mat_in.composicion is None:
                mat_in.composicion = {"water": 0.95, "glucose": 0.05}
            if mat_in.flujo_masico == 0.0 or mat_in.flujo_masico is None:
                mat_in.flujo_masico = 1000.0
            # ------------------------------------------
            termo.simular_mezcla_jarabe(mat_in)

        x_g_in = mat_in.composicion.get("glucose", 0.0)
        
        self._var_L = gestor.registrar_variable(f"{self.nombre}.flujo_L", mat_in.flujo_masico * 0.5)
        self._var_V = gestor.registrar_variable(f"{self.nombre}.flujo_V", mat_in.flujo_masico * 0.5)
        self._var_xg = gestor.registrar_variable(f"{self.nombre}.x_glucose", min(x_g_in * 1.5, 0.99))

        # 3. Funciones de Residuo (Física)
        def residuo_masa() -> float:
            return mat_in.flujo_masico - (self._var_L.valor + self._var_V.valor)

        def residuo_soluto() -> float:
            w_g_in = self._fraccion_molar_masica(x_g_in)
            w_g_out = self._fraccion_molar_masica(self._var_xg.valor)
            return (mat_in.flujo_masico * w_g_in) - (self._var_L.valor * w_g_out)

        def residuo_energia() -> float:
            # === PROPAGACIÓN DINÁMICA ===
            liq_out.flujo_masico = self._var_L.valor
            vap_out.flujo_masico = self._var_V.valor
            # ============================
            
            liq_out.composicion = {"water": 1.0 - self._var_xg.valor, "glucose": self._var_xg.valor}
            liq_out.presion = self.presion
            termo.simular_mezcla_jarabe(liq_out)

            vap_out.temperatura = liq_out.temperatura
            vap_out.presion = self.presion
            termo.simular_vapor_saturado(vap_out)

            mw_in = self._peso_molecular_aparente(x_g_in)
            mw_L_out = self._peso_molecular_aparente(self._var_xg.valor)
            mw_V_out = 0.018015
            
            flujo_molar_in = mat_in.flujo_masico / mw_in
            flujo_molar_L = self._var_L.valor / mw_L_out
            flujo_molar_V = self._var_V.valor / mw_V_out
            
            Q_in = calor_in.flujo_calor if calor_in else 0.0
            
            H_in_total = (flujo_molar_in * mat_in.entalpia) + Q_in
            H_out_total = (flujo_molar_L * liq_out.entalpia) + (flujo_molar_V * vap_out.entalpia)

            # ESCALADO NUMÉRICO
            return (H_in_total - H_out_total) / 1e6

        # 4. Registrar ecuaciones
        gestor.registrar_residuo(residuo_masa)
        gestor.registrar_residuo(residuo_soluto)
        gestor.registrar_residuo(residuo_energia)

    def aplicar_resultados_finales(
        self, 
        inlets: List[Conexion], 
        outlets: List[Conexion],
        termo: PropSimService
    ) -> None:
        
        liq_out = next(c for c in outlets if isinstance(c, LineaMateria) and c.tipo_conexion == TipoConexion.MATERIA)
        vap_out = next(c for c in outlets if isinstance(c, LineaVapor))

        # 1. Asignar la matemática a las corrientes de salida
        liq_out.flujo_masico = self._var_L.valor
        vap_out.flujo_masico = self._var_V.valor
        liq_out.composicion = {"water": 1.0 - self._var_xg.valor, "glucose": self._var_xg.valor}
        liq_out.presion = self.presion
        
        vap_out.composicion = {"water": 1.0, "glucose": 0.0}
        vap_out.presion = self.presion

        # 2. Cierre termodinámico
        termo.simular_mezcla_jarabe(liq_out)
        vap_out.temperatura = liq_out.temperatura
        termo.simular_vapor_saturado(vap_out)

        # 3. Actualizar el estado interno del propio Evaporador (PropiedadesQuimicas)
        # El volumen de retención asume las propiedades del líquido saliente
        self.temperatura = liq_out.temperatura
        self.composicion = liq_out.composicion
        self.entalpia = liq_out.entalpia
        self.fase = liq_out.fase
    

@dataclass
class Mezclador(Equipo):
    """
    Nodo que une N corrientes de entrada en 1 corriente de salida.
    El cálculo es adiabático (Conservación de Masa, Especies y Energía).
    """
    
    def _fraccion_molar_a_masica(self, x_g: float) -> float:
        mw_w = 0.018015
        mw_g = 0.180156
        x_w = 1.0 - x_g
        masa_total = (x_w * mw_w) + (x_g * mw_g)
        return (x_g * mw_g) / masa_total if masa_total > 0 else 0.0

    def _peso_molecular_aparente(self, x_g: float) -> float:
        return (1.0 - x_g) * 0.018015 + x_g * 0.180156

    def modelar_sistema(
        self, 
        gestor: GestorSistemaEO, 
        inlets: List[Conexion], 
        outlets: List[Conexion], 
        termo: PropSimService
    ) -> None:
        
        # 1. Agrupar dinámicamente TODAS las entradas de materia
        entradas = [c for c in inlets if isinstance(c, LineaMateria)]
        
        # 2. Extraer la única corriente de salida permitida
        salida = next(c for c in outlets if isinstance(c, LineaMateria))

        # Validación térmica inicial (por si las corrientes de entrada vienen "crudas")
        for mat_in in entradas:
            if mat_in.entalpia is None:
                termo.simular_mezcla_jarabe(mat_in)

        # 3. Inscripción de Variables (Salida)
        # Usamos promedios o sumas simples como "guesses" iniciales para ayudar a SciPy
        flujo_in_total_guess = sum(c.flujo_masico for c in entradas)
        
        # Asumimos que la presión de mezcla es la mínima de las presiones entrantes
        self._presion_out = min(c.presion for c in entradas if c.presion is not None)

        self._var_F = gestor.registrar_variable(f"{self.nombre}.flujo_out", flujo_in_total_guess or 100.0)
        self._var_xg = gestor.registrar_variable(f"{self.nombre}.xg_out", 0.05) # Guess por defecto
        self._var_T = gestor.registrar_variable(f"{self.nombre}.T_out", 273.15 + 25.0) # 25°C guess

        # 4. Funciones de Residuo
        def residuo_masa() -> float:
            suma_in = sum(c.flujo_masico for c in entradas)
            return self._var_F.valor - suma_in

        def residuo_soluto() -> float:
            masa_glucosa_in = 0.0
            for c in entradas:
                x_g_in = c.composicion.get("glucose", 0.0)
                masa_glucosa_in += c.flujo_masico * self._fraccion_molar_a_masica(x_g_in)

            w_g_out = self._fraccion_molar_a_masica(self._var_xg.valor)
            masa_glucosa_out = self._var_F.valor * w_g_out
            
            return masa_glucosa_out - masa_glucosa_in

        def residuo_energia() -> float:
            # A) Actualizar el objeto de salida con las variables iteradas por SciPy
            salida.composicion = {"water": 1.0 - self._var_xg.valor, "glucose": self._var_xg.valor}
            salida.presion = self._presion_out
            salida.temperatura = self._var_T.valor
            
            # B) Calcular la entalpía de la salida basada en la T iterada
            termo.simular_mezcla_jarabe(salida)

            # C) Sumatoria de entalpías entrantes vs salientes (en J/h)
            H_in_total = 0.0
            for c in entradas:
                x_g_in = c.composicion.get("glucose", 0.0)
                mw_in = self._peso_molecular_aparente(x_g_in)
                flujo_molar_in = c.flujo_masico / mw_in
                H_in_total += flujo_molar_in * c.entalpia

            mw_out = self._peso_molecular_aparente(self._var_xg.valor)
            flujo_molar_out = self._var_F.valor / mw_out
            H_out_total = flujo_molar_out * salida.entalpia

            return H_out_total - H_in_total

        # 5. Registrar
        gestor.registrar_residuo(residuo_masa)
        gestor.registrar_residuo(residuo_soluto)
        gestor.registrar_residuo(residuo_energia)

    def aplicar_resultados_finales(
        self, 
        inlets: List[Conexion], 
        outlets: List[Conexion],
        termo: PropSimService
    ) -> None:
        
        salida = next(c for c in outlets if isinstance(c, LineaMateria))

        # Fijar valores definitivos
        salida.flujo_masico = self._var_F.valor
        salida.composicion = {"water": 1.0 - self._var_xg.valor, "glucose": self._var_xg.valor}
        salida.temperatura = self._var_T.valor
        salida.presion = self._presion_out
        
        # Último cálculo termo para asegurar consistencia de entalpía final
        termo.simular_mezcla_jarabe(salida)

@dataclass
class FuenteMateria(Equipo, PropiedadesQuimicas):
    flujo_masico: float

    def modelar_sistema(
        self, gestor: GestorSistemaEO, inlets: List[Conexion], outlets: List[Conexion], termo: PropSimService
    ) -> None:
        
        # 1. Simular la fuente reconociendo si es Vapor o Jarabe
        if self.entalpia is None:
            if self.fase == Fase.VAPOR:
                termo.simular_vapor_saturado(self)
            else:
                termo.simular_mezcla_jarabe(self)

        # 2. PROPAGACIÓN TEMPRANA: Rellenamos la "tubería" vacía para el siguiente equipo
        # Así el Condensador o Evaporador encontrarán la tubería con los datos correctos
        mat_out = outlets[0]
        mat_out.flujo_masico = self.flujo_masico
        mat_out.temperatura = self.temperatura
        mat_out.presion = self.presion
        mat_out.composicion = self.composicion
        mat_out.entalpia = self.entalpia
        mat_out.calidad = self.calidad
        mat_out.fase = self.fase

        # 3. Inscripción Numérica
        self._var_F = gestor.registrar_variable(f"{self.nombre}.F_out", self.flujo_masico)
        self._var_T = gestor.registrar_variable(f"{self.nombre}.T_out", self.temperatura)

        def residuo_masa() -> float:
            return self._var_F.valor - self.flujo_masico

        def residuo_energia() -> float:
            # === PROPAGACIÓN DINÁMICA ===
            mat_out.flujo_masico = self._var_F.valor
            mat_out.temperatura = self._var_T.valor
            # ============================
            return self._var_T.valor - self.temperatura

        gestor.registrar_residuo(residuo_masa)
        gestor.registrar_residuo(residuo_energia)

    def aplicar_resultados_finales(
        self, inlets: List[Conexion], outlets: List[Conexion], termo: PropSimService
    ) -> None:
        mat_out = outlets[0]
        mat_out.flujo_masico = self._var_F.valor
        mat_out.temperatura = self._var_T.valor
        mat_out.presion = self.presion
        mat_out.composicion = self.composicion
        mat_out.entalpia = self.entalpia


# =====================================================================
# 2. PURGA DE MATERIA (Boundary Condition - Salida)
# =====================================================================
@dataclass
class PurgaMateria(Equipo):
    """
    Nodo sumidero. Cierra el grafo de NetworkX recibiendo las corrientes finales.
    No genera ecuaciones ni variables porque no añade restricciones físicas al sistema.
    """
    def modelar_sistema(
        self, gestor: GestorSistemaEO, inlets: List[Conexion], outlets: List[Conexion], termo: PropSimService
    ) -> None:
        # Un sumidero simplemente absorbe los valores convergidos por los equipos anteriores.
        pass

    def aplicar_resultados_finales(
        self, inlets: List[Conexion], outlets: List[Conexion], termo: PropSimService
    ) -> None:
        # Aquí se podrían registrar métricas o logs de lo que salió de la planta.
        pass


# =====================================================================
# 3. VÁLVULA DE PRESIÓN / EXPANSIÓN
# =====================================================================
@dataclass
class Valvula(Equipo):
    """
    Válvula de expansión isentálpica.
    Reduce la presión del fluido. Si la caída de presión es drástica, 
    parte del líquido destellará (flasheo), lo cual será capturado por la Termodinámica.
    """
    presion_salida: float

    def modelar_sistema(
        self, gestor: GestorSistemaEO, inlets: List[Conexion], outlets: List[Conexion], termo: PropSimService
    ) -> None:
        mat_in = next(c for c in inlets if isinstance(c, LineaMateria))
        mat_out = next(c for c in outlets if isinstance(c, LineaMateria))

        if mat_in.entalpia is None:
            # --- INYECCIÓN DE SEMILLAS (Defensa EO) ---
            if mat_in.presion is None and mat_in.temperatura is None:
                mat_in.presion = 101325.0
                mat_in.temperatura = 273.15 + 80.0
            if mat_in.composicion is None:
                mat_in.composicion = {"water": 0.95, "glucose": 0.05}
            if mat_in.flujo_masico == 0.0 or mat_in.flujo_masico is None:
                mat_in.flujo_masico = 1000.0
            # ------------------------------------------
            termo.simular_mezcla_jarabe(mat_in)

        # Variables: Asumimos que la masa no cambia, solo buscamos la nueva Temperatura
        self._var_F = gestor.registrar_variable(f"{self.nombre}.F_out", mat_in.flujo_masico)
        self._var_T = gestor.registrar_variable(f"{self.nombre}.T_out", mat_in.temperatura)

        def residuo_masa() -> float:
            return self._var_F.valor - mat_in.flujo_masico

        def residuo_energia() -> float:
            # === PROPAGACIÓN DINÁMICA ===
            mat_out.flujo_masico = self._var_F.valor
            # ============================
            
            mat_out.presion = self.presion_salida
            mat_out.temperatura = self._var_T.valor
            mat_out.composicion = mat_in.composicion
            
            termo.simular_mezcla_jarabe(mat_out)
            
            # ESCALADO NUMÉRICO
            return (mat_out.entalpia - mat_in.entalpia) / 1e3

        gestor.registrar_residuo(residuo_masa)
        gestor.registrar_residuo(residuo_energia)

    def aplicar_resultados_finales(
        self, inlets: List[Conexion], outlets: List[Conexion], termo: PropSimService
    ) -> None:
        mat_in = next(c for c in inlets if isinstance(c, LineaMateria))
        mat_out = next(c for c in outlets if isinstance(c, LineaMateria))

        mat_out.flujo_masico = self._var_F.valor
        mat_out.presion = self.presion_salida
        mat_out.temperatura = self._var_T.valor
        mat_out.composicion = mat_in.composicion
        termo.simular_mezcla_jarabe(mat_out)


# =====================================================================
# 4. INTERCAMBIADOR DE CALOR (Condensador / Suministro)
# =====================================================================
@dataclass
class IntercambiadorCalor(Equipo):
    """
    Condensador de servicio térmico. 
    Toma vapor saturado, lo condensa a líquido saturado y exporta el calor latente liberado.
    """
    def modelar_sistema(
        self, gestor: GestorSistemaEO, inlets: List[Conexion], outlets: List[Conexion], termo: PropSimService
    ) -> None:
        # Entradas y Salidas
        vap_in = next(c for c in inlets if isinstance(c, LineaVapor))
        liq_out = next(c for c in outlets if isinstance(c, LineaMateria))
        calor_out = next(c for c in outlets if isinstance(c, Calor))

        if vap_in.entalpia is None:
            # --- INYECCIÓN DE SEMILLAS (Defensa EO) ---
            if vap_in.presion is None and vap_in.temperatura is None:
                vap_in.presion = 101325.0
            if vap_in.flujo_masico == 0.0 or vap_in.flujo_masico is None:
                vap_in.flujo_masico = 1000.0
            # ------------------------------------------
            termo.simular_vapor_saturado(vap_in)

        # Inicializamos el guess del calor liberado en 1 millón de Joules
        guess_q_MW = (vap_in.flujo_masico * 2.2) if vap_in.flujo_masico > 0 else 1000.0
        self._var_Q_MW = gestor.registrar_variable(f"{self.nombre}.Q_lib_MW", guess_q_MW)

        def residuo_energia() -> float:
            # === PROPAGACIÓN DINÁMICA ===
            liq_out.flujo_masico = vap_in.flujo_masico
            # ============================
            
            liq_out.presion = vap_in.presion
            liq_out.calidad = 0.0 
            termo.simular_agua_saturada(liq_out)

            # Desescalamos a Joules solo para el balance térmico de las tuberías
            Q_real = self._var_Q_MW.valor * 1e6
            calor_out.flujo_calor = Q_real

            mw_w = 0.018015
            flujo_molar = vap_in.flujo_masico / mw_w

            H_in = flujo_molar * vap_in.entalpia
            H_out = flujo_molar * liq_out.entalpia

            # ESCALADO NUMÉRICO
            return (H_in - H_out - Q_real) / 1e6

        # Nota: Como el flujo es 1 a 1, no necesitamos un residuo de masa, 
        # pasamos el flujo directo en los cálculos. Solo resolvemos la energía.
        gestor.registrar_residuo(residuo_energia)

    def aplicar_resultados_finales(
        self, inlets: List[Conexion], outlets: List[Conexion], termo: PropSimService
    ) -> None:
        vap_in = next(c for c in inlets if isinstance(c, LineaVapor))
        liq_out = next(c for c in outlets if isinstance(c, LineaMateria))
        calor_out = next(c for c in outlets if isinstance(c, Calor))

        # El flujo másico y la composición del agua se conservan intactos
        liq_out.flujo_masico = vap_in.flujo_masico
        liq_out.composicion = vap_in.composicion
        liq_out.presion = vap_in.presion
        liq_out.calidad = 0.0
        
        termo.simular_agua_saturada(liq_out)

        # Traspasamos la energía calculada al enlace de calor
        calor_out.flujo_calor = self._var_Q_MW.valor * 1e6