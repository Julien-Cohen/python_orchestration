from typing import Literal, Union, Annotated
from pydantic import BaseModel, Field

from algorithmic_task import AlgorithmicTaskConfig
from agent_task import EvaluationConfig, GenerationConfig
from join import SolutionJoin, DecisionMode
from ChannelStructure import ChannelStructure


class Sequence(BaseModel):
    type: Literal["sequence"] = "sequence"
    step1: "Step"
    step2: "Step"

class AlgorithmicStep(BaseModel):
    type: Literal["algorithmic-step"] = "algorithmic-step"
    task: AlgorithmicTaskConfig

class GenerationStep(BaseModel):
    type: Literal["generation-step"] = "generation-step"
    task: GenerationConfig

class EvaluationStep(BaseModel):
    type: Literal["evaluation-step"] = "evaluation-step"
    task: EvaluationConfig


class RetryUntilValidated(BaseModel):
    type: Literal["retry-loop"] = "retry-loop"
    body: "Step"
    acceptanceChannel: str

class AccumulateLoop(BaseModel):
    type: Literal["accumulate-loop"] = "accumulate-loop"
    body: "Step"
    stopChannel : str

class ParallelBuild(BaseModel):
    type: Literal["parallel-build"] = "parallel-build"
    branches: list["Step"]
    reconciliation: SolutionJoin

class ParallelEvaluation(BaseModel):
    type: Literal["parallel-eval"] = "parallel-eval"
    branches: list["Step"]
    reconciliation: DecisionMode

class ReplyStep(BaseModel):
    type: Literal["reply-step"] = "reply-step"
    outputChannels : list[str]

Step = Annotated[
    Union[Sequence, AlgorithmicStep, GenerationStep, EvaluationStep, RetryUntilValidated, AccumulateLoop, ParallelBuild, ParallelEvaluation, ReplyStep],
    Field(discriminator="type")
]

Sequence.model_rebuild()
RetryUntilValidated.model_rebuild()
AccumulateLoop.model_rebuild()
ParallelBuild.model_rebuild()
ParallelEvaluation.model_rebuild()




class ChannelDeclaration(BaseModel):
    """
    A channel contains the data that is read or written by agents.
    The name of a channel must be unique.
    It is initialized once at the beginning of an orchestration.
    """
    type: Literal["channel-declaration"] = "channel-declaration"
    name: str
    structure: ChannelStructure
    init: str


class Workflow(BaseModel):
    type: Literal["workflow"] = "workflow"

    inputChannels: list[ChannelDeclaration]
    """Channels that are initialized a startup by input."""

    internalChannels : list[ChannelDeclaration]

    outputChannels: list[ChannelDeclaration]
    """Channels that are reported to client at finish time."""

    body: Step



"""
TODO: 

* Check invariants : 
    * Channel occurrences are bound.
    * Declared channels have unique names.
"""