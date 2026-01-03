lexer grammar CommentLexer;

/*
 * ---------- comments ----------
 */

LINE_COMMENT
    : '//' ~[\n]* -> channel(HIDDEN)
    ;

BLOCK_COMMENT
    : '/*' .*? '*/' -> channel(HIDDEN)
    ;
