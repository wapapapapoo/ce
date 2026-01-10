# vg_effects.py
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict

from vg_types import ValueGraph, ValueNode, Edge
from ast_types import Block, Stmt, Identifier, Function, Call, Expr, BlockInfo

# -----------------------------
# Configuration / heuristics
# -----------------------------
EFFECT_ANNOTATION_NAMES = {"!effect", "effect!"}

# builtin names considered effectful (same heuristic you had)
def _builtin_name_is_effect(name: str) -> bool:
    if not name:
        return False
    return name in ['print!', 'readi32!', 'readchr!']

# -----------------------------
# AST helpers (boundary-aware)
# -----------------------------
def _is_inside_ast_no_cross_function(inner: Any, outer: Any) -> bool:
    """
    Like descendant test, but stops if a Function boundary is encountered
    that is NOT the outer. This prevents attributing inner function-body nodes
    to an outer statement's execution region.
    """
    cur = inner
    try:
        while cur is not None:
            if cur is outer:
                return True
            if isinstance(cur, Function) and cur is not outer:
                return False
            cur = cur.getParent()
    except Exception:
        return False
    return False

def _stmt_contains_edge_ast(stmt: Stmt, edge_ast: Any) -> bool:
    """
    Does edge_ast syntactically sit inside stmt.expr (without crossing nested
    Function boundaries)? Additionally, if stmt.expr is a Function, do NOT
    attribute nodes that are inside its .body to the outer statement.
    """
    if stmt is None or edge_ast is None:
        return False
    expr = stmt.expr
    if isinstance(expr, Function):
        # header parts belong to outer stmt, body does not
        if expr.params and _is_inside_ast_no_cross_function(edge_ast, expr.params):
            return True
        if expr.ret and _is_inside_ast_no_cross_function(edge_ast, expr.ret):
            return True
        for a in getattr(expr, "ann", []) or []:
            if _is_inside_ast_no_cross_function(edge_ast, a):
                return True
        return False
    return _is_inside_ast_no_cross_function(edge_ast, expr)

def _get_stmt_position_key(stmt: Stmt) -> tuple:
    # Stmt 本身没有 cstPointer，用 expr 的
    expr = stmt.expr
    cst = getattr(expr, "cstPointer", None)
    if cst:
        line = cst.get('start', {'line': 0}).get("line")
        col = cst.get('start', {'line': 0}).get("column")
        if line is not None and col is not None:
            return (line, col)
    return (0, 0)


# -----------------------------
# defensive: normalize input -> ValueNode list
# -----------------------------
def _value_nodes_from_input(potential) -> List[ValueNode]:
    if potential is None:
        return []
    if hasattr(potential, "candidates"):
        vals = set()
        for lvl_vals in potential.candidates.values():
            vals.update(lvl_vals)
        return list(vals)
    return [potential]

# -----------------------------
# edge -> owning BlockInfo lookup
# -----------------------------
def _build_block_ast_to_bi_map(block_index: List[BlockInfo]) -> Dict[Block, BlockInfo]:
    m = {}
    for bi in block_index:
        m[bi.ast_block] = bi
    return m

def _find_enclosing_block_ast(node: Any) -> Optional[Block]:
    cur = node
    try:
        while cur is not None:
            if isinstance(cur, Block):
                return cur
            cur = cur.getParent()
    except Exception:
        return None
    return None

def _edge_owner_blockinfo(edge: Edge, block_ast_to_bi: Dict[Block, BlockInfo], default_bi: BlockInfo) -> BlockInfo:
    """
    Determine the BlockInfo that 'owns' this edge in execution semantics terms:
    - climb AST parents from edge.ast until hitting a Block AST
    - map that Block AST to BlockInfo
    - fall back to default_bi (top-level) if not found
    """
    block_ast = _find_enclosing_block_ast(edge.ast)
    if block_ast is None:
        return default_bi
    return block_ast_to_bi.get(block_ast, default_bi)

