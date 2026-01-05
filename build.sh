rm -rf ./bin/
mkdir bin
cp -r ./src/* ./bin/

antlr4 -Dlanguage=Python3 -visitor -o bin/grammar bin/grammar/lexer/MainLexer.g4 bin/grammar/parser/MainParser.g4
