lexer grammar IntegerLexer;

import CommonFragments;

/*
 * entry point
 *
 * - supports decimal / hex / octal / binary
 * - underscore ONLY between digits
 * - C-style suffix: u, l, ll (no underscore before suffix)
 * - octal: 0... and 0o...
 */

INTEGER_CONSTANT
    : DECIMAL_INTEGER INTEGER_SUFFIX?
    | HEX_INTEGER     INTEGER_SUFFIX?
    | OCTAL_INTEGER   INTEGER_SUFFIX?
    | BINARY_INTEGER  INTEGER_SUFFIX?
    ;

/*
 * ---------- decimal ----------
 * 0
 * non-zero leading decimal
 */

fragment DECIMAL_INTEGER
    : '0'
    | NONZERO_DIGIT DECIMAL_TAIL?
    ;

fragment DECIMAL_TAIL
    : ('_'? DECIMAL_DIGIT)+
    ;

/*
 * ---------- hexadecimal ----------
 * 0x...
 */

fragment HEX_INTEGER
    : HEX_PREFIX HEX_DIGITS
    ;

/*
 * ---------- octal ----------
 * 0...
 * 0o...
 */

fragment OCTAL_INTEGER
    : '0' OCTAL_TAIL?
    | OCT_PREFIX OCT_DIGITS
    ;

fragment OCTAL_TAIL
    : OCT_DIGITS
    ;

/*
 * ---------- binary ----------
 * 0b...
 */

fragment BINARY_INTEGER
    : BIN_PREFIX BIN_DIGITS
    ;

/*
 * ---------- suffix ----------
 * strict C-style: directly after digits, no underscore
 */

fragment INTEGER_SUFFIX
    : UNSIGNED_SUFFIX LONG_SUFFIX?
    | LONG_SUFFIX UNSIGNED_SUFFIX?
    ;

fragment UNSIGNED_SUFFIX
    : [uU]
    ;

fragment LONG_SUFFIX
    : [lL] [lL]?
    ;
