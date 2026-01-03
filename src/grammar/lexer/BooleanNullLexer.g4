lexer grammar BooleanNullLexer;

BOOLEAN_CONSTANT
    : TRUE
    | FALSE
    ;

fragment TRUE
    : 'true'
    ;

fragment FALSE
    : 'false'
    ;

NULL_CONSTANT
    : 'null'
    ;
