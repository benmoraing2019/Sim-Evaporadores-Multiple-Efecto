"""
Pruebas de conexión y topología de la red de proceso (networkx).

Cubre:
  - validación de Composicion
  - identidad y códigos de Puerto
  - registro de puertos en Equipo
  - reglas de conexión (materia / energía)
  - errores de conexión (puerto inexistente, dirección, tipo, doble conexión)
  - orden de resolución topológico
  - detección de ciclos y agrupación en bloques
  - validación global de la red
  - serialización a dict

Ejecutar con:
    python -m pytest test/test_network.py -v
"""

from __future__ import annotations

import json

import networkx as nx
import pytest

from core.schemas.base import (
    Composicion,
    Direccion,
    Equipo,
    Fase,
    Puerto,
    TipoFlujo,
)
from core.schemas.engine import (
    Divisor,
    Evaporador,
    Fuente,
    IntercambiadorCalor,
    Sumidero,
)
from core.schemas.network import RedProceso
from core.schemas.streams import CargaTermica, Corriente


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
COMP = Composicion(fracciones={"water": 0.95, "glucose": 0.05})


def corriente(nombre: str = "S1", fase: Fase = Fase.LIQUIDO, T: float = 373.0,
              P: float = 1.0e5, F: float = 1.0) -> Corriente:
    return Corriente(nombre=nombre, comp=COMP, temperatura=T, presion=P,
                     flujo_masico=F, fase=fase)


def red_triple_efecto() -> RedProceso:
    """Misma red que main.py, pero sin depender del script."""
    red = RedProceso()

    ev = [
        Evaporador(nombre=f"E-10{i}", puertos=Evaporador.puertos_estandar(),
                   presion_operacion=p)
        for i, p in zip((1, 2, 3), (1.0e5, 5.0e4, 2.0e4))
    ]
    ic = [
        IntercambiadorCalor(nombre=f"IC-10{i}",
                            puertos=IntercambiadorCalor.puertos_estandar(),
                            area=50.0, coeficiente_global=900.0)
        for i in (1, 2, 3)
    ]
    red.agregar(*ev, *ic)

    red.conectar_energia("IC-101", "q", "E-101", "q", CargaTermica(nombre="Q1"))
    red.conectar_materia("E-101", "vapor", "IC-102", "entrada_caliente",
                         corriente("V1", fase=Fase.VAPOR))
    red.conectar_energia("IC-102", "q", "E-102", "q", CargaTermica(nombre="Q2"))
    red.conectar_materia("E-102", "vapor", "IC-103", "entrada_caliente",
                         corriente("V2", fase=Fase.VAPOR))
    red.conectar_energia("IC-103", "q", "E-103", "q", CargaTermica(nombre="Q3"))
    red.conectar_materia("E-101", "liquido", "E-102", "alimentacion",
                         corriente("L1"))
    red.conectar_materia("E-102", "liquido", "E-103", "alimentacion",
                         corriente("L2"))
    return red


def red_completa() -> RedProceso:
    """Red de 2 efectos con todos los puertos conectados (fuentes y sumideros)."""
    red = RedProceso()

    f1, f2 = Fuente(nombre="F1", puertos=Fuente.puertos_estandar()), \
             Fuente(nombre="F2", puertos=Fuente.puertos_estandar())
    s1, s2 = Sumidero(nombre="S1", puertos=Sumidero.puertos_estandar()), \
             Sumidero(nombre="S2", puertos=Sumidero.puertos_estandar())
    s3, s4 = Sumidero(nombre="S3", puertos=Sumidero.puertos_estandar()), \
             Sumidero(nombre="S4", puertos=Sumidero.puertos_estandar())

    e1 = Evaporador(nombre="E-101", puertos=Evaporador.puertos_estandar(),
                    presion_operacion=1.0e5)
    e2 = Evaporador(nombre="E-102", puertos=Evaporador.puertos_estandar(),
                    presion_operacion=5.0e4)
    ic1 = IntercambiadorCalor(nombre="IC-101",
                              puertos=IntercambiadorCalor.puertos_estandar(),
                              area=50.0, coeficiente_global=900.0)
    ic2 = IntercambiadorCalor(nombre="IC-102",
                              puertos=IntercambiadorCalor.puertos_estandar(),
                              area=50.0, coeficiente_global=900.0)

    red.agregar(f1, f2, s1, s2, s3, s4, e1, e2, ic1, ic2)

    red.conectar_materia("F1", "salida", "IC-101", "entrada_caliente",
                         corriente("VC", fase=Fase.VAPOR))
    red.conectar_energia("IC-101", "q", "E-101", "q", CargaTermica("Q1"))
    red.conectar_materia("IC-101", "condensado", "S1", "entrada",
                         corriente("C1"))
    red.conectar_materia("F2", "salida", "E-101", "alimentacion",
                         corriente("ALIM"))

    red.conectar_materia("E-101", "vapor", "IC-102", "entrada_caliente",
                         corriente("V1", fase=Fase.VAPOR))
    red.conectar_energia("IC-102", "q", "E-102", "q", CargaTermica("Q2"))
    red.conectar_materia("IC-102", "condensado", "S2", "entrada",
                         corriente("C2"))
    red.conectar_materia("E-101", "liquido", "E-102", "alimentacion",
                         corriente("L1"))
    red.conectar_materia("E-102", "vapor", "S3", "entrada",
                         corriente("V2", fase=Fase.VAPOR))
    red.conectar_materia("E-102", "liquido", "S4", "entrada",
                         corriente("L2"))
    return red


