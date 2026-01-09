from typing import Dict, List, Optional
from ast_types import AstList, BindPhi, Block, BlockInfo, Call, Expr, Function, Identifier, Literal, Point, Program, Stmt
from intr import INTRINSIC

def build_bdg(ast: Program):
    block_index: List[BlockInfo] = []
    point_index: List[Point] = []
    bindphi_index: List[BindPhi] = []

    block_id = 0
    point_id = 0
    bindphi_id = 0

    # =============================
    # builtin identifiers (depth = -1)
    # =============================
    builtin_scope: Dict[str, set[Point]] = {}

    def add_builtin(name: str):
        nonlocal point_id
        fake_block = None
        fake_ident = Identifier(name)
        fake_stmt = None
        p = Point(
            id=point_id,
            name=name,
            block=None,
            identifier=fake_ident,
            stmt=fake_stmt,
            define_depth=-1,
            typ='builtin'
        )
        point_id += 1
        fake_ident.point = p
        builtin_scope.setdefault(name, set()).add(p)
        point_index.append(p)

    # 你可以在这里预置 builtin
    for intr in INTRINSIC:
        add_builtin(intr)

    # =============================
    # helpers
    # =============================
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
        block: Optional[BlockInfo],
        ident: Identifier,
        stmt: Optional[Stmt],
        depth: int,
        typ: str,
    ) -> Point:
        nonlocal point_id
        p = Point(
            id=point_id,
            name=name,
            block=block,
            identifier=ident,
            stmt=stmt,
            define_depth=depth,
            typ=typ,
        )
        point_id += 1
        assert ident.bindphi is None
        ident.point = p
        point_index.append(p)
        if block is not None:
            block.points.append(p)
        return p

    def new_bindphi(name: str, entry: Identifier) -> BindPhi:
        nonlocal bindphi_id
        bp = BindPhi(bindphi_id, name, entry)
        bindphi_id += 1
        bindphi_index.append(bp)
        return bp

    # =============================
    # Phase 1: build block tree + stmt target points
    # =============================
    def visit_block(block: Block, parent: Optional[BlockInfo]):
        bi = new_block(parent, block)

        # stmt targets: simultaneous
        for stmt in block.stmts:
            if stmt.target:
                p = new_point(
                    name=stmt.target.name,
                    block=bi,
                    ident=stmt.target,
                    stmt=stmt,
                    depth=bi.depth,
                    typ='point',
                )
                stmt.point = p

        # visit RHS
        for stmt in block.stmts:
            visit_expr(stmt.expr, bi)

    # =============================
    # Phase 2: identifier resolution
    # =============================
    def resolve_identifier(ident: Identifier, bi: BlockInfo):
        # 已经是定义位（target / key / builtin）
        if ident.point is not None:
            return

        # 已经解析过 use
        if ident.bindphi is not None:
            return

        bp = new_bindphi(ident.name, ident)

        # symbol scope (depth = -2)
        for p in symbol_scope.get(ident.name, []):
            bp.add(p, depth=-2)

        # block scopes
        cur = bi
        while cur:
            for p in cur.points:
                if p.name == ident.name:
                    bp.add(p, depth=cur.depth)
            cur = cur.parent

        # builtin (depth = -1)
        for p in builtin_scope.get(ident.name, []):
            bp.add(p, depth=-1)

        ident.bindphi = bp


    # =============================
    # Phase 3: expression traversal
    # =============================
    symbol_scope: Dict[str, set[Point]] = {}

    def visit_expr(expr: Expr, bi: BlockInfo):
        if isinstance(expr, Identifier):
            resolve_identifier(expr, bi)

        elif isinstance(expr, Literal):
            return

        elif isinstance(expr, Call):
            visit_expr(expr.fn, bi)
            visit_expr(expr.arg, bi)

        elif isinstance(expr, AstList):
            for item in expr.items:
                if item.key:
                    # symbol
                    p = new_point(
                        name=item.key.name,
                        block=None,
                        ident=item.key,
                        stmt=None,
                        depth=-2,
                        typ='symbol'
                    )
                    symbol_scope.setdefault(item.key.name, set()).add(p)
                visit_expr(item.value, bi)

        elif isinstance(expr, Function):
            # params are in outer block
            visit_expr(expr.params, bi)
            # body is new block
            visit_block(expr.body, bi)
            if expr.ret:
                visit_expr(expr.ret, bi)

        else:
            raise NotImplementedError(type(expr))

    # =============================
    # run
    # =============================
    visit_block(ast.block, None)

    return (
        ast,
        block_index,
        point_index,
        bindphi_index,
    )
