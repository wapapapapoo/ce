parser grammar Test;

options {
    tokenVocab = MainLexer;
}

/*
 * Consume tokens one by one, classifying them by type.
 */

file
    : token_item* EOF
    ;

token_item
    : float_const
    | int_const
    | bool_const
    | null_const
    | other_token
    ;

/* ---------- literals ---------- */

float_const
    : FLOAT_CONSTANT
    ;

int_const
    : INTEGER_CONSTANT
    ;

bool_const
    : BOOLEAN_CONSTANT
    ;

null_const
    : NULL_CONSTANT
    ;

/*
 * Catch-all for every other visible token.
 * This MUST be last.
 */
other_token
    : .
    ;
