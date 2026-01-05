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
    pass

class Expr(AstNode):
    pass

class Program(AstNode):
    def __init__(self, block: Block):
        self.block: Block = block

class Stmt(AstNode):
    def __init__(
        self,
        expr: Expr,
        target: Optional[Identifier] = None,
    ):
        self.target: Optional[Identifier] = target
        self.expr: Expr = expr

class Block(AstNode):
    def __init__(self, stmts: List[Stmt]):
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
        self.key: Optional[Identifier] = key
        self.value: Expr = value

class List(Expr):
    def __init__(self, items: List[ListItem]):
        self.items: List[ListItem] = items

class Function(Expr):
    def __init__(
        self,
        params: Expr,
        body: Block,
        ret: Optional[Expr] = None,
        ann: Optional[List[Expr]] = None,
    ):
        self.params: Expr = params
        self.body: Block = body
        self.ret: Optional[Expr] = ret
        self.ann: List[Expr] = ann or []

class Call(Expr):
    def __init__(
        self,
        fn: Expr,
        arg: Expr,
    ):
        self.fn: Expr = fn
        self.arg: Expr = arg

