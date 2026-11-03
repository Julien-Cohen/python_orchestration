"""Recursive-descent parser for the workflow language.

Grammar (informal EBNF)::

    workflow   := step* EOF
    step       := 'first' 'start' ';'
                | 'then'? ( init | input | output | action | loop )
    init       := 'init' name ':=' expr ';'
    input      := 'input'  name ':' type ';'
    output     := 'output' name ':' type ';'
    action     := 'action' name (':' name)? ('x' INT)? ('with' name)?
                  ( '{' member* '}' | ';' )
    member     := ':>>' name ('=' | ':') expr ';'
                | ('in' | 'out') name ':' type ';'
    loop       := 'loop' 'action'? name ('with' 'max' INT 'retries')?
                  '{' step* '}' ('until' expr ';')?
    type       := name multiplicity?
    multiplicity := '*' | '+' | '?' | '[' INT ('..' (INT | '*'))? ']'
    expr       := STRING | INT | FLOAT | 'true' | 'false' | name
    name       := (IDENT | QNAME) ('::' (IDENT | QNAME))*

Fault tolerance (reported as warnings, or as errors with ``strict=True``):
  * a statement may end with '.' instead of ';'
  * the ';' may be missing when the next token clearly starts something new
  * 'then' may be omitted before a step keyword
"""

import re
from typing import Optional

from pydantic import ValidationError

from . import nodes as n
from .errors import Diagnostic, ParseError
from .lexer import Token, tokenize

_REPEAT_RE = re.compile(r"[xX](\d+)\Z")

STEP_KEYWORDS = frozenset({"init", "input", "output", "action", "loop"})
STEP_FOLLOWERS = frozenset({"then"})
MEMBER_FOLLOWERS = frozenset({":>>", "in", "out"})


def describe(tok: Token) -> str:
    if tok.kind == "EOF":
        return "end of file"
    if tok.kind == "STRING":
        return f"string {tok.text}"
    return f"'{tok.text}'"


