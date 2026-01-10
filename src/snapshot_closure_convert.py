from __future__ import annotations
from typing import Dict, Set, List
from collections import defaultdict

from vg_types import ValueGraph, ValueNode, Edge


# ============================================================
# Entry
# ============================================================
def closure_convert(graph: ValueGraph):
    fndef_edges = [e for e in graph.edges if e.kind == "fndef"]
    fn_closure: Dict[ValueNode, List[ValueNode]] = {}

    # 1️⃣ 计算自由变量 + 扩展签名
    for fndef in fndef_edges:
        free = collect_free_vars(graph, fndef)
        if free:
            fn_closure[fndef.output] = free
            extend_fndef_inputs(fndef, free)

    # 2️⃣ 建值使用关系
    users: Dict[ValueNode, List[Edge]] = defaultdict(list)
    for e in graph.edges:
        if e.transform is not None:
            users[e.transform].append(e)
        for v in e.inputs:
            users[v].append(e)

    # 3️⃣ 冒泡
    worklist = list(fn_closure.keys())
    seen: Set[ValueNode] = set(worklist)

    while worklist:
        fn_val = worklist.pop()
        closure_vars = fn_closure[fn_val]

        for e in users.get(fn_val, []):
            if e.kind == "call" and e.transform is fn_val:
                rewrite_call(e, closure_vars)

            elif e.kind == "fndef":
                outer_fn = e.output
                merged = merge_closure(fn_closure.get(outer_fn, []),
                                       closure_vars)
                if merged != fn_closure.get(outer_fn):
                    fn_closure[outer_fn] = merged
                    extend_fndef_inputs(e, closure_vars)
                    if outer_fn not in seen:
                        seen.add(outer_fn)
                        worklist.append(outer_fn)

            else:
                out = e.output
                if out is None:
                    continue
                merged = merge_closure(fn_closure.get(out, []),
                                       closure_vars)
                if merged != fn_closure.get(out):
                    fn_closure[out] = merged
                    if out not in seen:
                        seen.add(out)
                        worklist.append(out)

    # 4️⃣ ★ 真正消闭包：重写函数体
    for fndef in fndef_edges:
        rewrite_function_body(graph, fndef)

    # 5️⃣ ★ 最后 sanity check
    assert_no_free_symbols(graph)



def assert_no_free_symbols(graph: ValueGraph):
    for fndef in [e for e in graph.edges if e.kind == "fndef"]:
        params = set(fndef.inputs)
        block = fndef.inputs[-1].ast

        used: Set[ValueNode] = set()

        for e in graph.edges:
            if e.ast is None:
                continue
            if not is_inside_block(e.ast, block):
                continue

            if e.transform is not None:
                used.add(e.transform)
            for v in e.inputs:
                used.add(v)

        for v in used:
            # 只要是 symbol，就必须是参数
            if v.kind == "symbol" and v not in params:
                raise RuntimeError(
                    f"free symbol in function {fndef.output.id}: v{v.id} {v.ast}"
                )





# ============================================================
# Free variable analysis
# ============================================================

def collect_free_vars(graph: ValueGraph, fndef: Edge) -> List[ValueNode]:
    """
    返回 fndef 的自由 symbol（ValueNode）
    """

    formal = set(fndef.inputs)
    block = fndef.inputs[-1].ast

    used: Set[ValueNode] = set()

    for e in graph.edges:
        if e.ast is None:
            continue
        if not is_inside_block(e.ast, block):
            continue

        if e.transform is not None:
            used.add(e.transform)
        for v in e.inputs:
            used.add(v)

    # 反向追依赖
    stack = list(used)
    while stack:
        v = stack.pop()
        if v.in_edge is None:
            continue
        ie = v.in_edge
        if ie.transform is not None and ie.transform not in used:
            used.add(ie.transform)
            stack.append(ie.transform)
        for iv in ie.inputs:
            if iv not in used:
                used.add(iv)
                stack.append(iv)

    free: List[ValueNode] = []
    for v in used:
        if v in formal:
            continue
        if v.kind == "symbol":
            free.append(v)
    
    if v.kind == "symbol" and v not in formal:
        # 必须是来自外层 fndef.inputs 或更外层
        if v.in_edge is None or v.in_edge.kind != "fndef":
            free.append(v)

    return free


def is_inside_block(ast_node, block_ast) -> bool:
    cur = ast_node
    while cur is not None:
        if cur is block_ast:
            return True
        try:
            cur = cur.getParent()
        except Exception:
            return False
    return False


# ============================================================
# Rewrites
# ============================================================

def extend_fndef_inputs(fndef: Edge, closure_vars: List[ValueNode]):
    """
    closure_vars: 外层捕获到的 symbol ValueNode
    """
    if not hasattr(fndef, "_closure_param_map"):
        fndef._closure_param_map = {}

    new_inputs = []

    for v in closure_vars:
        # 只接受 symbol / block
        assert v.kind in {"symbol", "block"}

        if v in fndef._closure_param_map:
            continue

        # 关键：不 new，直接复用
        fndef._closure_param_map[v] = v
        new_inputs.append(v)

    if new_inputs:
        # 约定：closure 参数在最前
        fndef.inputs = new_inputs + fndef.inputs


def rewrite_function_body(graph: ValueGraph, fndef: Edge):
    """
    把函数体内对 closure symbol 的使用
    全部替换为对应的参数 ValueNode
    """

    if not hasattr(fndef, "_closure_param_map"):
        return

    block = fndef.inputs[-1].ast
    sym2param = fndef._closure_param_map

    for e in graph.edges:
        if e.ast is None:
            continue
        if not is_inside_block(e.ast, block):
            continue

        # rewrite transform
        if e.transform in sym2param:
            e.transform = sym2param[e.transform]

        # rewrite inputs
        new_inputs = []
        changed = False
        for v in e.inputs:
            if v in sym2param:
                new_inputs.append(sym2param[v])
                changed = True
            else:
                new_inputs.append(v)
        if changed:
            e.inputs = new_inputs



# def rewrite_call(call: Edge, closure_vars: List[ValueNode]):
#     new = []
#     for v in closure_vars:
#         if v not in call.inputs:
#             new.append(v)
#     if new:
#         call.inputs = new + call.inputs
def rewrite_call(call: Edge, closure_vars: List[ValueNode]):
    callee = call.transform
    if callee is None or not hasattr(callee.in_edge, "_closure_param_map"):
        return

    # 用 fndef.inputs 的前缀顺序
    fndef = callee.in_edge
    n = len(fndef._closure_param_map)

    closure_args = fndef.inputs[:n]

    new = []
    for v in closure_args:
        if v not in call.inputs:
            new.append(v)

    if new:
        call.inputs = new + call.inputs




def merge_closure(a: List[ValueNode], b: List[ValueNode]) -> List[ValueNode]:
    res = list(a)
    for v in b:
        if v not in res:
            res.append(v)
    return res
