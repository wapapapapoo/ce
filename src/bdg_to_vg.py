from __future__ import annotations
from typing import List, Optional

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

















from typing import List, Deque
from collections import deque

from ast_types import (
    Program, Block, BlockInfo, Point, BindPhi,
    AstList, Function, Call, Identifier, Literal as AstLiteral
)
from vg_types import ValueGraph, PhiNode

# ============================================================
# Entry: 接收 BDG 全量产物
# ============================================================

def build_value_graph(
    ast: Program,
    block_index: List[BlockInfo],
    point_index: List[Point],
    bindphi_index: List[BindPhi],
) -> ValueGraph:
    """
    Step 1:
    - 接收 BDG 四个返回值

    Step 2:
    - 以 block_index[0] 作为根
    - BFS 遍历整个 BlockInfo 树
    - 当前只搭遍历框架，不做任何语义处理
    """
    graph = ValueGraph()

    # ------------------------------
    # Block BFS skeleton
    # ------------------------------

    assert len(block_index) > 0
    root: BlockInfo = block_index[0]

    q: Deque[BlockInfo] = deque()
    q.append(root)

    while q:
        bi = q.popleft()

        # TODO: 后续步骤在这里处理 block
        process_block(graph, bi)

        for child in bi.children:
            q.append(child)
    
    connect_identifiers(graph, bi, point_index)

    return graph

# ============================================================
# Step 3: block 处理框架 + stmt DFS 骨架
# ============================================================

def process_block(
    graph: ValueGraph,
    bi: BlockInfo,
):
    """
    在 BFS 中调用：
    - 遍历该 block 内的每一条语句
    - 对 stmt.expr 做 DFS 拆解
    - 目标只是：ValueNode -> Edge -> PhiNode -> ValueNode 的树形结构
    - 不做 resolve / merge / 多候选处理
    """
    block = bi.ast_block

    for stmt in block.stmts:
        build_expr_tree(graph, stmt.expr)


# ============================================================
# DFS: Expr → ValueNode / Edge / PhiNode（骨架）
# ============================================================

def build_expr_tree(
    graph: ValueGraph,
    expr,
):
    """
    DFS 拆 expr，生成一棵：
        ValueNode(root)
          <- Edge
              <- 单候选 PhiNode
                  <- ValueNode(child)
    规则（当前步）：
    - Literal / Identifier / Block 为递归终止
    - Identifier：用 expr ValueNode 表示，不解析 phi
    - Function / AstList / Call：继续 DFS
    """

    # ---------- Literal ----------
    if isinstance(expr, AstLiteral):
        return graph.new_value(
            kind="literal",
            ast=expr,
            cst=expr.cstPointer,
        )

    # ---------- Identifier（终止，作为 expr value） ----------
    if isinstance(expr, Identifier):
        return graph.new_value(
            kind="expr",
            ast=expr,
            cst=expr.cstPointer,
            placeholder=True,
        )

    # ---------- Call ----------
    if isinstance(expr, Call):
        fn_val = build_expr_tree(graph, expr.fn)
        arg_val = build_expr_tree(graph, expr.arg)

        out = graph.new_value(
            kind="expr",
            ast=expr,
            cst=expr.cstPointer,
        )

        fn_phi = graph.new_phi(
            identifier=expr.fn if isinstance(expr.fn, Identifier) else None,
            bindphi=None,
        )
        fn_phi.add(0, fn_val)

        arg_phi = graph.new_phi(
            identifier=expr.arg if isinstance(expr.arg, Identifier) else None,
            bindphi=None,
        )
        arg_phi.add(0, arg_val)

        graph.new_edge(
            kind="call",
            output=out,
            transform=fn_phi,
            inputs=[arg_phi],
            ast=expr,
        )
        return out

    # ---------- Function ----------
    if isinstance(expr, Function):
        inputs: List[PhiNode] = []

        # params
        p_val = build_expr_tree(graph, expr.params)
        p_phi = graph.new_phi(identifier=None, bindphi=None)
        p_phi.add(0, p_val)
        inputs.append(p_phi)

        # return type
        if expr.ret is not None:
            r_val = build_expr_tree(graph, expr.ret)
            r_phi = graph.new_phi(identifier=None, bindphi=None)
            r_phi.add(0, r_val)
            inputs.append(r_phi)

        # annotations
        for a in expr.ann:
            a_val = build_expr_tree(graph, a)
            a_phi = graph.new_phi(identifier=None, bindphi=None)
            a_phi.add(0, a_val)
            inputs.append(a_phi)

        # block as value (terminal)
        blk_val = graph.new_value(
            kind="block",
            ast=expr.body,
            cst=None,
        )
        blk_phi = graph.new_phi(identifier=None, bindphi=None)
        blk_phi.add(0, blk_val)
        inputs.append(blk_phi)

        out = graph.new_value(
            kind="expr",
            ast=expr,
            cst=expr.cstPointer,
        )

        fndef = graph.new_edge(
            kind="fndef",
            output=out,
            transform=None,
            inputs=inputs,
            ast=expr,
        )

        graph.type_values.append([
            fndef,
            *inputs,
        ])

        return out

    # ---------- AstList ----------
    if isinstance(expr, AstList):
        item_phis: List[PhiNode] = []

        for item in expr.items:
            # key-value
            if item.key is not None:
                k_val = graph.new_value(
                    kind="symbol",
                    ast=item.key,
                    cst=item.key.cstPointer,
                )
                v_val = build_expr_tree(graph, item.value)

                k_phi = graph.new_phi(identifier=item.key, bindphi=None)
                k_phi.add(0, k_val)
                v_phi = graph.new_phi(identifier=None, bindphi=None)
                v_phi.add(0, v_val)

                kv_out = graph.new_value(
                    kind="expr",
                    ast=item,
                    cst=item.cstPointer,
                )

                graph.new_edge(
                    kind="kvdef",
                    output=kv_out,
                    transform=None,
                    inputs=[k_phi, v_phi],
                    ast=item,
                )

                kv_phi = graph.new_phi(identifier=None, bindphi=None)
                kv_phi.add(0, kv_out)
                item_phis.append(kv_phi)

            else:
                v_val = build_expr_tree(graph, item.value)
                v_phi = graph.new_phi(identifier=None, bindphi=None)
                v_phi.add(0, v_val)
                item_phis.append(v_phi)

        out = graph.new_value(
            kind="expr",
            ast=expr,
            cst=expr.cstPointer,
        )

        graph.new_edge(
            kind="listdef",
            output=out,
            transform=None,
            inputs=item_phis,
            ast=expr,
        )
        return out

    raise NotImplementedError(type(expr))