class Parser:
    def __init__(self, source: str, *, strict: bool = False) -> None:
        self.source = source
        self.strict = strict
        self.tokens = tokenize(source)
        self.pos = 0
        self.warnings: list[Diagnostic] = []

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    @property
    def cur(self) -> Token:
        return self.tokens[self.pos]

    @property
    def prev(self) -> Token:
        return self.tokens[max(self.pos - 1, 0)]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.kind != "EOF":
            self.pos += 1
        return tok

    def accept_sym(self, sym: str) -> Optional[Token]:
        return self.advance() if self.cur.is_sym(sym) else None

    def accept_kw(self, word: str) -> Optional[Token]:
        return self.advance() if self.cur.is_kw(word) else None

    def accept_word(self, word: str) -> Optional[Token]:
        return self.advance() if self.cur.is_word(word) else None

    def error(self, message: str, tok: Optional[Token] = None, hint: Optional[str] = None) -> ParseError:
        tok = tok or self.cur
        return ParseError(message, tok.loc, self.source, hint)

    def warn(self, message: str, tok: Token) -> None:
        if self.strict:
            raise self.error(message, tok)
        self.warnings.append(Diagnostic(message, tok.loc))

    def expect_sym(self, sym: str) -> Token:
        if not self.cur.is_sym(sym):
            raise self.error(f"expected '{sym}', found {describe(self.cur)}")
        return self.advance()

    def expect_kw(self, word: str) -> Token:
        if not self.cur.is_kw(word):
            raise self.error(f"expected '{word}', found {describe(self.cur)}")
        return self.advance()

    def expect_word(self, word: str) -> Token:
        if not self.cur.is_word(word):
            raise self.error(f"expected '{word}', found {describe(self.cur)}")
        return self.advance()

    def expect_int(self) -> int:
        if self.cur.kind != "INT":
            raise self.error(f"expected an integer, found {describe(self.cur)}")
        return self.advance().value

    def end_statement(self, followers: frozenset = STEP_FOLLOWERS) -> None:
        tok = self.cur
        if tok.is_sym(";"):
            self.advance()
        elif tok.is_sym("."):
            self.warn("'.' used as statement terminator; ';' expected", tok)
            self.advance()
        elif (
            tok.kind == "EOF"
            or tok.is_sym("}")
            or (tok.kind in ("KW", "SYM") and tok.value in followers)
        ):
            self.warn("missing ';' at end of statement", self.prev)
        else:
            raise self.error(f"expected ';', found {describe(tok)}")

    # ------------------------------------------------------------------
    # Names, types, expressions
    # ------------------------------------------------------------------

    def parse_name(self, what: str = "a name") -> str:
        parts = []
        while True:
            tok = self.cur
            if tok.kind not in ("IDENT", "QNAME"):
                raise self.error(f"expected {what}, found {describe(tok)}")
            parts.append(self.advance().value)
            if not self.accept_sym("::"):
                return "::".join(parts)

    def parse_multiplicity(self) -> Optional[n.Multiplicity]:
        tok = self.cur
        if tok.is_sym("*"):
            self.advance()
            return n.Multiplicity(lower=0, upper=None, loc=tok.loc)
        if tok.is_sym("+"):
            self.advance()
            return n.Multiplicity(lower=1, upper=None, loc=tok.loc)
        if tok.is_sym("?"):
            self.advance()
            return n.Multiplicity(lower=0, upper=1, loc=tok.loc)
        if tok.is_sym("["):
            self.advance()
            lower = self.expect_int()
            upper: Optional[int] = lower
            if self.accept_sym(".."):
                upper = None if self.accept_sym("*") else self.expect_int()
            self.expect_sym("]")
            try:
                return n.Multiplicity(lower=lower, upper=upper, loc=tok.loc)
            except ValidationError:
                raise self.error(f"invalid multiplicity: upper bound is below lower bound {lower}", tok)
        return None

    def parse_type_ref(self) -> n.TypeRef:
        loc = self.cur.loc
        name = self.parse_name("a type name")
        return n.TypeRef(name=name, multiplicity=self.parse_multiplicity(), loc=loc)

    def parse_expr(self) -> n.Expression:
        tok = self.cur
        if tok.kind == "STRING":
            self.advance()
            return n.StringLiteral(value=tok.value, loc=tok.loc)
        if tok.kind in ("INT", "FLOAT"):
            self.advance()
            return n.NumberLiteral(value=tok.value, loc=tok.loc)
        if tok.is_kw("true") or tok.is_kw("false"):
            self.advance()
            return n.BoolLiteral(value=tok.value == "true", loc=tok.loc)
        if tok.kind in ("IDENT", "QNAME"):
            return n.Reference(name=self.parse_name(), loc=tok.loc)
        raise self.error(f"expected an expression, found {describe(tok)}")

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def parse_workflow(self) -> n.Workflow:
        loc = self.cur.loc
        steps: list = []
        while self.cur.kind != "EOF":
            steps.append(self.parse_step())
        return n.Workflow(steps=steps, loc=loc)

    def parse_step(self):
        tok = self.cur

        if tok.is_kw("first"):
            self.advance()
            self.expect_kw("start")
            self.end_statement()
            return n.StartStep(loc=tok.loc)

        if tok.is_kw("then"):
            self.advance()
        elif tok.kind == "KW" and tok.value in STEP_KEYWORDS:
            self.warn("missing 'then' before step", tok)
        else:
            hint = "there is an unmatched '}'" if tok.is_sym("}") else None
            raise self.error(f"expected 'then' to start a step, found {describe(tok)}", hint=hint)

        tok = self.cur
        if tok.is_kw("init"):
            return self.parse_init()
        if tok.is_kw("input"):
            return self.parse_io(n.InputStep)
        if tok.is_kw("output"):
            return self.parse_io(n.OutputStep)
        if tok.is_kw("action"):
            return self.parse_action()
        if tok.is_kw("loop"):
            return self.parse_loop()
        raise self.error(
            f"expected 'init', 'input', 'output', 'action' or 'loop' after 'then', found {describe(tok)}"
        )

    def parse_init(self) -> n.InitStep:
        start = self.advance()
        name = self.parse_name("a variable name")
        self.expect_sym(":=")
        value = self.parse_expr()
        self.end_statement()
        return n.InitStep(name=name, value=value, loc=start.loc)

    def parse_io(self, cls):
        start = self.advance()
        name = self.parse_name("a parameter name")
        self.expect_sym(":")
        type_ref = self.parse_type_ref()
        self.end_statement()
        return cls(name=name, type=type_ref, loc=start.loc)

    def parse_action(self) -> n.ActionStep:
        start = self.advance()
        name = self.parse_name("an action name")

        type_name: Optional[str] = None
        if self.accept_sym(":"):
            type_name = self.parse_name("a type name")

        repeat: Optional[int] = None
        match = _REPEAT_RE.match(self.cur.value) if self.cur.kind == "IDENT" else None
        if match:
            self.advance()
            repeat = int(match.group(1))

        aggregation: Optional[str] = None
        if self.accept_kw("with"):
            aggregation = self.parse_name("an aggregation name")

        members: list = []
        if self.cur.is_sym("{"):
            open_tok = self.advance()
            while not self.cur.is_sym("}"):
                if self.cur.kind == "EOF":
                    raise self.error(
                        f"end of file inside the body of action '{name}'",
                        hint=f"the '{{' at line {open_tok.loc.line} is never closed",
                    )
                members.append(self.parse_member())
            self.advance()
        else:
            self.end_statement()

        return n.ActionStep(
            name=name, type=type_name, repeat=repeat, aggregation=aggregation, members=members, loc=start.loc
        )

    def parse_member(self):
        tok = self.cur

        if tok.is_sym(":>>"):
            self.advance()
            name = self.parse_name("a feature name")
            op_tok = self.cur
            if not (op_tok.is_sym("=") or op_tok.is_sym(":")):
                raise self.error(f"expected '=' or ':', found {describe(op_tok)}")
            self.advance()
            value = self.parse_expr()
            self.end_statement(MEMBER_FOLLOWERS)
            return n.Redefinition(name=name, operator=op_tok.value, value=value, loc=tok.loc)

        if tok.is_kw("in") or tok.is_kw("out"):
            self.advance()
            name = self.parse_name("a parameter name")
            self.expect_sym(":")
            type_ref = self.parse_type_ref()
            self.end_statement(MEMBER_FOLLOWERS)
            return n.Parameter(direction=tok.value, name=name, type=type_ref, loc=tok.loc)

        raise self.error(f"expected ':>>', 'in' or 'out', found {describe(tok)}")

    def parse_loop(self) -> n.LoopStep:
        start = self.advance()
        self.accept_kw("action")
        name = self.parse_name("a loop name")

        max_retries: Optional[int] = None
        if self.accept_kw("with"):
            self.expect_word("max")
            max_retries = self.expect_int()
            if not (self.accept_word("retries") or self.accept_word("retry")):
                raise self.error(f"expected 'retries', found {describe(self.cur)}")

        open_tok = self.expect_sym("{")
        body: list = []
        while not self.cur.is_sym("}"):
            tok = self.cur
            if tok.kind == "EOF":
                raise self.error(
                    f"end of file inside the body of loop '{name}'",
                    hint=f"the '{{' at line {open_tok.loc.line} is never closed",
                )
            if tok.is_kw("until"):
                raise self.error(
                    f"unexpected 'until' inside the body of loop '{name}'",
                    hint=(
                        f"loop '{name}' (opened at line {open_tok.loc.line}) is still open: "
                        f"a '}}' is probably missing before this 'until'"
                    ),
                )
            body.append(self.parse_step())
        self.advance()

        until: Optional[n.Expression] = None
        if self.accept_kw("until"):
            until = self.parse_expr()
            self.end_statement()

        return n.LoopStep(name=name, max_retries=max_retries, body=body, until=until, loc=start.loc)


# ----------------------------------------------------------------------
# Convenience functions
# ----------------------------------------------------------------------


def parse(source: str, *, strict: bool = False) -> n.Workflow:
    """Parse source text into a Workflow. Raises LexError / ParseError."""
    return Parser(source, strict=strict).parse_workflow()


def parse_with_warnings(source: str, *, strict: bool = False) -> tuple[n.Workflow, list[Diagnostic]]:
    parser = Parser(source, strict=strict)
    workflow = parser.parse_workflow()
    return workflow, parser.warnings


def parse_file(path: str, *, strict: bool = False) -> n.Workflow:
    with open(path, encoding="utf-8") as f:
        return parse(f.read(), strict=strict)
