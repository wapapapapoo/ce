from typing import List
from ast_types import (
    Program,
    Block,
    Stmt,
    Expr,
    Identifier,
    Literal,
    List as AstList,
    ListItem,
    Function,
    Call,
)

# ==================================================
# CST helpers
# ==================================================

def is_rule(node: dict, name: str) -> bool:
    return node is not None and node.get("node-type") == "rule" and node.get("rule") == name


def is_token(node: dict, token_type: str) -> bool:
    return node is not None and node.get("node-type") == "token" and node.get("token-type") == token_type


def first_rule(node: dict, name: str):
    print(f"called first_rule {name}: ", end='')
    for c in node.get("children", []):
        print(c.get("node-type"), c.get("rule"), is_rule(c, name), end='; ')
        if is_rule(c, name):
            print("find.")
            return c
    print("not find.")
    return None


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
    return Literal(raw=tok["text"], type=ty)


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
        return AstList([])

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
        return AstList([item])

    # (list_element, ...)
    items: List[ListItem] = []
    for child in children:
        if is_rule(child, "list_element"):
            items.append(build_list_item(child))
    return AstList(items)



def build_list_item(cst: dict) -> ListItem:
    # list_element :
    #   list_indexed_element
    # | list_non_indexed_element

    inner = cst["children"][0]

    # indexed: ID : expression
    if is_rule(inner, "list_indexed_element"):
        key_tok = inner["children"][0]          # ID_IDENTIFIER
        value_expr = build_expr(inner["children"][2])
        return ListItem(
            key=Identifier(key_tok["text"]),
            value=value_expr,
        )

    # non-indexed: expression
    if is_rule(inner, "list_non_indexed_element"):
        expr = build_expr(inner["children"][0])
        return ListItem(value=expr, key=None)

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
            return Call(fn=fn, arg=arg)

        # case 2: list
        elif len(arg_list_children) == 1:
            list_node = arg_list_children[0]
            assert is_rule(list_node, 'list')
            arg = build_list(list_node)
            return Call(fn=fn, arg=arg)

        raise RuntimeError(
            "function_arg_list contains neither expression nor list"
        )

    # [expr, expr] common_call
    fn = build_expr(children[1])
    arg = build_expr(children[3])
    return Call(fn=fn, arg=arg)


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
        return Identifier(children[0]["text"])

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
        return build_expr(children[1])

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
    body = build_block(body_wrap[1])

    return Function(
        params=params_expr,
        body=body,
        ret=ret,
        ann=ann,
    )


# ==================================================
# Expression (核心修复点)
# ==================================================

def build_expr(cst: dict) -> Expr:
    # -------- token 直接处理 --------
    if cst["node-type"] == "token":
        # 语义 token
        if cst["token-type"] == "ID_IDENTIFIER":
            return Identifier(cst["text"])

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
    return Program(build_block(block))


def build_block(cst: dict) -> Block:
    stmts: List[Stmt] = []
    for child in cst["children"]:
        if is_rule(child, "statement"):
            stmts.append(build_stmt(child))
    return Block(stmts)


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
        target = Identifier(children[0]["text"])
        value = build_expr(children[2])
        return Stmt(expr=value, target=target)

    # expression-only
    expr = build_expr(children[len(children) - 1])
    return Stmt(expr=expr, target=None)


# ==================================================
# Entry
# ==================================================

def build_ast_entry(cst: dict) -> Program:
    return build_program(cst)