# -----------------------------
# main pass: apply_effects
# -----------------------------
def apply_effects(graph: ValueGraph, block_index: List[BlockInfo]) -> Dict[str, Any]:
    """
    Main entry implementing your six rules.
    Side-effects:
      - sets e._is_effect (bool) for edges (only call edges will be True)
      - sets e._effect_index (int) and e._effect_block (Block AST) for each effect edge
      - sets graph._effect_edges, graph._effect_order, graph._effect_pos
    Raises RuntimeError if a function's block contains effect but the Function AST
    has no !effect annotation (per your rule 3).
    """
    for e in graph.edges:
        e._is_effect = False
        e._effect_index = None
        e._effect_block = None

    if not block_index:
        return {"effect_edges": set(), "effect_order": {}, "effect_pos": {}}

    # map block AST -> BlockInfo (取第一个，避免重复)
    block_ast_to_bi = {}
    for bi in block_index:
        if bi.ast_block not in block_ast_to_bi:
            block_ast_to_bi[bi.ast_block] = bi
    
    top_bi = block_index[0]

    # build edges -> owning block info mapping (based on AST containment)
    edges_by_block: Dict[BlockInfo, List[Edge]] = {bi: [] for bi in block_index}
    for e in graph.edges:
        if e.kind != 'call':
            continue
        bi = _edge_owner_blockinfo(e, block_ast_to_bi, top_bi)
        edges_by_block[bi].append(e)

    # we'll process blocks bottom-up (deeper depth first)
    # 去重：只处理唯一的block_ast
    unique_blocks = {}
    for bi in block_index:
        if bi.ast_block not in unique_blocks:
            unique_blocks[bi.ast_block] = bi
    
    bis_sorted = sorted(unique_blocks.values(), key=lambda b: -b.depth)

    # record: function value node -> bool (block had effect and thus function required annotated)
    func_value_marked_effectful: Dict[ValueNode, bool] = {}

    # final containers
    all_effect_edges: Set[Edge] = set()
    effect_order_map: Dict[Block, List[Edge]] = {}
    edge_to_pos: Dict[Edge, Tuple[Optional[Block], int]] = {}

    # precompute function fndef mapping: block AST -> list of fndef edges that reference that block
    block_to_fndefs: Dict[Block, List[Edge]] = defaultdict(list)
    for e in graph.edges:
        if e.kind == "fndef":
            # inputs last is block value (could be Phi or ValueNode)
            if not e.inputs:
                continue
            blk_input = e.inputs[-1]
            vals = _value_nodes_from_input(blk_input)
            for v in vals:
                if v is None:
                    continue
                if v.ast is None:
                    continue
                if isinstance(v.ast, Block):
                    block_ast = v.ast
                    block_to_fndefs[block_ast].append(e)

    # 添加调试信息
    # print(f"Total unique blocks to process: {len(bis_sorted)}")
    # for i, bi in enumerate(bis_sorted):
        # print(f"  Block {i}: depth={bi.depth}, stmts={len(bi.ast_block.stmts)}")

    # process each block bottom-up
    for bi in bis_sorted:
        block_ast = bi.ast_block
        # print(f"\nProcessing block {id(block_ast)} with {len(block_ast.stmts)} statements")
        
        # 获取该block的所有边
        if bi not in edges_by_block:
            edges_in_block = []
        else:
            edges_in_block = edges_by_block[bi]

        # only consider call edges that syntactically belong to this block (filter out nested fndef/listdef etc)
        call_edges_in_block: List[Edge] = [
            e for e in edges_in_block
            if e.kind == "call"
            and isinstance(e.ast, Call)
            and _find_enclosing_block_ast(e.ast) is block_ast
        ]
        
        # print(f"  Call edges in this block: {[e.id for e in call_edges_in_block]}")

        # effect set local to this block (only edges from call_edges_in_block considered)
        effect_set: Set[Edge] = set()

        # 1) initial seed: builtin calls
        for e in call_edges_in_block:
            trans_vals = _value_nodes_from_input(e.transform)
            for tv in trans_vals:
                if tv is None:
                    continue
                if tv.ast is not None and isinstance(tv.ast, Identifier):
                    if _builtin_name_is_effect(tv.ast.name):
                        effect_set.add(e)
                        # print(f"    Edge E{e.id} is effectful (builtin: {tv.ast.name})")
                        break

        # 2) if callee is a function value AND that function currently is known to be effectful
        for e in call_edges_in_block:
            if e in effect_set:
                continue
            trans_vals = _value_nodes_from_input(e.transform)
            for tv in trans_vals:
                if tv is None:
                    continue
                if tv.ast is not None and isinstance(tv.ast, Function):
                    anns = getattr(tv.ast, "ann", []) or []
                    if any(isinstance(a, Identifier) and a.name in EFFECT_ANNOTATION_NAMES for a in anns):
                        effect_set.add(e)
                        # print(f"    Edge E{e.id} is effectful (function with !effect annotation)")
                        break
                if tv.in_edge is not None and tv.in_edge.kind == "fndef":
                    f_ast = tv.in_edge.ast
                    if isinstance(f_ast, Function):
                        anns = getattr(f_ast, "ann", []) or []
                        if any(isinstance(a, Identifier) and a.name in EFFECT_ANNOTATION_NAMES for a in anns):
                            effect_set.add(e)
                            # print(f"    Edge E{e.id} is effectful (fndef with !effect)")
                            break
                    if func_value_marked_effectful.get(tv, False):
                        effect_set.add(e)
                        # print(f"    Edge E{e.id} is effectful (function value marked effectful)")
                        break

        # 3) propagate inside block
        changed = True
        while changed:
            changed = False
            for e in call_edges_in_block:
                if e in effect_set:
                    continue
                inputs = []
                for inp in e.inputs:
                    inputs.extend(_value_nodes_from_input(inp))
                input_causes = False
                for v in inputs:
                    if v is None:
                        continue
                    prod = v.in_edge
                    if prod is None:
                        continue
                    if prod in call_edges_in_block:
                        if prod in effect_set:
                            input_causes = True
                            break
                if input_causes:
                    effect_set.add(e)
                    changed = True
                    # print(f"    Edge E{e.id} is effectful (propagated from input)")

        # print(f"  Effect set: {[e.id for e in effect_set]}")

        # 4) If this block is a function body and it has any effect call
        if effect_set:
            fndefs_for_block = block_to_fndefs.get(block_ast, [])
            if fndefs_for_block:
                for fndef_edge in fndefs_for_block:
                    f_ast = fndef_edge.ast
                    if not isinstance(f_ast, Function):
                        continue
                    anns = getattr(f_ast, "ann", []) or []
                    has_effect_ann = any(isinstance(a, Identifier) and a.name in EFFECT_ANNOTATION_NAMES for a in anns)
                    if not has_effect_ann:
                        loc = "<unknown>"
                        try:
                            cst = f_ast.getCstPointer()
                            if cst:
                                loc = f"{cst.get('line','?')}:{cst.get('column','?')}"
                        except Exception:
                            pass
                        raise RuntimeError(
                            f"Function at {loc} whose block contains effectful operations is missing !effect annotation."
                        )
                    func_value_marked_effectful[fndef_edge.output] = True

        # 5) assign ordering inside this block for the effect_set.
        ordered: List[Edge] = []
        matched: Set[Edge] = set()
        stmts = getattr(block_ast, "stmts", []) or []
        stmts_sorted = sorted(stmts, key=_get_stmt_position_key)

        print([_get_stmt_position_key(i) for i in stmts_sorted])
        
        # print(f"  Statements in order: {[f'Stmt@{_get_stmt_position_key(stmt)}' for stmt in stmts_sorted]}")

        # 修复匹配逻辑：先建立边到语句的映射
        stmt_to_edges: Dict[Stmt, List[Edge]] = defaultdict(list)
        for e in call_edges_in_block:
            if e not in effect_set:
                continue
            for stmt in stmts_sorted:
                try:
                    if _stmt_contains_edge_ast(stmt, e.ast):
                        stmt_to_edges[stmt].append(e)
                        break
                except Exception:
                    continue
        
        # 按语句顺序处理
        for stmt in stmts_sorted:
            edges_in_stmt = stmt_to_edges.get(stmt, [])
            # 如果同一语句中有多条边，按它们在语句中的位置排序
            edges_in_stmt.sort(key=lambda e: (
                e.ast.getCstPointer().get('start', {'line': 0}).get("line", 0),
                e.ast.getCstPointer().get('start', {'column': 0}).get("column", 0)
            ))
            for e in edges_in_stmt:
                if e not in matched:
                    # print(f"    Statement at {_get_stmt_position_key(stmt)} contains edge E{e.id}")
                    ordered.append(e)
                    matched.add(e)

        # 处理没有匹配到任何语句的边
        remaining = [e for e in call_edges_in_block if e in effect_set and e not in matched]
        remaining.sort(key=lambda e: e.id)
        for e in remaining:
            # print(f"    Adding remaining edge E{e.id}")
            ordered.append(e)

        # print(f"  Final ordered edges: {[e.id for e in ordered]}")

        # final sanity: all effect edges in this block must be assigned an index (no -1)
        for idx, e in enumerate(ordered):
            setattr(e, "_effect_index", idx)
            setattr(e, "_effect_block", block_ast)
            setattr(e, "_is_effect", True)

        # ensure non-effect call edges have attributes set false
        for e in call_edges_in_block:
            if e not in effect_set:
                setattr(e, "_is_effect", False)
                setattr(e, "_effect_index", None)
                setattr(e, "_effect_block", None)

        # collect results
        all_effect_edges.update(ordered)
        effect_order_map[block_ast] = ordered
        for i, e in enumerate(ordered):
            edge_to_pos[e] = (block_ast, i)

    # Post-pass: ensure no fndef edges are marked effect (they are definitions)
    for e in graph.edges:
        if e.kind == "fndef":
            setattr(e, "_is_effect", False)
            setattr(e, "_effect_index", None)
            setattr(e, "_effect_block", None)

    # Attach to graph
    setattr(graph, "_effect_edges", all_effect_edges)
    setattr(graph, "_effect_order", effect_order_map)
    setattr(graph, "_effect_pos", edge_to_pos)

    return {
        "effect_edges": all_effect_edges,
        "effect_order": effect_order_map,
        "effect_pos": edge_to_pos,
    }