from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class Node(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Policy(str, Enum):
    MAJORITY = "Majority"
    UNANIMITY = "Unanimity"


class Verdict(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


Value = Union[str, int]          # literal: string or integer


class TypeRef(Node):
    name: str
    many: bool = False           # True for `String*`


class Condition(Node):
    var: str
    verdict: Verdict


# ---- members of an action body ----
class Redefinition(Node):        # :>> skill = "..." ;
    kind: Literal["redefinition"] = "redefinition"
    name: str
    value: Value

class In(Node):                  # in x ;
    kind: Literal["in"] = "in"
    name: str

class Out(Node):                 # out x : T ;
    kind: Literal["out"] = "out"
    name: str
    type_ref: TypeRef

class Send(Node):                # send x ;
    kind: Literal["send"] = "send"
    name: str

Member = Annotated[Union[Redefinition, In, Out, Send], Field(discriminator="kind")]


# ---- statements (what follows `then`) ----
class Input(Node):
    kind: Literal["input"] = "input"
    name: str
    type_ref: TypeRef

class Init(Node):
    kind: Literal["init"] = "init"
    name: str
    type_ref: TypeRef
    value: Value

class Action(Node):
    kind: Literal["action"] = "action"
    name: str
    step_type: str               # SolutionStep, EvaluationStep, ...
    members: list[Member] = []

class Spawn(Node):
    kind: Literal["spawn"] = "spawn"
    count: PositiveInt
    name: str
    step_type: str
    policy: Policy
    members: list[Member] = []

class Reference(Node):
    kind: Literal["reference"] = "reference"
    name: str
    step_type: str
    members: list[Member] = []

class Loop(Node):
    kind: Literal["loop"] = "loop"
    name: str
    max_retries: PositiveInt
    body: list[Statement] = []   # forward reference: loops nest
    until: Condition

Statement = Annotated[
    Union[Input, Init, Action, Spawn, Reference, Loop],
    Field(discriminator="kind"),
]


class Workflow(Node):
    statements: list[Statement] = []


Loop.model_rebuild()
Workflow.model_rebuild()