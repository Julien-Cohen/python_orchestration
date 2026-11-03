"""Error and diagnostic types shared by the lexer and the parser."""

from dataclasses import dataclass
from typing import Optional

from .nodes import Loc


class WofError(Exception):
    """Base class. Formats itself with the offending source line and a caret."""

    def __init__(
        self,
        message: str,
        loc: Optional[Loc] = None,
        source: Optional[str] = None,
        hint: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.loc = loc
        self.source = source
        self.hint = hint

    def __str__(self) -> str:
        if self.loc is None:
            return self.message
        out = [f"{self.loc}: {self.message}"]
        if self.source is not None:
            lines = self.source.splitlines()
            if 1 <= self.loc.line <= len(lines):
                number = f"{self.loc.line:>4}"
                out.append(f"{number} | {lines[self.loc.line - 1]}")
                out.append(f"{' ' * len(number)} | {' ' * (self.loc.column - 1)}^")
        if self.hint:
            out.append(f"hint: {self.hint}")
        return "\n".join(out)


class LexError(WofError):
    pass


class ParseError(WofError):
    pass


@dataclass(frozen=True)
class Diagnostic:
    """A non-fatal problem the parser tolerated (e.g. a missing `;`)."""

    message: str
    loc: Loc

    def __str__(self) -> str:
        return f"{self.loc}: warning: {self.message}"
