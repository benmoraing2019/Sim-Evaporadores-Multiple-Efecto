"""
Zona de pruebas para entender como funciona phasepy
"""

from phasepy import component, mixture, virialgamma
import numpy as np

class PruebaServicio:
    def __init__(self):

        self.agua = None
        self.sacarosa = None
        self.mezcla = None
        self.modelo_eq = None
        pass
    def inicializa_componentes(self):
        self.agua = component(
            name='water',
            Tc=647.13, Pc=220.55, Zc=0.229, Vc=55.948, w=0.344861,
            Ant=[11.64785144, 3797.41566067, -46.77830444],
            GC={'H2O': 1}  # No se usará con NRTL, pero no estorba
        )

        # --- Sacarosa ---
        # Propiedades críticas de la literatura (Tc, Vc) y estimadas (Pc, w).
        # Constantes de Antoine "dummy" para que su Psat sea ~0 (no volátil).
        self.sacarosa = component(
            name='sucrose',
            Tc=1782.70, Pc=25.0, Vc=784.0, w=1.0,
            Ant=[10.0, 10000.0, 0.0],  # Psat ≈ 5e-8 bar a 373 K
            GC={}  # No se usará con NRTL
        )

        return

    def inicia_mezcla(self):

        self.mezcla = mixture(self.agua, self.sacarosa)
        alpha = np.array([[0.0, 0.3],
                  [0.3, 0.0]])

        # g: parámetros de energía de interacción (en K)
        # g[0,1] = interacción agua-sacarosa; g[1,0] = sacarosa-agua
        g = np.array([[0.0, 500.0],
                      [-200.0, 0.0]])

        # g1: dependencia con la temperatura (aquí nula)
        g1 = np.array([[0.0, 0.0],
                       [0.0, 0.0]])

        # Asignar el modelo NRTL a la mezcla
        self.mezcla.NRTL(alpha, g, g1)

        self.modelo_eq = virialgamma(self.mezcla, actmodel="nrtl")
       


if __name__ == "__main__":
    p1 = PruebaServicio()
    p1.inicializa_componentes()
    p1.inicia_mezcla()