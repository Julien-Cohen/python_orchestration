"""Lexer for the workflow language.

Token kinds:
    IDENT   identifier (`x3`, `domainDescription`)
    QNAME   quoted name, 'like this'
    STRING  "string literal" (value is unescaped)
    INT / FLOAT
    KW      reserved word (see KEYWORDS)
    SYM     punctuation / operator (`:>>`, `:=`, `{`, ...)
    EOF
"""

import re
from dataclasses import dataclass
from typing import Any

from .errors import LexError
from .nodes import Loc

KEYWORDS = frozenset(
    {
        "first", "start", "then", "init", "input", "output", "loop", "action",
        "until", "with", "in", "out", "true", "false",
    }
)

# Alternatives are tried in order, so longer symbols come first.
_TOKEN_RE = re.compile(
    r"""
      (?P<ws>[ \t\r\n]+)
    | (?P<lcomment>//[^\n]*)
    | (?P<bcomment>/\*(?s:.*?)\*/)
    | (?P<string>"(?:[^"\\\n]|\\.)*")
    | (?P<qname>'(?:[^'\\\n]|\\.)*')
    | (?P<number>\d+(?:\.\d+)?)
    | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<sym>:>>|:=|::|\.\.|[:;.{}()\[\]=*+?,])
    """,
    re.VERBOSE,
)

_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"', "'": "'"}


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    value: Any
    loc: Loc
    text: str

    def is_kw(self, word: str) -> bool:
        return self.kind == "KW" and self.value == word

    def is_sym(self, sym: str) -> bool:
        return self.kind == "SYM" and self.value == sym

    def is_word(self, word: str) -> bool:
        """A contextual keyword: an ordinary identifier with this spelling."""
        return self.kind == "IDENT" and self.value == word


def _unescape(body: str) -> str:
    return re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(1)), body)


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    line = 1
    line_start = 0

    while pos < len(source):
        loc = Loc(line=line, column=pos - line_start + 1)
        match = _TOKEN_RE.match(source, pos)

        if match is None:
            ch = source[pos]
            if ch in "\"'":
                raise LexError("unterminated string literal", loc, source, "close it on the same line")
            if source.startswith("/*", pos):
                raise LexError("unterminated block comment", loc, source, "add a closing '*/'")
            raise LexError(f"unexpected character {ch!r}", loc, source)

        kind = match.lastgroup
        text = match.group()

        if kind == "string":
            tokens.append(Token("STRING", _unescape(text[1:-1]), loc, text))
        elif kind == "qname":
            tokens.append(Token("QNAME", _unescape(text[1:-1]), loc, text))
        elif kind == "number":
            if "." in text:
                tokens.append(Token("FLOAT", float(text), loc, text))
            else:
                tokens.append(Token("INT", int(text), loc, text))
        elif kind == "ident":
            tokens.append(Token("KW" if text in KEYWORDS else "IDENT", text, loc, text))
        elif kind == "sym":
            tokens.append(Token("SYM", text, loc, text))
        # ws / lcomment / bcomment: skipped

        newlines = text.count("\n")
        if newlines:
            line += newlines
            line_start = pos + text.rfind("\n") + 1
        pos = match.end()

    tokens.append(Token("EOF", "", Loc(line=line, column=pos - line_start + 1), ""))
    return tokens
