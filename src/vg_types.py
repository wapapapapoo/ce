from __future__ import annotations
from typing import Dict, List, Optional, Set, Literal, Union

from ast_types import (
    AstNode, Expr, Identifier, Literal as AstLiteral,
    AstList, Function, Call, Block, BindPhi
)

ValueKind = Literal[
    "literal",   # 字面量
    "symbol",    # 编译期符号
    "block",     # block (视为特殊的symbol)
    "expr",      # 计算结果, 指向identifier/expr, 若不是builtin, 则必然是一个Edge的输出
]

EdgeKind = Literal[
    "call",      # 函数调用
    "listdef",   # list 构造, (a: 123, 456, x)展开为listdef(kvdef(symbol a, literal 123), literal 456, expr x)
    "kvdef",     # key-value 构造
    "fndef",     # 函数定义, (a: i32, b: i32): i32 => !pure { +(a, b); }展开为fndef(listdef(kvdef(symbol a, expr i32), kvdef(symbol b, expr i32)), expr i32, listdef(expr !pure), block <block ref>)
]

# ============================================================
# ValueNode —— 图中的“值”
# ============================================================

class ValueNode:
    """
    SSA / Value Graph 中的“值节点”

    约束：
    - kind != "expr" → 绝不能有 in_edge
    - kind == "expr" → 必须恰好由一个 edge 产生, 或者必须在builtin里(即有point且depth=-1)
    """
    def __init__(
        self,
        id: int,
        *,
        kind: ValueKind,
        ast: Optional[Union[
            AstLiteral, Identifier, Expr, AstList, Function, Block
        ]],
        cst: Optional[dict],
        placeholder: bool = False,
    ):
        self.id: int = id # unique id
        self.kind: ValueKind = kind
        # 指向 AST / CST
        self.ast: Optional[Union[
            AstLiteral, Identifier, Expr, AstList, Function, Block
        ]] = ast
        self.cst: Optional[dict] = cst
        # SSA
        self.in_edge: Optional[Edge] = None     # 只有 expr 才有
        self.out_edges: List[BindPhi] = []      # 可能被哪些 edge 使用
        self.placeholder = placeholder

        assert kind in {"literal","symbol","block","expr"}
        if kind != "expr":
            assert self.in_edge is None

# ============================================================
# PhiNode —— “未 resolve 的引用”, 不是phi函数, 严禁多个Edge点位共用
# ============================================================

class PhiNode:
    """
    phi list: 表示“这个位置可能引用的值集合”

    核心语义:
    - identity = AST 中某个 Identifier 的出现
    - 不代表函数、不代表 symbol、不代表 value
    """
    def __init__(
        self,
        id: int,
        *,
        identifier: Identifier,
        bindphi: Optional[BindPhi],
        placeholder: bool = False,
    ):
        self.id: int = id
        # 对应的 AST identifier/bindphi
        self.identifier: Identifier = identifier
        self.bindphi: Optional[BindPhi] = bindphi
        # level -> 可能的 ValueNode
        self.candidates: Dict[int, Set[ValueNode]] = {}
        self.placeholder = placeholder

    def add(self, level: int, value: ValueNode):
        self.candidates.setdefault(level, set()).add(value)

# ============================================================
# Edge —— 唯一的“计算”
# ============================================================

class Edge:
    """
    一个计算关系：

        inputs (φ...) + transform (φ)
            -------- Edge(kind) -------->
                    output (ValueNode)

    约束：
    - output.kind == "expr"
    - transform / inputs 全是 PhiNode
    """
    def __init__(
        self,
        id: int,
        *,
        kind: EdgeKind,
        output: ValueNode,
        transform: Optional[PhiNode],
        inputs: List[PhiNode],
        ast: Union[Call, AstList, Function, Block],
    ):
        self.id: int = id
        self.kind: EdgeKind = kind

        self.output: ValueNode = output
        self.transform: Optional[PhiNode] = transform # if kind is call, must not null
        self.inputs: List[PhiNode] = inputs

        # 对应的 AST 节点（call / list / function / ）
        self.ast: Union[Call, AstList, Function, Block] = ast

        assert kind in {"call","listdef","kvdef","fndef"}
        assert output.kind == "expr"
        assert output.in_edge is None

        output.in_edge = self



class ValueGraph:
    def __init__(self):
        self.values: List[ValueNode] = []
        self.phis: List[PhiNode] = []
        self.edges: List[Edge] = []

        self._vid = 0
        self._pid = 0
        self._eid = 0

        self.type_values: List[ValueNode] = []

    # ---------------- Value ----------------

    def new_value(
        self,
        *,
        kind: ValueKind,
        ast: Optional[AstNode],
        cst: Optional[dict],
        placeholder: bool = False,
    ) -> ValueNode:
        v = ValueNode(
            id=self._vid,
            kind=kind,
            ast=ast,
            cst=cst,
            placeholder=placeholder,
        )
        self._vid += 1
        self.values.append(v)
        return v

    # ---------------- Phi ----------------

    def new_phi(
        self,
        *,
        identifier: Identifier,
        bindphi: Optional[BindPhi],
        placeholder: bool = False,
    ) -> PhiNode:
        p = PhiNode(
            id=self._pid,
            identifier=identifier,
            bindphi=bindphi,
            placeholder=placeholder,
        )
        self._pid += 1
        self.phis.append(p)
        return p

    # ---------------- Edge ----------------

    def new_edge(
        self,
        *,
        kind: EdgeKind,
        output: ValueNode,
        transform: Optional[PhiNode],
        inputs: List[PhiNode],
        ast: AstNode,
    ) -> Edge:
        e = Edge(
            id=self._eid,
            kind=kind,
            output=output,
            transform=transform,
            inputs=inputs,
            ast=ast,
        )
        self._eid += 1
        self.edges.append(e)
        return e

    def value_of_expr(self, expr):
        for v in self.values:
            if v.ast is expr:
                return v
        return None
