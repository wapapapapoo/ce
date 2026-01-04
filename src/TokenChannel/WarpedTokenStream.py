from antlr4 import CommonTokenStream, Token
from antlr4.Token import CommonToken
from collections import deque

BLOCK = 0
PAREN = 1


class _WarpedTokenSource:
    def __init__(self, lexer):
        self.lexer = lexer
        self.mode_stack = [BLOCK]
        self.buffer = deque()
        self.prev_sig = None

    # -------- TokenSource API --------

    def nextToken(self):
        if self.buffer:
            tok = self.buffer.popleft()
            if tok.channel == Token.DEFAULT_CHANNEL:
                self.prev_sig = tok
            return tok

        tok = self.lexer.nextToken()

        if tok.type == Token.EOF:
            return tok

        self._update_mode(tok)

        if tok.type == self.lexer.OP_BIND and self._should_split_bind():
            self._split_bind(tok)
            return self.nextToken()

        if tok.channel == Token.DEFAULT_CHANNEL:
            self.prev_sig = tok
        return tok

    def getLine(self):
        return self.lexer.line

    def getCharPositionInLine(self):
        return self.lexer.column

    def getInputStream(self):
        return self.lexer.inputStream

    def getSourceName(self):
        return self.lexer.getSourceName()

    # -------- mode stack --------

    def _update_mode(self, tok):
        l = self.lexer
        t = tok.type

        if t in (l.LPAREN, l.LBRACK):
            self.mode_stack.append(PAREN)
        elif t == l.LBRACE:
            self.mode_stack.append(BLOCK)
        elif t in (l.RPAREN, l.RBRACK, l.RBRACE):
            if len(self.mode_stack) > 1:
                self.mode_stack.pop()

    # -------- decision --------

    def _should_split_bind(self):
        if self.mode_stack[-1] == PAREN:
            return True
        if self.prev_sig and self.prev_sig.type == self.lexer.RPAREN:
            return True
        return False

    # -------- rewrite := --------

    def _split_bind(self, bind_tok):
        l = self.lexer

        # ':' token
        colon = CommonToken(
            source=bind_tok.source,
            type=l.COLON,
            channel=Token.DEFAULT_CHANNEL,
            start=bind_tok.start,
            stop=bind_tok.start
        )
        colon.line = bind_tok.line
        colon.column = bind_tok.column
        self.buffer.append(colon)

        # skip / forward WS
        tok = self.lexer.nextToken()
        while tok.channel == Token.HIDDEN_CHANNEL:
            self.buffer.append(tok)
            tok = self.lexer.nextToken()

        # '=' handling
        if tok.text == "=":
            start = tok.start
            stop = tok.stop
            line = tok.line
            col = tok.column

            nxt = self.lexer.nextToken()

            # =INTEGER or =INTEGERID
            if nxt.type == l.INTEGER_CONSTANT:
                text = "=" + nxt.text
                stop = nxt.stop

                look = self.lexer.nextToken()
                if (
                    look.type == l.ID_IDENTIFIER
                    and look.start == nxt.stop + 1
                ):
                    text += look.text
                    stop = look.stop
                else:
                    self.buffer.append(look)

                eq = CommonToken(
                    source=tok.source,
                    type=l.ID_IDENTIFIER,
                    channel=Token.DEFAULT_CHANNEL,
                    start=start,
                    stop=stop
                )
                eq.text = text
                eq.line = line
                eq.column = col
                self.buffer.append(eq)
                return

            # plain '='
            eq = CommonToken(
                source=tok.source,
                type=l.ID_IDENTIFIER,
                channel=Token.DEFAULT_CHANNEL,
                start=start,
                stop=stop
            )
            eq.text = "="
            eq.line = line
            eq.column = col
            self.buffer.append(eq)
            self.buffer.append(nxt)
            return

        # fallback
        self.buffer.append(tok)


class WarpedTokenStream(CommonTokenStream):
    def __init__(self, lexer):
        self._warped_source = _WarpedTokenSource(lexer)
        super().__init__(self._warped_source)
