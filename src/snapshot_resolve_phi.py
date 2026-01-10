from typing import Dict, Set

from ast_types import Identifier, BindPhi, Point
from vg_types import ValueGraph, PhiNode, ValueNode


# ============================================================
# Error
# ============================================================

class PhiResolveError(Exception):
    pass


def loc(ident: Identifier | None) -> str:
    if ident is None:
        return "<unknown>"
    cst = ident.getCstPointer()
    if not cst:
        return "<unknown>"
    line = cst.get("line")
    col = cst.get("column")
    if line is not None and col is not None:
        return f"{line}:{col}"
    return "<unknown>"


# ============================================================
# Point → ValueNode (polymorphic)
# ============================================================

def resolve_point_to_value(
    graph: ValueGraph,
    pt: Point,
) -> ValueNode:
    # ---------------- stmt 定义 ----------------
    if pt.stmt is not None:
        val = graph.value_of_expr(pt.stmt.expr)
        if val is None:
            raise PhiResolveError(
                f"stmt point p{pt.id} not mapped to value at {loc(pt.identifier)}"
            )
        return val

    # ---------------- builtin ----------------
    if pt.type == "builtin":
        for v in graph.values:
            if v.kind == "symbol" and isinstance(v.ast, Identifier):
                if v.ast.name == pt.name:
                    return v
        raise PhiResolveError(
            f"builtin '{pt.name}' not found at {loc(pt.identifier)}"
        )

    # ---------------- symbol ----------------
    if pt.type == "symbol":
        for v in graph.values:
            if v.kind == "symbol" and v.ast is pt.identifier:
                return v
        raise PhiResolveError(
            f"symbol '{pt.name}' not found at {loc(pt.identifier)}"
        )

    # ---------------- function param ----------------
    if pt.type == "point":
        for v in graph.values:
            if v.kind == "symbol" and v.ast is pt.identifier:
                return v
        raise PhiResolveError(
            f"function param '{pt.name}' not found at {loc(pt.identifier)}"
        )

    raise PhiResolveError(
        f"unknown point p{pt.id} ({pt.type}) at {loc(pt.identifier)}"
    )


# ============================================================
# Phi resolve（只负责“决策”，不直接改图）
# ============================================================

def resolve_bindphi(
    graph: ValueGraph,
    phi: PhiNode,
) -> ValueNode:
    bp: BindPhi = phi.bindphi

    if not bp.candidates:
        raise PhiResolveError(
            f"BindPhi#{bp.id} '{bp.name}' has no candidates at {loc(bp.entry)}"
        )

    max_depth = max(bp.candidates.keys())
    pts: Set[Point] = bp.candidates[max_depth]

    if len(pts) != 1:
        raise PhiResolveError(
            f"BindPhi#{bp.id} '{bp.name}' ambiguous at depth {max_depth} "
            f"({len(pts)} points) at {loc(bp.entry)}"
        )

    pt = next(iter(pts))
    return resolve_point_to_value(graph, pt)


def resolve_phi_node(
    graph: ValueGraph,
    phi: PhiNode,
) -> ValueNode:
    if phi.bindphi is not None:
        return resolve_bindphi(graph, phi)

    if not phi.candidates:
        raise PhiResolveError(
            f"PhiNode p{phi.id} has no candidates"
        )

    max_level = max(phi.candidates.keys())
    vals = phi.candidates[max_level]

    if len(vals) != 1:
        raise PhiResolveError(
            f"PhiNode p{phi.id} ambiguous at level {max_level} "
            f"({len(vals)} values)"
        )

    return next(iter(vals))


# ============================================================
# 全图 resolve（关键修正点在这里）
# ============================================================
def resolve_all_phis(graph: ValueGraph):
    """
    目标：
    - 为每个 PhiNode 选唯一 ValueNode
    - 用 ValueNode 重写所有 Edge
    - 清空 graph.phis
    """

    # 1️⃣ PhiNode -> ValueNode
    phi_to_value: Dict[PhiNode, ValueNode] = {}

    for phi in list(graph.phis):
        phi_to_value[phi] = resolve_phi_node(graph, phi)

    # 2️⃣ 重写 Edge
    for e in graph.edges:
        if e.transform is not None:
            e.transform = phi_to_value[e.transform]

        e.inputs = [
            phi_to_value[p] for p in e.inputs
        ]

    # 3️⃣ 清空 Phi
    graph.phis.clear()