# --------------------------------------------------------------------------
# 1. Composicion
# --------------------------------------------------------------------------
class TestComposicion:
    def test_suma_uno_es_valida(self):
        c = Composicion(fracciones={"water": 0.5, "glucose": 0.5})
        assert c.componentes() == ["water", "glucose"]
        assert c.valores() == [0.5, 0.5]

    def test_suma_distinta_de_uno_falla(self):
        with pytest.raises(ValueError, match="sumar 1.0"):
            Composicion(fracciones={"a": 0.5, "b": 0.4})

    def test_fraccion_negativa_falla(self):
        with pytest.raises(ValueError, match="negativas"):
            Composicion(fracciones={"a": 1.5, "b": -0.5})

    def test_composicion_vacia_falla(self):
        with pytest.raises(ValueError, match="vacía"):
            Composicion(fracciones={})

    def test_es_inmutable(self):
        c = Composicion(fracciones={"a": 1.0})
        with pytest.raises(Exception):
            c.fracciones = {}  # type: ignore[misc]


# --------------------------------------------------------------------------
# 2. Puerto
# --------------------------------------------------------------------------
class TestPuerto:
    def test_codigo_sin_padre_falla(self):
        p = Puerto(nombre="in", direccion=Direccion.ENTRADA)
        with pytest.raises(RuntimeError, match="no pertenece"):
            _ = p.codigo

    def test_codigo_derivado_del_equipo(self):
        p = Puerto(nombre="in", direccion=Direccion.ENTRADA)
        EquipoDemo = type("EquipoDemo", (Equipo,), {"calcular": lambda self: None})
        eq = EquipoDemo.__new__(EquipoDemo)
        eq.nombre = "X-1"
        eq.puertos = [p]
        eq.__post_init__()
        assert p.codigo == "X-1.in"

    def test_conectado_por_defecto_falso(self):
        assert Puerto(nombre="in", direccion=Direccion.ENTRADA).conectado is False


