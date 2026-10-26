"""Red de proceso: envoltura tipada sobre nx.MultiDiGraph."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

import networkx as nx

from core.schemas.base import Direccion, Equipo, TipoFlujo
from core.schemas.streams import CargaTermica, Corriente

Flujo = Corriente | CargaTermica


class RedProceso:
    """
    Nodos  = equipos (id = equipo.nombre)
    Aristas = flujos, con 'tipo' en {"materia", "energia"}
    """

    def __init__(self) -> None:
        self.g: nx.MultiDiGraph = nx.MultiDiGraph()

    # ---------------- construcción ------------------------------------
    def agregar(self, *equipos: Equipo) -> None:
        for eq in equipos:
            if eq.nombre in self.g:
                raise ValueError(f"El equipo '{eq.nombre}' ya existe en la red")
            self.g.add_node(eq.nombre, equipo=eq, tipo=type(eq).__name__)

    def conectar_materia(
        self, origen: str, puerto_origen: str,
        destino: str, puerto_destino: str,
        corriente: Corriente,
    ) -> None:
        self._conectar(origen, puerto_origen, destino, puerto_destino,
                       corriente, TipoFlujo.MATERIA)

    def conectar_energia(
        self, origen: str, puerto_origen: str,
        destino: str, puerto_destino: str,
        carga: CargaTermica,
    ) -> None:
        self._conectar(origen, puerto_origen, destino, puerto_destino,
                       carga, TipoFlujo.ENERGIA)

    def _conectar(self, o: str, po_nombre: str, d: str, pd_nombre: str,
                  flujo: Flujo, tipo: TipoFlujo) -> None:
        if o not in self.g or d not in self.g:
            raise KeyError("Ambos equipos deben existir en la red antes de conectar")

        eq_o: Equipo = self.g.nodes[o]["equipo"]
        eq_d: Equipo = self.g.nodes[d]["equipo"]
        po = eq_o.puerto(po_nombre, tipo)
        pd = eq_d.puerto(pd_nombre, tipo)

        if po.direccion is not Direccion.SALIDA:
            raise ValueError(f"'{po.codigo}' no es un puerto de salida")
        if pd.direccion is not Direccion.ENTRADA:
            raise ValueError(f"'{pd.codigo}' no es un puerto de entrada")
        if po.conectado:
            raise ValueError(f"'{po.codigo}' ya está conectado")
        if pd.conectado:
            raise ValueError(f"'{pd.codigo}' ya está conectado")

        self.g.add_edge(
            o, d,
            key=po.codigo,                 # key única por puerto de salida
            flujo=flujo,
            tipo=tipo.value,
            puerto_origen=po_nombre,
            puerto_destino=pd_nombre,
        )
        po.conexion = (d, pd_nombre)
        pd.conexion = (o, po_nombre)

    # ---------------- análisis topológico ------------------------------
    def orden_resolucion(self) -> list[Equipo]:
        if not nx.is_directed_acyclic_graph(self.g):
            ciclos = list(nx.simple_cycles(self.g))
            raise ValueError(f"La red tiene {len(ciclos)} ciclo(s); usa 'bloques()'. Ej: {ciclos[:3]}")
        return [self.g.nodes[n]["equipo"] for n in nx.topological_sort(self.g)]

    def bloques(self) -> list[list[Equipo]]:
        """Componentes fuertemente conexas, en orden de resolución."""
        cond = nx.condensation(self.g)
        resultado = []
        for nodo in nx.topological_sort(cond):
            miembros = cond.nodes[nodo]["members"]
            resultado.append([self.g.nodes[m]["equipo"] for m in miembros])
        return resultado

    def sucesores(self, nombre: str) -> list[str]:
        return list(self.g.successors(nombre))

    def predecesores(self, nombre: str) -> list[str]:
        return list(self.g.predecessors(nombre))

    def aristas_energia(self) -> list[tuple[str, str, CargaTermica]]:
        return [
            (u, v, data["flujo"])
            for u, v, data in self.g.edges(data=True)
            if data["tipo"] == TipoFlujo.ENERGIA.value
        ]

    # ---------------- validación ----------------------------------------
    def validar(self) -> list[str]:
        problemas: list[str] = []
        for n, data in self.g.nodes(data=True):
            eq: Equipo = data["equipo"]
            for p in eq.puertos:
                if not p.conectado:
                    problemas.append(f"Puerto sin conectar: {p.codigo}")
                    continue
                if p.direccion is Direccion.ENTRADA:
                    entrantes = [e for e in self.g.in_edges(n, data=True)
                                 if e[2]["puerto_destino"] == p.nombre
                                 and e[2]["tipo"] == p.tipo.value]
                    if len(entrantes) != 1:
                        problemas.append(
                            f"'{p.codigo}' espera 1 entrada, tiene {len(entrantes)}"
                        )
        if not nx.is_weakly_connected(self.g):
            problemas.append("El grafo no es débilmente conexo")
        return problemas

    # ---------------- serialización (UI / persistencia) -----------------
    def a_dict(self) -> dict[str, Any]:
        def _flujo(f: Flujo) -> dict[str, Any]:
            d = asdict(f)
            c = d.get("comp")
            if isinstance(c, dict):
                d["comp"] = dict(c)
            return {k: (v.value if hasattr(v, "value") else v) for k, v in d.items()}

        return {
            "nodos": [
                {"id": n, "tipo": self.g.nodes[n]["tipo"]}
                for n in self.g.nodes
            ],
            "aristas": [
                {
                    "origen": u, "destino": v, "puerto_origen": d["puerto_origen"],
                    "puerto_destino": d["puerto_destino"], "tipo": d["tipo"],
                    "flujo": _flujo(d["flujo"]),
                }
                for u, v, d in self.g.edges(data=True)
            ],
        }