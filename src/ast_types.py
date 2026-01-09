from __future__ import annotations
from typing import Dict, List, Optional, Literal as TypingLiteral

LiteralType = TypingLiteral[
    "integer",
    "float",
    "string",
    "boolean",
    "null",
]

class AstNode:
    def __init__(self):
        self.cstPointer = None

    def setParent(self, parent: AstNode):
        self.parent = parent
        return self
    
    def getParent(self):
        return self.parent
    
    def setCstPointer(self, pointer: dict):
        assert self.cstPointer == None
        self.cstPointer = pointer
        return self
    
    def getCstPointer(self):
        return self.cstPointer

class Expr(AstNode):
    def __init__(self):
        super().__init__()

class Program(AstNode):
    def __init__(self, block: Block):
        super().__init__()
        assert isinstance(block, Block)
        self.block: Block = block

class Stmt(AstNode):
    def __init__(
        self,
        expr: Expr,
        target: Optional[Identifier] = None,
    ):
        super().__init__()
        assert isinstance(expr, Expr)
        assert isinstance(target, Identifier) or target is None
        self.target: Optional[Identifier] = target
        self.expr: Expr = expr
        self.point: Optional[Point] = None

class Block(AstNode):
    def __init__(self, stmts: List[Stmt]):
        super().__init__()
        assert len(stmts) == 0 or isinstance(stmts[0], Stmt)
        self.stmts: List[Stmt] = stmts
        self.block: BlockInfo = None

class Identifier(Expr):
    def __init__(self, name: str):
        super().__init__()
        self.name: str = name
        self.point: Optional[Point] = None
        self.bindphi: Optional[BindPhi] = None


class Literal(Expr):
    def __init__(self, raw: str, type: LiteralType):
        super().__init__()
        self.raw: str = raw
        self.type: LiteralType = type

class ListItem(AstNode):
    def __init__(
        self,
        value: Expr,
        key: Optional[Identifier] = None,
    ):
        super().__init__()
        assert isinstance(value, Expr)
        assert key is None or isinstance(key, Identifier)
        self.key: Optional[Identifier] = key
        self.value: Expr = value

class AstList(Expr):
    def __init__(self, items: List[ListItem]):
        super().__init__()
        assert len(items) == 0 or isinstance(items[0], ListItem)
        self.items: List[ListItem] = items

class Function(Expr):
    def __init__(
        self,
        params: Expr,
        body: Block,
        ret: Optional[Expr] = None,
        ann: Optional[List[Expr]] = None,
    ):
        super().__init__()
        assert isinstance(params, Expr)
        self.params: Expr = params
        assert isinstance(body, Block)
        self.body: Block = body
        assert isinstance(ret, Expr) or ret is None
        self.ret: Optional[Expr] = ret
        assert ann is None or len(ann) == 0 or isinstance(ann[0], Expr)
        self.ann: List[Expr] = ann or []

class Call(Expr):
    def __init__(
        self,
        fn: Expr,
        arg: Expr,
    ):
        super().__init__()
        assert isinstance(fn, Expr)
        self.fn: Expr = fn
        assert isinstance(fn, Expr)
        self.arg: Expr = arg

class BlockInfo:
    def __init__(self, id: int, parent: Optional[BlockInfo], block: Block):
        self.id = id
        self.parent = parent
        self.children: List[BlockInfo] = []
        self.depth = 0 if parent is None else parent.depth + 1

        self.points: List[Point] = []
        self.ast_block = block
    
    def __hash__(self):
        return self.id

class Point:
    def __init__(self,
                 id: int, name: str, typ: str,
                 block: BlockInfo, identifier: Identifier, stmt: Stmt,
                 define_depth: int,):
        self.id = id
        self.name = name
        self.block = block
        self.identifier = identifier
        self.stmt = stmt
        self.define_depth = define_depth
        self.type = typ
        assert typ in ['builtin', 'point', 'symbol']

    def __hash__(self):
        return self.id

class BindPhi:
    def __init__(self, id: int, name: str, entry: Identifier):
        self.id = id
        self.name = name
        self.entry = entry
        # candidates[level] = List[Point]
        self.candidates: Dict[int, set[Point]] = dict()

    def __hash__(self):
        return self.id

    def add(self, point: Point, depth: int = None):
        depth = point.block.depth if depth is None else depth
        if self.candidates.get(depth, None) is None:
            self.candidates[depth] = set([point])
        else:
            self.candidates[depth].add(point)