# --------------------------------------------------------------------------
# 3. Equipo
# --------------------------------------------------------------------------
class TestEquipo:
    def test_puertos_registrados_con_padre(self):
        e = Evaporador(nombre="E-1", puertos=Evaporador.puertos_estandar(),
                       presion_operacion=1.0e5)
        nombres = [p.nombre for p in e.puertos]
        assert nombres == ["alimentacion", "q", "vapor", "liquido"]
        assert all(p.codigo.startswith("E-1.") for p in e.puertos)

    def test_busqueda_por_nombre_y_tipo(self):
        e = Evaporador(nombre="E-1", puertos=Evaporador.puertos_estandar(),
                       presion_operacion=1.0e5)
        assert e.puerto("q", TipoFlujo.ENERGIA).tipo is TipoFlujo.ENERGIA
        assert e.puerto("vapor").direccion is Direccion.SALIDA

    def test_puerto_inexistente_falla(self):
        e = Evaporador(nombre="E-1", puertos=Evaporador.puertos_estandar(),
                       presion_operacion=1.0e5)
        with pytest.raises(KeyError):
            e.puerto("no_existe")

    def test_puertos_de_filtra_por_tipo(self):
        e = Evaporador(nombre="E-1", puertos=Evaporador.puertos_estandar(),
                       presion_operacion=1.0e5)
        assert len(e.puertos_de(TipoFlujo.MATERIA)) == 3
        assert len(e.puertos_de(TipoFlujo.ENERGIA)) == 1

    def test_puerto_duplicado_falla(self):
        puertos = [Puerto(nombre="in", direccion=Direccion.ENTRADA),
                   Puerto(nombre="in", direccion=Direccion.ENTRADA)]
        with pytest.raises(ValueError, match="duplicado"):
            Fuente(nombre="F", puertos=puertos)

    def test_puerto_ya_usado_por_otro_equipo_falla(self):
        p = Puerto(nombre="in", direccion=Direccion.ENTRADA)
        Fuente(nombre="F1", puertos=[p])
        with pytest.raises(ValueError, match="ya pertenece"):
            Fuente(nombre="F2", puertos=[p])

    def test_nombre_duplicado_en_red_falla(self):
        red = RedProceso()
        red.agregar(Fuente(nombre="F1", puertos=Fuente.puertos_estandar()))
        with pytest.raises(ValueError, match="ya existe"):
            red.agregar(Fuente(nombre="F1", puertos=Fuente.puertos_estandar()))


# --------------------------------------------------------------------------
# 4. Conexiones correctas
# --------------------------------------------------------------------------
class TestConexiones:
    def test_conexion_materia_crea_arista(self):
        red = red_completa()
        assert red.g.has_edge("E-101", "E-102")
        data = red.g["E-101"]["E-102"]["E-101.liquido"]
        assert data["tipo"] == TipoFlujo.MATERIA.value
        assert data["puerto_destino"] == "alimentacion"

    def test_conexion_energia_crea_arista(self):
        red = red_completa()
        data = red.g["IC-101"]["E-101"]["IC-101.q"]
        assert data["tipo"] == TipoFlujo.ENERGIA.value
        assert data["puerto_destino"] == "q"

    def test_conexion_marca_ambos_puertos(self):
        red = red_completa()
        e1: Evaporador = red.g.nodes["E-101"]["equipo"]
        ic1: IntercambiadorCalor = red.g.nodes["IC-101"]["equipo"]
        assert e1.puerto("q", TipoFlujo.ENERGIA).conectado
        assert ic1.puerto("q", TipoFlujo.ENERGIA).conectado
        assert e1.puerto("q", TipoFlujo.ENERGIA).conexion == ("IC-101", "q")

    def test_aristas_energia_listadas(self):
        red = red_completa()
        aristas = red.aristas_energia()
        pares = {(u, v) for u, v, _ in aristas}
        assert pares == {("IC-101", "E-101"), ("IC-102", "E-102")}
        assert all(isinstance(q, CargaTermica) for _, _, q in aristas)


# --------------------------------------------------------------------------
# 5. Errores de conexión
# --------------------------------------------------------------------------
class TestErroresDeConexion:
    def _red_simple(self) -> RedProceso:
        red = RedProceso()
        red.agregar(
            Fuente(nombre="F", puertos=Fuente.puertos_estandar()),
            IntercambiadorCalor(nombre="IC",
                                puertos=IntercambiadorCalor.puertos_estandar(),
                                area=1.0, coeficiente_global=1.0),
            Evaporador(nombre="E", puertos=Evaporador.puertos_estandar(),
                       presion_operacion=1.0e5),
        )
        return red

    def test_equipo_inexistente(self):
        red = self._red_simple()
        with pytest.raises(KeyError, match="deben existir"):
            red.conectar_materia("F", "salida", "NO_EXISTE", "alimentacion",
                                 corriente())

    def test_puerto_inexistente_en_destino(self):
        red = self._red_simple()
        with pytest.raises(KeyError, match="no tiene un puerto"):
            red.conectar_materia("F", "salida", "E", "no_existe", corriente())

    def test_tipo_de_flujo_incorrecto(self):
        red = self._red_simple()
        # 'q' es de ENERGIA, no existe como MATERIA -> KeyError
        with pytest.raises(KeyError):
            red.conectar_materia("F", "salida", "E", "q", corriente())

    def test_origen_no_es_salida(self):
        red = self._red_simple()
        with pytest.raises(ValueError, match="no es un puerto de salida"):
            red.conectar_materia("E", "alimentacion", "IC", "entrada_caliente",
                                 corriente())

    def test_destino_no_es_entrada(self):
        red = self._red_simple()
        with pytest.raises(ValueError, match="no es un puerto de entrada"):
            red.conectar_materia("F", "salida", "E", "vapor", corriente())

    def test_doble_conexion_del_mismo_puerto(self):
        red = self._red_simple()
        red.conectar_materia("F", "salida", "IC", "entrada_caliente",
                             corriente())
        with pytest.raises(ValueError, match="ya está conectado"):
            red.conectar_materia("F", "salida", "E", "alimentacion",
                                 corriente())

    def test_destino_ya_conectado(self):
        red = self._red_simple()
        red.agregar(Fuente(nombre="F2", puertos=Fuente.puertos_estandar()))
        red.conectar_materia("F", "salida", "E", "alimentacion", corriente())
        with pytest.raises(ValueError, match="ya está conectado"):
            red.conectar_materia("F2", "salida", "E", "alimentacion",
                                 corriente())


