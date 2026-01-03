lexer grammar CommonFragments;

/*
 * ======================== misc ===============================
 */

fragment FLOATING_SUFFIX
    : [fFlL]
    ;

fragment SIGN
    : [+-]
    ;

/*
 * ======================== digits =============================
 */

fragment DECIMAL_DIGIT
    : [0-9]
    ;

fragment NONZERO_DIGIT
    : [1-9]
    ;

fragment HEX_DIGIT
    : [0-9a-fA-F]
    ;

fragment BIN_DIGIT
    : [01]
    ;

fragment OCT_DIGIT
    : [0-7]
    ;

/*
 * =================== digit sequences =========================
 * underscore allowed ONLY between digits
 */

fragment DECIMAL_DIGITS
    : DECIMAL_DIGIT ('_'? DECIMAL_DIGIT)*
    ;

fragment HEX_DIGITS
    : HEX_DIGIT ('_'? HEX_DIGIT)*
    ;

fragment BIN_DIGITS
    : BIN_DIGIT ('_'? BIN_DIGIT)*
    ;

fragment OCT_DIGITS
    : OCT_DIGIT ('_'? OCT_DIGIT)*
    ;

/*
 * ======================== prefixes ===========================
 */

fragment HEX_PREFIX
    : '0' [xX]
    ;

fragment BIN_PREFIX
    : '0' [bB]
    ;

fragment OCT_PREFIX
    : '0' [oO]
    ;

/*
 * ====================== identifier ===========================
 */

fragment UNICODE_LETTER
    : '\u00A0'..'\uD7FF'
    | '\uF900'..'\uFDCF'
    | '\uFDF0'..'\uFFEF'
    ;

fragment SYMBOL_CHAR
    : [+\-*/<>!?$%&^~|@#.]
    | EQ_NOT_ARROW
    ;

fragment EQ_NOT_ARROW
    : '=' { self._input.LA(1) != ord('>') }?
    ;

fragment DIGIT
    : [0-9]
    ;

fragment ID_START
    : UNICODE_LETTER
    | [a-zA-Z_]
    | SYMBOL_CHAR
    ;

fragment ID_CONTINUE
    : ID_START
    | DIGIT
    ;

/*
 * ====================== whitespace ===========================
 */

fragment WS_CHAR
    : [ \t\r]
    ;

fragment EOL
    : '\n'
    | '\r\n'
    ;