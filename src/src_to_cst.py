from WarpedTokenStream import WarpedTokenStream
from grammar.MainLexer import MainLexer
from grammar.MainParser import MainParser

from antlr4 import InputStream, ParserRuleContext, TerminalNode
from antlr4.error.Errors import CancellationException
import xml.etree.ElementTree as ET
import json
import logging
from wcwidth import wcwidth

def visual_width(s: str) -> int:
    w = 0
    for ch in s:
        cw = wcwidth(ch)
        if cw > 0:
            w += cw
    return w


def print_error(input_text: str, token):
    lines = input_text.splitlines()
    line_text = lines[token.line - 1]

    lineno = f"{token.line} | "

    # token.column 是字符索引
    prefix = line_text[:token.column]

    caret_offset = visual_width(prefix)
    caret_width = max(1, visual_width(token.text))

    return (
        lineno + line_text + '\n'
        + " " * len(lineno)
        + " " * caret_offset
        + "^" * caret_width
    )



def parse_cst_to_dict(node, parser):
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
                parse_cst_to_dict(child, parser)
                for child in node.getChildren()
            ]
        }

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

def cst_dict_to_xml(node):
    if node["node-type"] == "rule":
        elem = ET.Element("node", {
            "name": node["rule"],
            "start-line": str(node["start"]["line"] or "0"),
            "start-column": str(node["start"]["column"] or "0"),
            "end-line": str(node["end"]["line"] or "0"),
            "end-column": str(node["end"]["column"] or "0"),
        })

        for child in node["children"]:
            elem.append(cst_dict_to_xml(child))

        return elem

    elif node["node-type"] == "token":
        return ET.Element("token", {
            "text": node["text"] or "",
            "token-type": node["token-type"],
            "token-type-id": str(node["token-type-id"]),
            "channel": str(node["channel"]),
            "line": str(node["line"]),
            "column": str(node["column"]),
        })

    else:
        raise ValueError(f"Unknown node-type: {node['node-type']}")

def indent_xml(elem, indent=2, level=0):
    i = "\n" + level * indent * ' '
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + indent * ' '
        for child in elem:
            indent_xml(child, indent, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i

def build_cst(input_text: str):
    logger = logging.getLogger(__name__)

    input_stream = InputStream(input_text)
    lexer = MainLexer(input_stream)
    # tokens = CommonTokenStream(lexer)
    tokens = WarpedTokenStream(lexer)
    parser = MainParser(tokens)
    from antlr4.error.ErrorStrategy import BailErrorStrategy
    parser._errHandler = BailErrorStrategy()

    try:
        tree = parser.program()
    except CancellationException as e:
        earg = e.args[0]
        token = earg.offendingToken
        logger.error(
            f"Syntax Error: Unexpect {parser.symbolicNames[token.type]} token `{token.text}` at line {token.line}:{token.column},\n"
            + print_error(input_text, token))
        raise
    cst_dict = parse_cst_to_dict(tree, parser)
    return cst_dict

def cst_xml_to_dict(elem):
    tag = elem.tag

    if tag == "node":
        return {
            "node-type": "rule",
            "rule": elem.attrib.get("name"),
            "start": {
                "line": int(elem.attrib["start-line"]) if elem.attrib.get("start-line") else None,
                "column": int(elem.attrib["start-column"]) if elem.attrib.get("start-column") else None,
            },
            "end": {
                "line": int(elem.attrib["end-line"]) if elem.attrib.get("end-line") else None,
                "column": int(elem.attrib["end-column"]) if elem.attrib.get("end-column") else None,
            },
            "children": [
                cst_xml_to_dict(child)
                for child in elem
            ]
        }

    elif tag == "token":
        return {
            "node-type": "token",
            "text": elem.attrib.get("text"),
            "token-type": elem.attrib.get("token-type"),
            "token-type-id": int(elem.attrib["token-type-id"]),
            "channel": int(elem.attrib["channel"]),
            "line": int(elem.attrib["line"]),
            "column": int(elem.attrib["column"]),
        }

    else:
        raise ValueError(f"Unknown CST XML tag: {tag}")

def load_cst(path: str, input_format="xml"):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if input_format == "json":
        return json.loads(content)

    elif input_format == "xml":
        root = ET.fromstring(content)
        return cst_xml_to_dict(root)

    else:
        raise ValueError(f"unknown CST format: {input_format}")
