lexer grammar StringLexer;

import CommonFragments;

/*
 * ====================== string entry =========================
 */

STRING_CONSTANT
    : SINGLE_QUOTED_STRING
    | DOUBLE_QUOTED_STRING
    | BACKTICK_STRING
    ;

/*
 * ====================== single quoted ========================
 * '...'
 * supports: \' \\ \n \t \r etc.
 */

fragment SINGLE_QUOTED_STRING
    : '\'' SINGLE_QUOTED_CHAR* '\''
    ;

fragment SINGLE_QUOTED_CHAR
    : ESCAPED_CHAR
    | ~['\\\r\n]
    ;

/*
 * ====================== double quoted ========================
 * "..."
 * supports: \" \\ \n \t \r etc.
 */

fragment DOUBLE_QUOTED_STRING
    : '"' DOUBLE_QUOTED_CHAR* '"'
    ;

fragment DOUBLE_QUOTED_CHAR
    : ESCAPED_CHAR
    | ~["\\\r\n]
    ;

/*
 * ====================== backtick ==============================
 * `...`
 * raw string: no escape processing at lexer level
 * allows anything except backtick itself
 */

fragment BACKTICK_STRING
    : '`' BACKTICK_CHAR* '`'
    ;

fragment BACKTICK_CHAR
    : ~[`]
    ;

/*
 * ====================== escape ================================
 */

fragment ESCAPED_CHAR
    : '\\' .
    ;