# --------------------------------------------------------------------------
# 6. Topología
# --------------------------------------------------------------------------
class TestTopologia:
    def test_orden_resolucion_triple_efecto(self):
        red = red_triple_efecto()
        orden = [(type(eq).__name__, eq.nombre) for eq in red.orden_resolucion()]
        assert orden == [
            ("IntercambiadorCalor", "IC-101"),
            ("Evaporador", "E-101"),
            ("IntercambiadorCalor", "IC-102"),
            ("Evaporador", "E-102"),
            ("IntercambiadorCalor", "IC-103"),
            ("Evaporador", "E-103"),
        ]

    def test_sucesores_y_predecesores(self):
        red = red_triple_efecto()
        assert set(red.sucesores("E-101")) == {"IC-102", "E-102"}
        assert set(red.predecesores("E-102")) == {"IC-102", "E-101"}

    def test_orden_respetas_dependencias_energia(self):
        red = red_completa()
        pos = {eq.nombre: i for i, eq in enumerate(red.orden_resolucion())}
        # el intercambiador debe resolverse antes que el evaporador que alimenta
        assert pos["IC-101"] < pos["E-101"]
        assert pos["IC-102"] < pos["E-102"]

    def test_ciclo_detectado_en_alimentacion_inversa(self):
        red = red_triple_efecto()
        # licor en contracorriente: E-103 -> E-101 cierra el ciclo
        red.conectar_materia("E-103", "liquido", "E-101", "alimentacion",
                             corriente("L3"))
        with pytest.raises(ValueError, match="ciclo"):
            red.orden_resolucion()

    def test_bloques_agrupa_componente_fuerte(self):
        red = red_triple_efecto()
        red.conectar_materia("E-103", "liquido", "E-101", "alimentacion",
                             corriente("L3"))
        bloques = [[eq.nombre for eq in b] for b in red.bloques()]
        planos = [n for b in bloques for n in b]
        assert set(planos) == {f"E-10{i}" for i in (1, 2, 3)} | {
            f"IC-10{i}" for i in (1, 2, 3)
        }
        # El lazo de licor arrastra también los intercambiadores de los
        # efectos intermedios: E-101->IC-102->E-102->IC-103->E-103->E-101
        ciclo = [b for b in bloques if len(b) > 1]
        assert len(ciclo) == 1
        assert set(ciclo[0]) == {"E-101", "E-102", "E-103", "IC-102", "IC-103"}
        # IC-101 queda fuera porque alimenta el lazo pero no depende de él
        assert bloques[0] == ["IC-101"]

    def test_grafo_es_dag_sin_reciclo(self):
        red = red_triple_efecto()
        assert nx.is_directed_acyclic_graph(red.g)

    def test_es_multidigrafo(self):
        assert isinstance(red_triple_efecto().g, nx.MultiDiGraph)


# --------------------------------------------------------------------------
# 7. Validación global
# --------------------------------------------------------------------------
class TestValidacion:
    def test_red_completa_sin_problemas(self):
        assert red_completa().validar() == []

    def test_red_incompleta_reporta_puertos(self):
        problemas = red_triple_efecto().validar()
        assert any("Puerto sin conectar" in p for p in problemas)
        assert any("E-101.alimentacion" in p for p in problemas)

    def test_red_disconexa_reportada(self):
        red = RedProceso()
        red.agregar(
            Fuente(nombre="F1", puertos=Fuente.puertos_estandar()),
            Fuente(nombre="F2", puertos=Fuente.puertos_estandar()),
        )
        assert any("débilmente conexo" in p for p in red.validar())


