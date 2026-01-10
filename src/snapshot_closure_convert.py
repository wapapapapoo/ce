from __future__ import annotations
from typing import Set, Dict, List

from vg_types import ValueGraph, ValueNode, Edge


# ============================================================
# Entry
# ============================================================

def closure_convert(graph: ValueGraph):
    """
    在 resolve_all_phis 之后调用
    直接在 ValueGraph 上做闭包消除
    """

    # 所有函数定义 edge
    fndef_edges: List[Edge] = [
        e for e in graph.edges if e.kind == "fndef"
    ]

    # 逐个函数处理（内 → 外自然会被重复捕获）
    for fndef in fndef_edges:
        closure_vars = collect_closure_vars(graph, fndef)
        if not closure_vars:
            continue

        # 1️⃣ 扩展函数定义参数
        extend_fndef_inputs(fndef, closure_vars)

        # 2️⃣ 改写所有 call
        rewrite_calls(graph, fndef, closure_vars)


# ============================================================
# Step 1: 找闭包变量
# ============================================================

def collect_closure_vars(graph: ValueGraph, fndef: Edge) -> List[ValueNode]:
    """
    返回该函数需要捕获的 ValueNode（symbol）
    """

    # ---- 显式参数 ----
    formal_inputs: Set[ValueNode] = set(fndef.inputs)

    # ---- 函数体内使用的值 ----
    used: Set[ValueNode] = set()

    # fndef.inputs 里最后一个一定是 block
    block_val = fndef.inputs[-1]
    block_ast = block_val.ast

    # 收集函数体内所有 edge
    body_edges = [
        e for e in graph.edges
        if e.ast is not None
        and hasattr(e.ast, "getParent")
        and is_inside_block(e.ast, block_ast)
    ]

    for e in body_edges:
        if e.transform is not None:
            used.add(e.transform)
        for v in e.inputs:
            used.add(v)

    # ---- 反向追依赖（expr -> in_edge）----
    worklist = list(used)
    while worklist:
        v = worklist.pop()
        if v.in_edge is None:
            continue
        e = v.in_edge
        if e.transform is not None and e.transform not in used:
            used.add(e.transform)
            worklist.append(e.transform)
        for iv in e.inputs:
            if iv not in used:
                used.add(iv)
                worklist.append(iv)

    # ---- 闭包变量判定 ----
    closure_vars: List[ValueNode] = []

    for v in used:
        if v in formal_inputs:
            continue
        if v.kind != "symbol":
            continue
        closure_vars.append(v)

    return closure_vars


def is_inside_block(ast_node, block_ast) -> bool:
    """
    判断 ast_node 是否在 block_ast 内
    纯 AST parent 追溯
    """
    cur = ast_node
    while cur is not None:
        if cur is block_ast:
            return True
        try:
            cur = cur.getParent()
        except:
            return False
    return False


# ============================================================
# Step 2: 扩展函数定义
# ============================================================

def extend_fndef_inputs(fndef: Edge, closure_vars: List[ValueNode]):
    """
    把闭包变量插到 fndef.inputs 最前面
    """

    # 保证不重复插
    new_inputs: List[ValueNode] = []
    for v in closure_vars:
        if v not in fndef.inputs:
            new_inputs.append(v)

    fndef.inputs = new_inputs + fndef.inputs


# ============================================================
# Step 3: 改写 call
# ============================================================

def rewrite_calls(graph: ValueGraph, fndef: Edge, closure_vars: List[ValueNode]):
    """
    对所有调用该函数的 call edge，补实参
    """

    fn_value = fndef.output

    for e in graph.edges:
        if e.kind != "call":
            continue
        if e.transform is not fn_value:
            continue

        # 插到实参最前
        new_inputs: List[ValueNode] = []
        for v in closure_vars:
            new_inputs.append(v)

        e.inputs = new_inputs + e.inputs