def connect_identifiers(graph: ValueGraph, bi: BlockInfo, points: Point):
    """
    Step 4:
    - 将 build_expr_tree 阶段遇到的 Identifier ValueNode
      与其 BindPhi 对应的定义点连接起来
    """

    # symbol ValueNode 复用（同一个 symbol 只建一个）
    symbol_cache: dict[str, ValueNode] = {}
    builtin_cache: dict[str, ValueNode] = {}

    # 注意：这里遍历的是“当前已经建出来的值”
    for val in list(graph.values):
        # 只处理 Identifier 对应的 expr value
        if val.kind != "expr":
            continue
        if not isinstance(val.ast, Identifier):
            continue

        ident: Identifier = val.ast
        bindphi: BindPhi = ident.bindphi
        if bindphi is None:
            continue

        # 为这个 identifier 构造一个“真实”的 PhiNode
        phi = graph.new_phi(
            identifier=ident,
            bindphi=bindphi,
        )

        # BindPhi.candidates: depth -> Set[Point]
        for depth, points in bindphi.candidates.items():
            for pt in points:
                # ---------- case 1: point 来自某条语句 ----------
                if pt.stmt is not None:
                    expr = pt.stmt.expr
                    target_val = graph.value_of_expr(expr)
                    assert target_val is not None
                    phi.add(depth, target_val)

                elif pt.type == 'builtin':
                    sym = Identifier(pt.name)
                    if pt.name not in builtin_cache:
                        builtin_cache[pt.name] = graph.new_value(
                            kind="symbol",
                            ast=sym,
                            cst=sym.cstPointer,
                        )
                    phi.add(depth, builtin_cache[pt.name])

                # ---------- case 3: symbol ----------
                else:
                    sym = pt.identifier
                    if sym.name not in symbol_cache:
                        symbol_cache[sym.name] = graph.new_value(
                            kind="symbol",
                            ast=sym,
                            cst=sym.cstPointer,
                        )
                    phi.add(depth, symbol_cache[sym.name])

        # 用这个新的 phi，替换掉原来 edge.inputs 里的占位 phi
        replace_input_phi(graph, val, phi)


def replace_input_phi(
    graph: ValueGraph,
    ident_val: ValueNode,
    new_phi: PhiNode,
):
    """
    ident_val: Identifier 对应的 ValueNode
    new_phi:   用 BindPhi 构造出来的新 PhiNode
    """

    # 在所有 edge.inputs 中找这个 ident_val
    found = False

    for edge in graph.edges:
        for i, phi in enumerate(edge.inputs):
            # 占位 phi 一定只有一个 candidate，且指向 ident_val
            for values in phi.candidates.values():
                if ident_val in values:
                    edge.inputs[i] = new_phi
                    found = True
                    break
            if found:
                break
        if found:
            break

    # assert found, f"identifier value v{ident_val.id} not used by any edge"
