from typing import Literal, Union, Annotated
from pydantic import BaseModel, Field

from algorithmic_task import AlgorithmicTaskConfig
from agent_task import EvaluationConfig, GenerationConfig
from join import SolutionJoin, DecisionMode


class Sequence(BaseModel):
    type: Literal["sequence"] = "sequence"
    step1: "Step"
    step2: "Step"

class AlgorithmicStep(BaseModel):
    type: Literal["algorithmic-step"] = "algorithmic-step"
    task: AlgorithmicTaskConfig

class GenerationStep(BaseModel):
    type: Literal["generation-step"] = "algorithmic-step"
    task: GenerationConfig


class RetryUntilValidated(BaseModel):
    type: Literal["retry-loop"] = "retry-loop"
    condition: EvaluationConfig
    body: "Step"

class AccumulateLoop(BaseModel):
    type: Literal["accumulate-loop"] = "accumulate-loop"
    condition: EvaluationConfig
    body: "Step"

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
    Union[Sequence, AlgorithmicStep, GenerationStep, RetryUntilValidated, AccumulateLoop, ParallelBuild, ParallelEvaluation, ReplyStep],
    Field(discriminator="type")
]

Sequence.model_rebuild()
RetryUntilValidated.model_rebuild()
AccumulateLoop.model_rebuild()
ParallelBuild.model_rebuild()
ParallelEvaluation.model_rebuild()
