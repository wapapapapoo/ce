from __future__ import annotations
from typing import List, Optional, Set

# ============================================================
# AST imports（你已有）
# ============================================================

from ast_types import (
    Expr, Identifier, Literal as AstLiteral,
    AstList, ListItem,
    Function, Call,
    Block, Stmt,
    BindPhi,
)

# ============================================================
# Value Graph imports（你已有）
# ============================================================

from vg_types import (
    ValueGraph,
    ValueNode,
    PhiNode,
    Edge,
    ValueKind,
    EdgeKind,
)



def dump_value_graph(graph: ValueGraph):
    print("=" * 80)
    print("VALUE GRAPH")
    print("=" * 80)

    dump_values(graph)
    dump_phis(graph)
    dump_edges(graph)

    print("=" * 80)


def dump_values(graph: ValueGraph):
    print("\n[ValueNodes]")
    for v in graph.values:
        ast = v.ast.__class__.__name__ if v.ast else None
        in_edge = f"e{v.in_edge.id}" if v.in_edge else None
        if v.placeholder:
            continue

        print(
            f"  v{v.id:<3} "
            f"kind={v.kind:<7} "
            f"ast={ast:<12} "
            f"in_edge={in_edge}"
            f"  {v.ast.getCstPointer().get('text', '<rule>') if v.ast.getCstPointer() is not None else '<builtin>'}"
        )


def dump_phis(graph: ValueGraph):
    print("\n[PhiNodes]")
    for p in graph.phis:
        if p.identifier is not None:
            name = p.identifier.name
        else:
            name = '<not an identifier>'
        bind = f"BindPhi#{p.bindphi.id}" if p.bindphi else None

        print(f"  p{p.id:<3} id={name} bindphi={bind}")

        for level, values in sorted(p.candidates.items()):
            vs = ", ".join(f"v{v.id}" for v in values)
            print(f"       depth {level}: {vs}")


def dump_edges(graph: ValueGraph):
    print("\n[Edges]")
    for e in graph.edges:
        print(f"  e{e.id:<3} kind={e.kind}")

        print(f"       out : v{e.output.id}")

        if e.transform:
            print(f"       fn  : p{e.transform.id}")

        if e.inputs:
            ins = ", ".join(f"p{p.id}" for p in e.inputs)
            print(f"       in  : {ins}")

        ast = e.ast.__class__.__name__
        print(f"       ast : {ast}")
















# bdg_to_vg_fixed.py
from typing import List, Deque, Optional, Any, Dict
from collections import deque, defaultdict

from ast_types import (
    Program, Block, BlockInfo, Point, BindPhi,
    AstList, Function, Call, Identifier, Literal as AstLiteral, ListItem, Stmt
)
from vg_types import ValueGraph, PhiNode, ValueNode, Edge

# -------------------------
# Helper: re-export graph.value_of_expr if needed
# -------------------------
# (Assumes ValueGraph has method value_of_expr as in your code.)

# -------------------------
# Build Value Graph
# -------------------------
def build_value_graph(
    ast: Program,
    block_index: List[BlockInfo],
    point_index: List[Point],
    bindphi_index: List[BindPhi],
) -> ValueGraph:
    graph = ValueGraph()

    assert len(block_index) > 0
    root: BlockInfo = block_index[0]

    q: Deque[BlockInfo] = deque()
    q.append(root)

    # BFS over block tree (keeps same ordering as before)
    while q:
        bi = q.popleft()
        process_block(graph, bi)
        for child in bi.children:
            q.append(child)

    # connect identifiers (resolve placeholder phis to real bindphis)
    connect_identifiers(graph)

    return graph



# -------------------------
# process_block: build expression trees for each stmt in block
# -------------------------
def process_block(graph: ValueGraph, bi: BlockInfo):
    block = bi.ast_block
    for stmt in block.stmts:
        build_expr_tree(graph, stmt.expr)


