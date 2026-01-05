from token_channel.WarpedTokenStream import WarpedTokenStream
from grammar.MainLexer import MainLexer
from grammar.MainParser import MainParser

from antlr4 import InputStream, ParserRuleContext, TerminalNode
import xml.etree.ElementTree as ET
import argparse
import json

def parse_tree_to_dict(node, parser):
    # 非终结符：Parser rule
    if isinstance(node, ParserRuleContext):
        rule_index = node.getRuleIndex()
        rule_name = parser.ruleNames[rule_index]

        return {
            "node-type": "rule",
            "rule": rule_name,
            "start": {
                "line": node.start.line if node.start else None,
                "column": node.start.column if node.start else None,
            },
            "end": {
                "line": node.stop.line if node.stop else None,
                "column": node.stop.column if node.stop else None,
            },
            "children": [
                parse_tree_to_dict(child, parser)
                for child in node.getChildren()
            ]
        }

    # 终结符：Token
    elif isinstance(node, TerminalNode):
        symbol = node.getSymbol()
        token_type = symbol.type

        return {
            "node-type": "token",
            "text": symbol.text,
            "token-type": parser.symbolicNames[token_type],
            "token-type-id": token_type,
            "channel": symbol.channel,
            "line": symbol.line,
            "column": symbol.column,
        }

    else:
        raise TypeError(f"Unknown node type: {type(node)}")

def parse_tree_to_xml(node, parser):
    # rule node
    if isinstance(node, ParserRuleContext):
        rule_name = parser.ruleNames[node.getRuleIndex()]

        elem = ET.Element("node", {
            "name": rule_name,
            "start-line": str(node.start.line) if node.start else "",
            "start-column": str(node.start.column) if node.start else "",
            "end-line": str(node.stop.line) if node.stop else "",
            "end-column": str(node.stop.column) if node.stop else "",
        })

        for child in node.getChildren():
            elem.append(parse_tree_to_xml(child, parser))

        return elem

    # token node
    elif isinstance(node, TerminalNode):
        sym = node.getSymbol()
        return ET.Element("token", {
            "text": sym.text or "",
            "token-type": parser.symbolicNames[sym.type],
            "token-type-id": str(sym.type),
            "channel": str(sym.channel),
            "line": str(sym.line),
            "column": str(sym.column),
        })

    else:
        raise TypeError(f"Unknown node type: {type(node)}")

def indent_xml(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i

def run_antlr(input_text: str, output_format = "xml"):
    input_stream = InputStream(input_text)
    lexer = MainLexer(input_stream)
    # tokens = CommonTokenStream(lexer)
    tokens = WarpedTokenStream(lexer)
    parser = MainParser(tokens)

    tree = parser.program()
    if output_format == "json":
        ast_dict = parse_tree_to_dict(tree, parser)
        print(json.dumps(ast_dict, indent=2, ensure_ascii=False))

    elif output_format == "xml":
        root = parse_tree_to_xml(tree, parser)
        indent_xml(root)
        print(ET.tostring(root, encoding="unicode"))

def run_ast(args):
    if args.source == "-":
        input_text = sys.stdin.read()
    else:
        with open(args.source, "r", encoding="utf-8") as f:
            input_text = f.read()

    if args.output:
        import sys
        from contextlib import redirect_stdout
        with open(args.output, "w", encoding="utf-8") as f:
            with redirect_stdout(f):
                run_antlr(input_text, 'xml' if args.xml else 'json')
    else:
        run_antlr(input_text, 'xml' if args.xml else 'json')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YAFL Compiler - Yet Another Functional Language")
    parser.add_argument(
        "source",
        help="Source file path, or '-' to read from stdin"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: stdout)",
        default=None
    )
    parser.add_argument(
        "-r", "--antlr",
        help="Run antlr lexer and parser only, get raw AST",
        action="store_true"
    )
    parser.add_argument(
        "-x", "--xml",
        help="Output AST in XML format",
        action="store_true"
    )

    args = parser.parse_args()

    if args.antlr:
        run_ast(args)