# --------------------------------------------------------------------------
# 8. Fronteras: Fuente / Sumidero
# --------------------------------------------------------------------------
class TestFuenteSumidero:
    def test_fuente_genera_puerto_salida(self):
        f = Fuente(nombre="F")
        assert [p.nombre for p in f.puertos] == ["salida"]
        assert f.puertos[0].direccion is Direccion.SALIDA
        assert f.puertos[0].tipo is TipoFlujo.MATERIA
        assert f.puertos[0].codigo == "F.salida"

    def test_sumidero_genera_puerto_entrada(self):
        s = Sumidero(nombre="S")
        assert [p.nombre for p in s.puertos] == ["entrada"]
        assert s.puertos[0].direccion is Direccion.ENTRADA
        assert s.puertos[0].codigo == "S.entrada"

    def test_fuente_no_tiene_entradas(self):
        assert Fuente(nombre="F").puertos_de(TipoFlujo.MATERIA)[0].direccion \
            is Direccion.SALIDA
        assert all(p.direccion is Direccion.SALIDA
                   for p in Fuente(nombre="F").puertos)

    def test_sumidero_no_tiene_salidas(self):
        assert all(p.direccion is Direccion.ENTRADA
                   for p in Sumidero(nombre="S").puertos)

    def test_calcular_es_no_op(self):
        assert Fuente(nombre="F").calcular() is None
        assert Sumidero(nombre="S").calcular() is None

    def test_puertos_personalizados_no_se_sobrescriben(self):
        f = Fuente(nombre="F", puertos=[Puerto(nombre="feed",
                                              direccion=Direccion.SALIDA)])
        assert [p.nombre for p in f.puertos] == ["feed"]

    def test_no_exponen_corriente(self):
        # el estado vive en la arista, no en la frontera (evita duplicidad)
        assert not hasattr(Fuente(nombre="F"), "corriente")
        assert not hasattr(Sumidero(nombre="S"), "corriente")

    def test_red_con_fronteras_valida(self):
        assert red_completa().validar() == []

    def test_frontera_cierra_red_disconexa(self):
        red = RedProceso()
        f = Fuente(nombre="F")
        s = Sumidero(nombre="S")
        red.agregar(f, s)
        red.conectar_materia("F", "salida", "S", "entrada", corriente())
        assert red.validar() == []
        assert red.orden_resolucion() == [f, s]


# --------------------------------------------------------------------------
# 9. Divisor
# --------------------------------------------------------------------------
class TestDivisor:
    def test_puertos_autogenerados(self):
        d = Divisor(nombre="D", n_salidas=3)
        assert [p.nombre for p in d.puertos] == \
            ["entrada", "salida_0", "salida_1", "salida_2"]

    def test_puertos_estandar_dos_salidas(self):
        assert [p.nombre for p in Divisor.puertos_estandar()] == \
            ["entrada", "salida_0", "salida_1"]

    def test_reparte_a_dos_sumideros(self):
        red = RedProceso()
        d, s1, s2 = Divisor(nombre="D"), Sumidero(nombre="S1"), Sumidero(nombre="S2")
        red.agregar(d, s1, s2)
        red.conectar_materia("D", "salida_0", "S1", "entrada", corriente("a"))
        red.conectar_materia("D", "salida_1", "S2", "entrada", corriente("b"))
        assert red.g.out_degree("D") == 2
        assert set(red.sucesores("D")) == {"S1", "S2"}


# --------------------------------------------------------------------------
# 10. Serialización
# --------------------------------------------------------------------------
class TestSerializacion:
    def test_a_dict_es_json_serializable(self):
        d = red_completa().a_dict()
        texto = json.dumps(d)  # no debe lanzar
        assert len(d["nodos"]) == 10
        assert len(d["aristas"]) == 10
        assert texto

    def test_a_dict_convierte_enums(self):
        d = red_completa().a_dict()
        tipos = {a["tipo"] for a in d["aristas"]}
        assert tipos == {"materia", "energia"}
        fases = {a["flujo"].get("fase") for a in d["aristas"]}
        assert fases <= {"LIQUIDO", "VAPOR", "BIFASICO", None}
