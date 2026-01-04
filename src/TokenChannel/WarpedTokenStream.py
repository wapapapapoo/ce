from antlr4 import Token
from antlr4.BufferedTokenStream import BufferedTokenStream
from antlr4.Token import CommonToken

BLOCK = 0
PAREN = 1

class WarpedTokenStream(BufferedTokenStream):
    def __init__(self, lexer):
        super().__init__(lexer)
        self.lexer = lexer
        self.mode_stack = [BLOCK]
        self.pending = []

    # ========= 核心 =========
    # def fetch(self, n):
    #     fetched = 0
    #     while fetched < n:
    #         if self.pending:
    #             self.tokens.append(self.pending.pop(0))
    #             fetched += 1
    #             continue

    #         t = self.tokenSource.nextToken()
    #         self._update_mode(t)

    #         if t.type == Token.EOF:
    #             self.tokens.append(t)
    #             fetched += 1
    #             break

    #         if t.type == self.lexer.OP_BIND and self._should_split():
    #             self._split_bind(t)
    #             fetched += 1
    #             continue

    #         self.tokens.append(t)
    #         fetched += 1

    #     return fetched
    def fetch(self, n):
        # Python antlr4 使用 self.index 而不是 self.p
        needed = self.index + n - len(self.tokens)
        if needed <= 0:
            return 0

        fetched = 0
        while fetched < needed:
            if self.pending:
                self.tokens.append(self.pending.pop(0))
                fetched += 1
                continue

            t = self.tokenSource.nextToken()
            self._update_mode(t)

            self.tokens.append(t)
            fetched += 1

            if t.type == Token.EOF:
                break

        return fetched

    # ========= 状态机 =========
    def _update_mode(self, tok):
        l = self.lexer
        if tok.type in (l.LPAREN, l.LBRACK):
            self.mode_stack.append(PAREN)
        elif tok.type == l.LBRACE:
            self.mode_stack.append(BLOCK)
        elif tok.type in (l.RPAREN, l.RBRACK, l.RBRACE):
            if len(self.mode_stack) > 1:
                self.mode_stack.pop()

    def _should_split(self):
        # 规则 1：当前在 PAREN
        if self.mode_stack[-1] == PAREN:
            return True

        # 规则 2：语义前一个 token 是 RPAREN（忽略 WS）
        for tok in reversed(self.tokens):
            if tok.channel == Token.HIDDEN_CHANNEL:
                continue
            return tok.type == self.lexer.RPAREN

        return False


    # ========= 拆 := =========
    def _split_bind(self, bind_tok):
        # 1) 先吐 COLON
        colon = self._clone(bind_tok, self.lexer.COLON, ":")
        self.tokens.append(colon)

        # 2) RHS 一定以 "=" 开头
        text = "="

        while True:
            nxt = self.tokenSource.nextToken()
            self._update_mode(nxt)

            # EOF 或 WS：停
            if nxt.type == Token.EOF or nxt.channel == Token.HIDDEN_CHANNEL:
                self.pending.append(nxt)
                break

            # 只要是连续 token（无 WS），都并进来
            if nxt.type in (
                self.lexer.INTEGER_CONSTANT,
                self.lexer.ID_IDENTIFIER,
            ) or nxt.text == "=":
                text += nxt.text
                continue

            # 不可并：回退
            self.pending.append(nxt)
            break

        merged = self._clone(bind_tok, self.lexer.ID_IDENTIFIER, text)
        self.pending.insert(0, merged)

    # ========= clone =========
    def _clone(self, src, ttype, text):
        tok = CommonToken(
            source=(self.tokenSource, self.tokenSource.inputStream),
            type=ttype,
            channel=Token.DEFAULT_CHANNEL,
            start=src.start,
            stop=src.stop,
        )
        tok.text = text
        tok.line = src.line
        tok.column = src.column
        return tok
