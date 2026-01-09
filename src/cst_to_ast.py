from typing import Any, List
from ast_types import (
    Program,
    Block,
    Stmt,
    Expr,
    Identifier,
    Literal,
    AstList,
    ListItem,
    Function,
    Call,
)

import ast

from intr import INTRINSIC

def parse_string_literal(token: str) -> bytes:
    """
    token: lexer 返回的完整 string literal（包含引号）
    return: UTF-8 encoded bytes
    """

    if len(token) < 2:
        raise ValueError("invalid string literal")

    quote = token[0]

    # backtick raw string
    if quote == '`':
        if token[-1] != '`':
            raise ValueError("unterminated backtick string")
        raw = token[1:-1]
        return raw.encode("utf-8")

    # single / double quoted -> Python-style escapes
    if quote in ("'", '"'):
        try:
            # ast.literal_eval 严格按 Python 字符串规则解析
            s = ast.literal_eval(token)
        except Exception as e:
            raise ValueError(f"invalid string literal: {e}")

        if not isinstance(s, str):
            raise ValueError("not a string literal")

        return s.encode("utf-8")

    raise ValueError(f"unknown string delimiter: {quote}")


# ==================================================
# CST helpers
# ==================================================

def is_rule(node: dict, name: str) -> bool:
    return node is not None and node.get("node-type") == "rule" and node.get("rule") == name


def is_token(node: dict, token_type: str) -> bool:
    return node is not None and node.get("node-type") == "token" and node.get("token-type") == token_type


# ==================================================
# Literal
# ==================================================

def build_literal(cst: dict) -> Literal:
    tok = cst["children"][0]
    table = {
        "INTEGER_CONSTANT": "integer",
        "FLOAT_CONSTANT": "float",
        "FLOAT_NAN": "float",
        "FLOAT_INF": "float",
        "STRING_CONSTANT": "string",
        "BOOLEAN_CONSTANT": "boolean",
        "NULL_CONSTANT": "null",
    }
    ty = table.get(tok["token-type"])
    if ty is None:
        raise ValueError(f"unknown literal token: {tok['token-type']}")
    if ty == 'string':
        crlist: list[ListItem] = []
        for ch in parse_string_literal(tok.get('text')):
            kpt = Literal(raw=str(ch), type='integer')
            wrap = ListItem(kpt, key=None)
            kpt.setParent(wrap)
            crlist.append(wrap)
        literal_ast_node = AstList(items=crlist)
        for wrap in crlist:
            wrap.setParent(literal_ast_node)
        literal_ast_node.setCstPointer(cst)
        return literal_ast_node
    literal_ast_node = Literal(raw=tok["text"], type=ty)
    literal_ast_node.setCstPointer(cst)
    return literal_ast_node


# ==================================================
# List / ListItem
# ==================================================

def build_list(cst: dict) -> AstList:
    children = cst["children"]

    # ()
    if (
        len(children) == 2
        and is_token(children[0], "LPAREN")
        and is_token(children[1], "RPAREN")
    ):
        return AstList([]).setCstPointer(cst)

    # (id: expr)
    if (
        len(children) == 3
        and is_token(children[0], "LPAREN")
        and is_rule(children[1], "list_indexed_element")
        and is_token(children[2], "RPAREN")
    ):
        item = build_list_item({
            "node-type": "rule",
            "rule": "list_element",
            "children": [children[1]],
        })
        list_ast_node = AstList([item]).setCstPointer(cst)
        item.setParent(list_ast_node)
        return list_ast_node

    # (list_element, ...)
    items: List[ListItem] = []
    for child in children:
        if is_rule(child, "list_element"):
            items.append(build_list_item(child))
    list_ast_node = AstList(items)
    for child in items:
        child.setParent(list_ast_node)
    return list_ast_node.setCstPointer(cst)



def build_list_item(cst: dict) -> ListItem:
    # list_element :
    #   list_indexed_element
    # | list_non_indexed_element

    inner = cst["children"][0]

    # indexed: ID : expression
    if is_rule(inner, "list_indexed_element"):
        key_tok = inner["children"][0]          # ID_IDENTIFIER
        value_expr = build_expr(inner["children"][2])
        key = build_identifier(key_tok["text"])
        li = ListItem(
            key=key,
            value=value_expr,
        )
        value_expr.setParent(li)
        key.setParent(li)
        key.setCstPointer(key_tok)
        return li.setCstPointer(cst)

    # non-indexed: expression
    if is_rule(inner, "list_non_indexed_element"):
        expr = build_expr(inner["children"][0])
        li = ListItem(value=expr, key=None)
        expr.setParent(li)
        li.setCstPointer(cst)
        return li

    raise RuntimeError("invalid list_element structure")