# -------------------------
# build_expr_tree: recursive construction
# - reuses graph.value_of_expr(expr) when available
# - creates placeholder ValueNodes for Identifiers (placeholder=True)
# - creates PhiNodes for calls/list items with those placeholder values as candidates
# -------------------------
def build_expr_tree(graph: ValueGraph, expr: Any) -> ValueNode:
    # try reuse
    existing = graph.value_of_expr(expr)
    if existing is not None:
        return existing

    # Literal
    if isinstance(expr, AstLiteral):
        return graph.new_value(kind="literal", ast=expr, cst=expr.cstPointer)

    # Identifier -> placeholder value (we will resolve later via phis)
    if isinstance(expr, Identifier):
        return graph.new_value(kind="expr", ast=expr, cst=expr.cstPointer, placeholder=True)

    # Call
    if isinstance(expr, Call):
        fn_val = build_expr_tree(graph, expr.fn)
        arg_val = build_expr_tree(graph, expr.arg)

        out = graph.new_value(kind="expr", ast=expr, cst=expr.cstPointer)

        # create placeholder phi nodes that contain those value nodes as single-candidate
        fn_phi = graph.new_phi(identifier=expr.fn if isinstance(expr.fn, Identifier) else None, bindphi=None)
        fn_phi.add(0, fn_val)

        arg_phi = graph.new_phi(identifier=expr.arg if isinstance(expr.arg, Identifier) else None, bindphi=None)
        arg_phi.add(0, arg_val)

        graph.new_edge(kind="call", output=out, transform=fn_phi, inputs=[arg_phi], ast=expr)
        return out

    # Function
    if isinstance(expr, Function):
        inputs: List[PhiNode] = []

        # params
        p_val = build_expr_tree(graph, expr.params)
        p_phi = graph.new_phi(identifier=None, bindphi=None); p_phi.add(0, p_val); inputs.append(p_phi)

        # ret
        if expr.ret is not None:
            r_val = build_expr_tree(graph, expr.ret)
            r_phi = graph.new_phi(identifier=None, bindphi=None); r_phi.add(0, r_val); inputs.append(r_phi)

        # annotations
        for a in expr.ann:
            a_val = build_expr_tree(graph, a)
            a_phi = graph.new_phi(identifier=None, bindphi=None); a_phi.add(0, a_val); inputs.append(a_phi)

        # block as value
        blk_val = graph.new_value(kind="block", ast=expr.body, cst=None)
        blk_phi = graph.new_phi(identifier=None, bindphi=None); blk_phi.add(0, blk_val); inputs.append(blk_phi)

        out = graph.new_value(kind="expr", ast=expr, cst=expr.cstPointer)
        fndef = graph.new_edge(kind="fndef", output=out, transform=None, inputs=inputs, ast=expr)
        graph.type_values.append([fndef, *inputs])
        return out

    # AstList
    if isinstance(expr, AstList):
        item_phis: List[PhiNode] = []
        for item in expr.items:
            if item.key is not None:
                k_val = graph.new_value(kind="symbol", ast=item.key, cst=item.key.cstPointer)
                v_val = build_expr_tree(graph, item.value)
                k_phi = graph.new_phi(identifier=item.key, bindphi=None); k_phi.add(0, k_val)
                v_phi = graph.new_phi(identifier=None, bindphi=None); v_phi.add(0, v_val)
                kv_out = graph.new_value(kind="expr", ast=item, cst=item.cstPointer)
                graph.new_edge(kind="kvdef", output=kv_out, transform=None, inputs=[k_phi, v_phi], ast=item)
                kv_phi = graph.new_phi(identifier=None, bindphi=None); kv_phi.add(0, kv_out)
                item_phis.append(kv_phi)
            else:
                v_val = build_expr_tree(graph, item.value)
                v_phi = graph.new_phi(identifier=None, bindphi=None); v_phi.add(0, v_val)
                item_phis.append(v_phi)

        out = graph.new_value(kind="expr", ast=expr, cst=expr.cstPointer)
        graph.new_edge(kind="listdef", output=out, transform=None, inputs=item_phis, ast=expr)
        return out

    raise NotImplementedError(f"Unhandled expr type: {type(expr)}")


def materialize_value(graph: ValueGraph, v: ValueNode) -> ValueNode:
    if not v.placeholder:
        return v

    new_v = graph.new_value(
        kind=v.kind,
        ast=v.ast,
        cst=v.cst,
        placeholder=False,
    )

    replace_value_node(graph, v, new_v)
    return new_v


