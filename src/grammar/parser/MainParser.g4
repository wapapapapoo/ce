parser grammar MainParser;

options {
    tokenVocab = MainLexer;
}

program
    : block EOF
    ;

block
    : (statement (SEMICOLON statement)* SEMICOLON?)?
    ;

statement
    : ID_IDENTIFIER OP_BIND expression
    | expression
    ;

literface
    : INTEGER_CONSTANT
    | FLOAT_CONSTANT
    | FLOAT_NAN
    | FLOAT_INF
    | STRING_CONSTANT
    | BOOLEAN_CONSTANT
    | NULL_CONSTANT
    ;

list
    : LPAREN RPAREN
    | LPAREN list_indexed_element RPAREN
    | LPAREN
        list_element
        COMMA
        (list_element (COMMA list_element)*)?
        COMMA?
      RPAREN
    ;

list_indexed_element
    : ID_IDENTIFIER COLON expression
    ;

list_non_indexed_element
    : expression
    ;

list_element
    : list_indexed_element
    | list_non_indexed_element
    ;

function
    : function_params
      function_return_type?
      OP_ARROW
      function_annotations*
      function_body
    ;

function_params
    : ID_IDENTIFIER
    | list
    | LPAREN expression RPAREN
    ;

function_return_type
    : COLON atom_expression
    ;

function_annotations
    : atom_expression
    ;

function_body
    : LBRACE block RBRACE
    ;

function_call
    : atom_expression function_arg_list         # convenient_call
    | function_call function_arg_list           # curry_call
    | LBRACK expression COMMA expression RBRACK # common_call
    ;

function_arg_list
    : list
    | LPAREN expression RPAREN
    ;

expression
    : function_call
    | atom_expression
    ;

atom_expression
    : function
    | literface
    | ID_IDENTIFIER
    | list
    | LPAREN expression RPAREN
    ;
