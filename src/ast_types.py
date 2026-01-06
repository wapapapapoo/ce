from __future__ import annotations
from typing import List, Optional, Literal as TypingLiteral

LiteralType = TypingLiteral[
    "integer",
    "float",
    "string",
    "boolean",
    "null",
]

class AstNode:
    def setParent(self, parent: AstNode):
        self.parent = parent
        return self
    
    def getParent(self):
        return self.parent
    
    def setCstPointer(self, pointer: dict):
        self.cstPointer = pointer
        return self
    
    def getCstPointer(self):
        return self.cstPointer

class Expr(AstNode):
    pass

class Program(AstNode):
    def __init__(self, block: Block):
        assert isinstance(block, Block)
        self.block: Block = block

class Stmt(AstNode):
    def __init__(
        self,
        expr: Expr,
        target: Optional[Identifier] = None,
    ):
        assert isinstance(expr, Expr)
        assert isinstance(target, Identifier) or target is None
        self.target: Optional[Identifier] = target
        self.expr: Expr = expr

class Block(AstNode):
    def __init__(self, stmts: List[Stmt]):
        assert len(stmts) == 0 or isinstance(stmts[0], Stmt)
        self.stmts: List[Stmt] = stmts

class Identifier(Expr):
    def __init__(self, name: str):
        self.name: str = name


class Literal(Expr):
    def __init__(self, raw: str, type: LiteralType):
        self.raw: str = raw
        self.type: LiteralType = type

class ListItem(AstNode):
    def __init__(
        self,
        value: Expr,
        key: Optional[Identifier] = None,
    ):
        assert isinstance(value, Expr)
        assert key is None or isinstance(key, Identifier)
        self.key: Optional[Identifier] = key
        self.value: Expr = value

class AstList(Expr):
    def __init__(self, items: List[ListItem]):
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
        assert isinstance(fn, Expr)
        self.fn: Expr = fn
        assert isinstance(fn, Expr)
        self.arg: Expr = arg
