lexer grammar WhitespaceLexer;

import CommonFragments;

/*
 * ---------- whitespace ----------
 */

WS
    : (WS_CHAR+ | EOL) -> channel(HIDDEN)
    ;