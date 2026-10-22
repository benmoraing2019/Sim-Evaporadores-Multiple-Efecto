from thermo import ChemicalConstantsPackage, Mixture
from thermo.nrtl import NRTL
from thermo import CEOSGas

sustancias = ["water", "acetone"]
fracciones_molar = [0.6, 0.4]

# 1. Al pasar una lista, constants es una TUPLA de objetos individuales
constants = ChemicalConstantsPackage.from_IDs(sustancias)

# 2. Extraemos los valores en formato de lista iterando sobre la tupla
tcs = [c.Tc for c in constants]
pcs = [c.Pc for c in constants]
omegas = [c.omega for c in constants]
heat_caps = [c.Cpg for c in constants]
cas_list = [c.CAS for c in constants]

# 3. Instanciamos NRTL con las listas extraídas
nrtl_liquid = NRTL(
    Tcs=tcs,
    Pcs=pcs,
    omegas=omegas
)

gas_model = CEOSGas(
    {'Tcs': tcs, 'Pcs': pcs, 'omegas': omegas},
    HeatCapacityGases=heat_caps
)

# 4. Construimos la mezcla
mix = Mixture(
    constants=constants, # Mixture sí acepta la tupla directamente aquí
    properties=constants,
    liquid=nrtl_liquid,
    gas=gas_model,
    CASs=cas_list,
    zs=fracciones_molar,
    T=330.15,
    P=101325.0
)

print("¡Modelo NRTL inicializado y calculado con éxito!")
print(f"Fase líquida activa: {type(mix.liquid).__name__}")
print(f"Entalpía molar: {mix.H:.2f} J/mol")