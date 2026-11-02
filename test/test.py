"""
Zona de pruebas y experimentaciónd de los Scripts ocuapados
"""

from core.services.ecuaciones_manager import VariableSolver, GestorSistemaEO

from scipy.optimize import root
import numpy as np

class DivisorPrueba:
    """
    Clase de pruebas para usarlo en un sistema tipo divisor
    """

    def __init__(self):

        self.flujo_in = 100.0

        self.var_A = None
        self.var_B = None

    def modelar_sistema(self, gestor:GestorSistemaEO):

        self.var_A = gestor.registrar_variable("Flujo_A", 50.0)
        self.var_B = gestor.registrar_variable("Flujo_B", 50.0)

        def residuo_masa():
            return self.flujo_in - (self.var_A.valor + self.var_B.valor)

        def residuo_condicion_operativa():
            return self.var_A.valor - (2.0*self.var_B.valor)

        gestor.registrar_residuo(residuo_masa)
        gestor.registrar_residuo(residuo_condicion_operativa)

if __name__ == "__main__":

    print("Iniciando pruebas de comprobación de clases")

    gestor = GestorSistemaEO()
    equipo = DivisorPrueba()


    equipo.modelar_sistema(gestor=gestor)

    print(f"\nVector inicial (x0) extraído para SciPy: {gestor.get_array()}")

    print("Iniciando analisis por Root")

    solucion = root(
        fun=gestor.evaluar_sistema,
        x0=gestor.get_array(),
        method="hybr"
    )

    if solucion.success:
        print("\n✅ ¡Convergencia exitosa!")
        print(f"Mensaje de SciPy: {solucion.message}")
        print(f"Vector final devuelto por SciPy: {solucion.x}")
        
        # 5. La prueba de fuego: ¿Se actualizaron las variables dentro del equipo automáticamente?
        # Para que el sistema funcione (100 = A + B y A = 2*B), la respuesta exacta es A=66.666... y B=33.333...
        print("\n--- Lectura directa desde el Equipo (Magia de Referencias) ---")
        print(f"Valor final Flujo_A (var_A.valor): {equipo.var_A.valor:.4f}")
        print(f"Valor final Flujo_B (var_B.valor): {equipo.var_B.valor:.4f}")
        
    else:
        print("\n❌ Fallo en la convergencia.")
        print(solucion.message)



    
