parser grammar Test;

options {
    tokenVocab = MainLexer;
}

file
    : line* EOF
    ;

line
    : number EOL
    ;

number
    : FLOAT_CONSTANT
    | INTEGER_CONSTANT
    ;
