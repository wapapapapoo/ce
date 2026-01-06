from typing import Any, List

INDENT = "  "

def dump_ast(node: Any, level: int = 0):
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
