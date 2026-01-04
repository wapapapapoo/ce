from antlr4 import InputStream, CommonTokenStream

from src.TokenChannel.WarpedTokenStream import WarpedTokenStream
from bin.MainLexer import MainLexer
from bin.MainParser import MainParser

import argparse

def run(input_text: str):
    input_stream = InputStream(input_text)
    lexer = MainLexer(input_stream)
    # tokens = CommonTokenStream(lexer)
    tokens = WarpedTokenStream(lexer)
    # parser = MainParser(tokens)

    # tree = parser.file_()
    tokens.fill()
    for t in tokens.tokens:
        print(f"{t.text!r:20} -> {lexer.symbolicNames[t.type]}")


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
                run(input_text)
    else:
        run(input_text)
