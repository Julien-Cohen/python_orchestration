"""AST node types for the workflow language, as Pydantic models.

Every node carries an optional source location (`loc`). Nodes that can appear
in a heterogeneous list (expressions, members, steps) carry a `kind`
discriminator so that a tree can be dumped to JSON and validated back.
"""

from typing import Annotated, Any, Iterator, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Loc(BaseModel):
    """A 1-based line / column position in the source text."""

    model_config = ConfigDict(frozen=True)

    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"


class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loc: Optional[Loc] = None


# --------------------------------------------------------------------------
# Types and multiplicities
# --------------------------------------------------------------------------


class Multiplicity(Node):
    """`*` = (0, None), `+` = (1, None), `?` = (0, 1), `[2..5]` = (2, 5)."""

    lower: int = Field(ge=0)
    upper: Optional[int] = Field(default=None, ge=0)  # None means unbounded

    @model_validator(mode="after")
    def _check_bounds(self) -> "Multiplicity":
        if self.upper is not None and self.upper < self.lower:
            raise ValueError(f"upper bound {self.upper} is below lower bound {self.lower}")
        return self


class TypeRef(Node):
    name: str
    multiplicity: Optional[Multiplicity] = None


# --------------------------------------------------------------------------
# Expressions
# --------------------------------------------------------------------------


class StringLiteral(Node):
    kind: Literal["string"] = "string"
    value: str


class BoolLiteral(Node):
    kind: Literal["bool"] = "bool"
    value: bool


class NumberLiteral(Node):
    kind: Literal["number"] = "number"
    value: Union[int, float]


class Reference(Node):
    """A (possibly qualified) name, e.g. `isSyntacticallyCorrect`."""

    kind: Literal["ref"] = "ref"
    name: str


Expression = Annotated[
    Union[StringLiteral, BoolLiteral, NumberLiteral, Reference],
    Field(discriminator="kind"),
]


# --------------------------------------------------------------------------
# Action members (the body of `action ... { ... }`)
# --------------------------------------------------------------------------


class Parameter(Node):
    """`in name : Type;` or `out name : Type*;`"""

    kind: Literal["parameter"] = "parameter"
    direction: Literal["in", "out"]
    name: str
    type: TypeRef


class Redefinition(Node):
    """`:>> name = expr;` or `:>> name : expr;`

    `operator` records which of `=` / `:` was written in the source.
    """

    kind: Literal["redefinition"] = "redefinition"
    name: str
    operator: Literal["=", ":"]
    value: Expression


Member = Annotated[Union[Parameter, Redefinition], Field(discriminator="kind")]


# --------------------------------------------------------------------------
# Steps
# --------------------------------------------------------------------------


class StartStep(Node):
    """`first start;`"""

    kind: Literal["start"] = "start"



class InitStep(Node):
    """`then init name := expr;`"""

    kind: Literal["init"] = "init"
    name: str
    value: Expression


class InputStep(Node):
    """`then input name : Type;`"""

    kind: Literal["input"] = "input"
    name: str
    type: TypeRef


class OutputStep(Node):
    """`then output name : Type;`"""

    kind: Literal["output"] = "output"
    name: str
    type: TypeRef


class ActionStep(Node):
    """`then action name : Type x3 with Aggregation { members }`"""

    kind: Literal["action"] = "action"
    name: str
    type: Optional[str] = None
    repeat: Optional[int] = Field(default=None, ge=1)  # the `x3` part
    aggregation: Optional[str] = None  # the `with Unanimity` part
    members: list[Member] = Field(default_factory=list)

    def member(self, name: str) -> Optional[Union[Parameter, Redefinition]]:
        return next((m for m in self.members if m.name == name), None)

    @property
    def inputs(self) -> list[Parameter]:
        return [m for m in self.members if isinstance(m, Parameter) and m.direction == "in"]

    @property
    def outputs(self) -> list[Parameter]:
        return [m for m in self.members if isinstance(m, Parameter) and m.direction == "out"]

    @property
    def redefinitions(self) -> dict[str, Expression]:
        return {m.name: m.value for m in self.members if isinstance(m, Redefinition)}


class LoopStep(Node):
    """`then loop action name with max 3 retries { steps } until cond;`"""

    kind: Literal["loop"] = "loop"
    name: str
    max_retries: Optional[int] = Field(default=None, ge=0)
    body: list["Step"] = Field(default_factory=list)
    until: Optional[Expression] = None


Step = Annotated[
    Union[StartStep, InitStep, InputStep, OutputStep, ActionStep, LoopStep],
    Field(discriminator="kind"),
]

LoopStep.model_rebuild()


class Workflow(Node):
    steps: list[Step] = Field(default_factory=list)

    def walk(self) -> Iterator[Step]:
        """Yield every step, depth first, descending into loop bodies."""

        def rec(steps: list[Step]) -> Iterator[Step]:
            for step in steps:
                yield step
                if isinstance(step, LoopStep):
                    yield from rec(step.body)

        yield from rec(self.steps)

    def to_dict(self, include_loc: bool = False) -> dict[str, Any]:
        """Plain-dict form of the tree; source locations are dropped by default."""
        data = self.model_dump(mode="json")
        return data if include_loc else _strip_loc(data)


def _strip_loc(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_loc(v) for k, v in value.items() if k != "loc"}
    if isinstance(value, list):
        return [_strip_loc(v) for v in value]
    return value


Workflow.model_rebuild()
