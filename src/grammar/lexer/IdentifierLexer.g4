lexer grammar IdentifierLexer;

import CommonFragments;

/*
 * ---------- identifier ----------
 * generic symbol name
 */

ID_IDENTIFIER
    : ID_START ID_CONTINUE*
    ;
