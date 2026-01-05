from tasks.ast import build_ast_entry
from tasks.cst import run_antlr
from tasks.ast_dump import dump_ast

import xml.etree.ElementTree as ET
import argparse
import json

def run_cst(args):
    if args.source == "-":
        input_text = sys.stdin.read()
    else:
        with open(args.source, "r", encoding="utf-8") as f:
            input_text = f.read()

    return run_antlr(input_text)


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

    args = parser.parse_args()

    cst = run_cst(args)
    ast = build_ast_entry(cst)

    if args.output:
        import sys
        from contextlib import redirect_stdout
        with open(args.output, "w", encoding="utf-8") as f:
            with redirect_stdout(f):
                dump_ast(ast)
    else:
        dump_ast(ast)
