from typing import Dict, List, Optional
from ast_types import (
    AstList, BindPhi, Block, BlockInfo, Call, Expr,
    Function, Identifier, Literal, Point, Program, Stmt
)
from intr import INTRINSIC


def build_bdg(ast: Program):
    block_index: List[BlockInfo] = []
    point_index: List[Point] = []
    bindphi_index: List[BindPhi] = []

    block_id = 0
    point_id = 0
    bindphi_id = 0

    # ==================================================
    # builtin identifiers (depth = -1)
    # ==================================================
    builtin_scope: Dict[str, set[Point]] = {}

    def add_builtin(name: str):
        nonlocal point_id
        ident = Identifier(name)
        p = Point(
            point_id,
            name,
            'builtin',
            None,
            ident,
            None,
            -1,
        )
        point_id += 1
        ident.point = p
        builtin_scope.setdefault(name, set()).add(p)
        point_index.append(p)

    for intr in INTRINSIC:
        add_builtin(intr)

    # ==================================================
    # helpers
    # ==================================================
    def new_block(parent: Optional[BlockInfo], block: Block) -> BlockInfo:
        nonlocal block_id
        bi = BlockInfo(block_id, parent, block)
        block_id += 1
        block.block = bi
        if parent:
            parent.children.append(bi)
        block_index.append(bi)
        return bi

    def new_point(
        name: str,
        typ: str,
        block: Optional[BlockInfo],
        ident: Identifier,
        stmt: Optional[Stmt],
        depth: int,
    ) -> Point:
        nonlocal point_id
        p = Point(
            point_id,
            name,
            typ,
            block,
            ident,
            stmt,
            depth,
        )
        point_id += 1
        ident.point = p
        point_index.append(p)
        if block:
            block.points.append(p)
        return p

    def new_bindphi(name: str, entry: Identifier) -> BindPhi:
        nonlocal bindphi_id
        bp = BindPhi(bindphi_id, name, entry)
        bindphi_id += 1
        bindphi_index.append(bp)
        return bp

    # ==================================================
    # Phase 0: 全程序 symbol 扫描（AstList.key）
    # ==================================================
    symbol_scope: Dict[str, set[Point]] = {}

    def scan_symbols_expr(expr: Expr):
        if isinstance(expr, AstList):
            for item in expr.items:
                if item.key:
                    p = new_point(
                        item.key.name,
                        'symbol',
                        None,
                        item.key,
                        None,
                        -2,
                    )
                    symbol_scope.setdefault(item.key.name, set()).add(p)
                scan_symbols_expr(item.value)

        elif isinstance(expr, Call):
            scan_symbols_expr(expr.fn)
            scan_symbols_expr(expr.arg)

        elif isinstance(expr, Function):
            scan_symbols_expr(expr.params)
            if expr.ret:
                scan_symbols_expr(expr.ret)
            scan_symbols_block(expr.body)

        elif isinstance(expr, (Identifier, Literal)):
            return

        else:
            raise NotImplementedError(type(expr))

    def scan_symbols_block(block: Block):
        for stmt in block.stmts:
            scan_symbols_expr(stmt.expr)

    scan_symbols_block(ast.block)

    # ==================================================
    # Phase 1: 构建 block 树 + block 内 point（无顺序）
    # ==================================================
    def build_blocks(block: Block, parent: Optional[BlockInfo]):
        bi = new_block(parent, block)

        # stmt targets
        for stmt in block.stmts:
            if stmt.target:
                new_point(
                    stmt.target.name,
                    'point',
                    bi,
                    stmt.target,
                    stmt,
                    bi.depth,
                )

        # children blocks
        for stmt in block.stmts:
            if isinstance(stmt.expr, Function):
                build_blocks(stmt.expr.body, bi)

    build_blocks(ast.block, None)

    # ==================================================
    # Phase 2: identifier resolve（按 block depth BFS）
    # ==================================================
    def resolve_identifier(ident: Identifier, bi: BlockInfo):
        if ident.point or ident.bindphi:
            return

        bp = new_bindphi(ident.name, ident)

        # symbol
        for p in symbol_scope.get(ident.name, []):
            bp.add(p, depth=-2)

        # block chain
        cur = bi
        while cur:
            for p in cur.points:
                if p.name == ident.name:
                    bp.add(p, depth=cur.depth)
            cur = cur.parent

        # builtin
        for p in builtin_scope.get(ident.name, []):
            bp.add(p, depth=-1)

        ident.bindphi = bp

    def resolve_expr(expr: Expr, bi: BlockInfo):
        if isinstance(expr, Identifier):
            resolve_identifier(expr, bi)

        elif isinstance(expr, Literal):
            return

        elif isinstance(expr, Call):
            resolve_expr(expr.fn, bi)
            resolve_expr(expr.arg, bi)

        elif isinstance(expr, AstList):
            for item in expr.items:
                resolve_expr(item.value, bi)

        elif isinstance(expr, Function):
            resolve_expr(expr.params, bi)
            if expr.ret:
                resolve_expr(expr.ret, bi)
            # body later by BFS

        else:
            raise NotImplementedError(type(expr))

    for bi in sorted(block_index, key=lambda b: b.depth):
        for stmt in bi.ast_block.stmts:
            resolve_expr(stmt.expr, bi)

    return ast, block_index, point_index, bindphi_index
