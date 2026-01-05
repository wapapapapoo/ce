lexer grammar FloatLexer;

import CommonFragments;

/*
 * entry point
 */
FLOAT_CONSTANT
    : DECIMAL_FLOAT
    | HEX_FLOAT
    | BINARY_FLOAT
    | OCTAL_FLOAT
    ;

/*
 * special float
 */
FLOAT_NAN
    : [nN][aA][nN]
    ;

FLOAT_INF
    : SIGN? [iI][nN][fF]
    | SIGN? [iI][nN][fF][iI][nN]
    | SIGN? [iI][nN][fF][iI][nN][iI][tT][yY]
    ;

/*
 * ---------- decimal floating ----------
 */

fragment DECIMAL_FLOAT
    : SIGN? DECIMAL_FRACTIONAL EXPONENT_PART? FLOATING_SUFFIX?
    | SIGN? DECIMAL_DIGITS EXPONENT_PART FLOATING_SUFFIX?
    ;

fragment DECIMAL_FRACTIONAL
    : DECIMAL_DIGITS? '.' DECIMAL_DIGITS
    | DECIMAL_DIGITS '.'
    ;

/*
 * ---------- hexadecimal floating ----------
 * NOTE: hex float MUST use p/P exponent, e/E is forbidden
 */

fragment HEX_FLOAT
    : SIGN? HEX_PREFIX HEX_FRACTIONAL HEX_EXPONENT_PART? FLOATING_SUFFIX?
    | SIGN? HEX_PREFIX HEX_DIGITS HEX_EXPONENT_PART FLOATING_SUFFIX?
    ;

fragment HEX_FRACTIONAL
    : HEX_DIGITS? '.' HEX_DIGITS
    | HEX_DIGITS '.'
    ;

/*
 * ---------- binary floating ----------
 */

fragment BINARY_FLOAT
    : SIGN? BIN_PREFIX BIN_FRACTIONAL EXPONENT_PART? FLOATING_SUFFIX?
    | SIGN? BIN_PREFIX BIN_DIGITS EXPONENT_PART FLOATING_SUFFIX?
    ;

fragment BIN_FRACTIONAL
    : BIN_DIGITS? '.' BIN_DIGITS
    | BIN_DIGITS '.'
    ;

/*
 * ---------- octal floating ----------
 */

fragment OCTAL_FLOAT
    : SIGN? OCT_PREFIX OCT_FRACTIONAL EXPONENT_PART? FLOATING_SUFFIX?
    | SIGN? OCT_PREFIX OCT_DIGITS EXPONENT_PART FLOATING_SUFFIX?
    ;

fragment OCT_FRACTIONAL
    : OCT_DIGITS? '.' OCT_DIGITS
    | OCT_DIGITS '.'
    ;

/*
 * ---------- exponent ----------
 */

fragment EXPONENT_PART
    : [eEpP] SIGN? DECIMAL_DIGITS
    ;

/* hex-only exponent (no e/E allowed) */
fragment HEX_EXPONENT_PART
    : [pP] SIGN? DECIMAL_DIGITS
    ;

/*
 * ---------- digits with underscore ----------
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