def replace_value_node(graph: ValueGraph, old: ValueNode, new: ValueNode):
    # 1. edge.output
    for e in graph.edges:
        if e.output is old:
            e.output = new
            new.in_edge = e

    # 2. phi candidates
    for p in graph.phis:
        for depth, vs in p.candidates.items():
            if old in vs:
                vs.remove(old)
                vs.add(new)

    # 3. graph.values
    graph.values = [new if v is old else v for v in graph.values]


# -------------------------
# connect_identifiers: replace placeholder phis (bindphi-less) with real bindphi phis
# Strategy:
#  - scan graph.phis for placeholder phis that carry identifier info (phi.identifier is Identifier, phi.bindphi is None)
#  - for each such placeholder phi, get identifier.bindphi (BindPhi), build a new PhiNode whose candidates are
#    resolved ValueNodes corresponding to BindPhi.candidates (stmt expr value / builtin / symbol)
#  - replace all uses of the placeholder phi (edge.inputs / edge.transform) with the new PhiNode
# -------------------------
def connect_identifiers(graph: ValueGraph):
    # caches for builtin & symbol value nodes
    builtin_cache: Dict[str, ValueNode] = {}
    symbol_cache: Dict[str, ValueNode] = {}
    
    # 提前收集所有需要 materialize 的值节点
    values_to_materialize: Set[ValueNode] = set()
    
    # 第一步：收集所有需要处理的 placeholder phi 节点
    placeholder_phis: List[PhiNode] = [
        p for p in list(graph.phis) 
        if getattr(p, "identifier", None) is not None and p.bindphi is None
    ]
    
    # 第二步：处理每个 placeholder phi
    for old_phi in placeholder_phis:
        ident = old_phi.identifier
        if ident is None:
            continue
            
        bp: Optional[BindPhi] = getattr(ident, "bindphi", None)
        if bp is None:
            continue
            
        # 创建新的 phi 节点
        new_phi = graph.new_phi(identifier=ident, bindphi=bp)
        
        # 填充候选值
        for depth, pts in bp.candidates.items():
            for pt in pts:
                if pt.stmt is not None:
                    target_val = graph.value_of_expr(pt.stmt.expr)
                    if target_val is None:
                        # 如果值不存在，需要先构建表达式树
                        target_val = build_expr_tree(graph, pt.stmt.expr)
                    values_to_materialize.add(target_val)
                    new_phi.add(depth, target_val)
                elif pt.type == "builtin":
                    name = pt.name
                    if name not in builtin_cache:
                        sym = Identifier(name)
                        builtin_cache[name] = graph.new_value(
                            kind="expr", ast=sym, cst=None, placeholder=False
                        )
                    new_phi.add(depth, builtin_cache[name])
                else:
                    sym = pt.identifier
                    if sym.name not in symbol_cache:
                        symbol_cache[sym.name] = graph.new_value(
                            kind="symbol", ast=sym, cst=sym.cstPointer, placeholder=False
                        )
                    new_phi.add(depth, symbol_cache[sym.name])
        
        # 替换所有对 old_phi 的引用
        for e in graph.edges:
            if e.transform is old_phi:
                e.transform = new_phi
            e.inputs = [new_phi if inp is old_phi else inp for inp in e.inputs]
    
    # 第三步：materialize 所有收集到的值节点
    for v in values_to_materialize:
        if v.placeholder:
            materialize_value(graph, v)
    
    # 第四步：清理不再使用的 phi 节点
    used_phis = set()
    for e in graph.edges:
        if e.transform:
            used_phis.add(e.transform)
        used_phis.update(e.inputs)
    
    graph.phis = [p for p in graph.phis if p in used_phis]
    
    # 第五步：最后清理剩余的 placeholder 值节点
    final_cleanup_placeholders(graph)

def final_cleanup_placeholders(graph: ValueGraph):
    """清理所有剩余的 placeholder 值节点"""
    for v in list(graph.values):
        if v.placeholder:
            # 对于仍然存在的 placeholder，强制创建非 placeholder 版本
            new_v = graph.new_value(
                kind=v.kind,
                ast=v.ast,
                cst=v.cst,
                placeholder=False,
            )
            replace_value_node(graph, v, new_v)