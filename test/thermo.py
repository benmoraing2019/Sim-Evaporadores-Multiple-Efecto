"""
Sistema de pruebas del modelo predictivo de sustancias quimicas agua y azucar
"""

from thermo import Chemical

def prueba_uso():
    agua = Chemical("water")

    P_evap = 101325
    T_sat = agua.Tsat(P_evap)
    print(T_sat)

if __name__ == "__main__":
    prueba_uso()