# ==================================================
# Call
# ==================================================

def build_call(cst: dict) -> Call:
    # function_call :
    #   atom_expression function_arg_list
    # | '[' expression ',' expression ']'

    children = cst["children"]

    # fn(arg)
    if is_rule(children[0], "atom_expression"):
        fn = build_expr(children[0])

        arg_list = children[1]
        assert is_rule(arg_list, 'function_arg_list')
        arg_list_children = arg_list['children']

        # case 1: (expression)
        if len(arg_list_children) == 3:
            expr_node = arg_list_children[1]
            assert is_rule(expr_node, 'expression')
            arg = build_expr(expr_node)
            arg_li = ListItem(value=arg)
            arg_list = AstList([arg_li])
            call = Call(fn=fn, arg=arg_list).setCstPointer(cst)
            arg.setParent(arg_li)
            arg_li.setParent(arg_list)
            arg_list.setParent(call)
            arg_li.setCstPointer(arg_list_children[1])
            arg_list.setCstPointer(arg_list_children[0])
            fn.setParent(call)
            assert isinstance(call.arg, AstList)
            return call

        # case 2: list
        elif len(arg_list_children) == 1:
            list_node = arg_list_children[0]
            assert is_rule(list_node, 'list')
            arg = build_list(list_node)
            call = Call(fn=fn, arg=arg).setCstPointer(cst)
            arg.setParent(call)
            fn.setParent(call)
            assert isinstance(call.arg, AstList)
            return call

        raise RuntimeError(
            "function_arg_list contains neither expression nor list"
        )

    # [expr, expr] common_call
    fn = build_expr(children[1])
    arg = build_expr(children[3])
    call = Call(fn=fn, arg=arg).setCstPointer(cst)
    fn.setParent(call)
    arg.setParent(call)
    assert isinstance(call.arg, Expr)
    return call


# ==================================================
# Function
# ==================================================

def build_function_params(cst: dict) -> Expr:
    # function_params :
    #   ID_IDENTIFIER
    # | list
    # | LPAREN expression RPAREN

    children = cst["children"]

    # case 1: ID_IDENTIFIER
    if len(children) == 1 and is_token(children[0], "ID_IDENTIFIER"):
        return build_identifier(children[0]["text"]).setCstPointer(children[0])

    # case 2: list
    if len(children) == 1 and is_rule(children[0], "list"):
        return build_list(children[0])

    # case 3: ( expression )
    if (
        len(children) == 3
        and is_token(children[0], "LPAREN")
        and is_rule(children[1], "expression")
        and is_token(children[2], "RPAREN")
    ):
        return build_expr(children[1]).setCstPointer(children[1])

    raise RuntimeError(
        "invalid function_params structure, grammar violated"
    )


def build_function(cst: dict) -> Function:
    children = cst["children"]
    idx = 0

    # params（严格按 grammar）
    params_expr = build_function_params(children[idx])
    idx += 1

    # return type
    ret = None
    if idx < len(children) and is_rule(children[idx], "function_return_type"):
        ret = build_expr(children[idx]["children"][1])
        idx += 1

    # OP_ARROW
    idx += 1

    # annotations（atom_expression*，不是 list）
    ann: List[Expr] = []
    while idx < len(children) and is_rule(children[idx], "function_annotations"):
        ann.append(build_expr(children[idx]["children"][0]))
        idx += 1

    # body
    body_wrap = children[idx]['children']
    assert len(body_wrap) == 3
    assert is_rule(body_wrap[1], 'block')
    body = build_block(body_wrap[1]).setCstPointer(body_wrap[1])

    fn = Function(
        params=params_expr,
        body=body,
        ret=ret,
        ann=ann,
    ).setCstPointer(cst)
    params_expr.setParent(fn)
    body.setParent(fn)
    if ret is not None:
        ret.setParent(fn)
    for a in ann:
        a.setParent(fn)
    return fn


# ==================================================
# Expression (核心修复点)
# ==================================================

