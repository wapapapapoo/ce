from antlr4 import *
from bin.MainLexer import MainLexer
from bin.MainParser import MainParser

def run(input_text: str):
    input_stream = InputStream(input_text)
    lexer = MainLexer(input_stream)
    tokens = CommonTokenStream(lexer)
    parser = MainParser(tokens)

    tree = parser.file_()
    tokens.fill()
    for t in tokens.tokens:
        print(f"{t.text!r:20} -> {lexer.symbolicNames[t.type]}")


if __name__ == "__main__":
    with open("test.txt", "r", encoding="utf-8") as f:
        run(f.read())
