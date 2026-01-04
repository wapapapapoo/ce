rm -rf ./bin/

antlr4 -Dlanguage=Python3 -visitor -o bin/ src/grammar/lexer/MainLexer.g4 src/grammar/parser/MainParser.g4