def build_expr(cst: dict) -> Expr:
    # -------- token 直接处理 --------
    if cst["node-type"] == "token":
        # 语义 token
        if cst["token-type"] == "ID_IDENTIFIER":
            return build_identifier(cst["text"]).setCstPointer(cst)

        # 结构性 token：直接忽略，让上层 rule 负责结构
        if cst["token-type"] in {
            "LPAREN", "RPAREN",
            "LBRACK", "RBRACK",
            "COMMA",
        }:
            raise RuntimeError(
                "structural token leaked into build_expr: "
                f"{cst['token-type']} — grammar glue layer missed a case"
            )

        raise NotImplementedError(
            f"unexpected token in expr: {cst['token-type']}"
        )

    # -------- rule glue --------
    if is_rule(cst, "expression") or is_rule(cst, "atom_expression"):
        # '(' expression ')'
        if (
            len(cst["children"]) == 3
            and is_token(cst["children"][0], "LPAREN")
        ):
            return build_expr(cst["children"][1])

        return build_expr(cst["children"][0])

    if is_rule(cst, "literface"):
        return build_literal(cst)

    if is_rule(cst, "list"):
        return build_list(cst)

    if is_rule(cst, "function"):
        return build_function(cst)

    if is_rule(cst, "function_call"):
        return build_call(cst)

    raise NotImplementedError(
        f"unhandled expr rule: {cst.get('rule')} / node-type={cst.get('node-type')}"
    )


# ==================================================
# Program / Block / Stmt
# ==================================================

def build_program(cst: dict) -> Program:
    block_list = cst.get('children')
    assert len(block_list) == 2
    block = block_list[0]
    assert is_rule(block, 'block')
    block_ast_node = build_block(block)
    block_ast_node.setCstPointer(block)
    program_ast_node = Program(block_ast_node)
    block_ast_node.setParent(program_ast_node)
    return program_ast_node


def build_block(cst: dict) -> Block:
    stmts: List[Stmt] = []
    for child in cst["children"]:
        if is_rule(child, "statement"):
            stmt_ast_node = build_stmt(child)
            stmt_ast_node.setCstPointer(child)
            stmts.append(stmt_ast_node)
    block_ast_node = Block(stmts)
    for stmt in block_ast_node.stmts:
        stmt.setParent(block_ast_node)
    return block_ast_node

def build_stmt(cst: dict) -> Stmt:
    children = cst["children"]
    assert len(children) == 1 or len(children) == 3
    assert is_rule(children[len(children) - 1], 'expression')

    # ID OP_BIND expression
    if (
        len(children) == 3
        and is_token(children[0], "ID_IDENTIFIER")
        and is_token(children[1], "OP_BIND")
    ):
        target = build_identifier(children[0]["text"])
        target.setCstPointer(children[0])
        value = build_expr(children[2])
        stmt_ast_node = Stmt(expr=value, target=target)
        target.setParent(stmt_ast_node)
        value.setParent(stmt_ast_node)
        return stmt_ast_node

    # expression-only
    expr = build_expr(children[len(children) - 1])
    stmt_ast_node = Stmt(expr=expr, target=None)
    expr.setParent(stmt_ast_node)
    return stmt_ast_node

def build_identifier(name: str):
    return Identifier(name)

# ==================================================
# Entry
# ==================================================

def build_ast(cst: dict) -> Program:
    program_ast_node = build_program(cst)
    program_ast_node.setCstPointer(cst)
    return program_ast_node

def dump_ast(node: Any, level: int = 0, INDENT = "  "):
    pad = INDENT * level

    if node is None:
        print(pad + "None")
        return

    cls = node.__class__.__name__
    print(pad + cls)

    # 约定：AST 节点只包含简单字段
    for name, value in vars(node).items():
        print(pad + INDENT + f"{name}:")
        if (name in { 'parent', 'cstPointer' }):
            print(pad + INDENT * 2 + '<recur>')
            continue

        if isinstance(value, list):
            if not value:
                print(pad + INDENT * 2 + "[]")
            else:
                for item in value:
                    dump_ast(item, level + 2)

        elif _is_ast_node(value):
            dump_ast(value, level + 2)

        else:
            print(pad + INDENT * 2 + repr(value))


def _is_ast_node(obj: Any) -> bool:
    return hasattr(obj, "__class__") and hasattr(obj, "__dict__")
