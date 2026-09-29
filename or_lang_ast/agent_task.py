"""Data structures to represent specification of agent tasks.

    Task take part in a workflow (or orchestration).

    Two kinds of agent tasks: generation of solutions and evaluation of solutions.

    This module does not define the workflow between task.

    The execution of a task consists in requesting a list of agents to the MOSAICO repository,
    launch them if needed, send them appropriate input,
    collect the answers, handle failures, reconcile the answers,
    and decide to finish the task.

    We call 'worker' an agent working inside a task. If a same agent is prompted 3 times in parallel for the same task, we consider 3 workers.

    We call 'channel' a global variable in the orchestration process that is read or written by agent tasks or algorithmic tasks.
    Tasks do not have access to channels unless explicitly specified.
    Some channels contain so called 'solutions' produced by generative tasks (containing text or file),
    some channels contain 'evaluations' produced by evaluation tasks,
    and some channels contain 'explanations' (textual, natural language), also produced by evaluation tasks.
    The request received by the orchestration task is considered as a read-only channel, and the final outcome of the orchestration is considered as a write-only channel.
"""

from pydantic import BaseModel
from enum import Enum

from join import SolutionJoin, DecisionMode


class OnAgentFailure(str, Enum):
    """Specify what to do when an agent fails."""

    RETRY_SAME = "RetrySame"
    """Retry with the same agent."""

    RETRY_OTHER = "RetryOther"
    """Find an other agent (ask the repo) and try with it."""

    NO_RETRY = "NoRetry"
    """Don't retry on failure."""


class AgentTaskConfig(BaseModel):
    """Configuration for agent tasks. Contains the information common to generation tasks and evaluation tasks."""

    skill : str
    """The skill the agent should have. Passed to the MOSAICO repository."""

    nbSpawns : int
    """Number of parallel workers."""

    nbDifferentAgents : int
    """Number of different agents among workers. 1 means a same agent is spawned several times (if nbSpawns > 1)."""

    nbRequiredAnswers : int
    """Number of answers to be received before finishing the step (must be <=nbSpawns)."""

    agentTimeout : int
    """Time in  milliseconds after a worker is considered as failed."""

    onAgentFailure : OnAgentFailure
    """Action to be performed when a worker fails (error, timeout)."""

    onAgentRejection: OnAgentFailure
    """Action to be performed when a worker rejects a task."""

    maxEffort : int
    """Max cost (tokens/money). Don't launch new workers if the max effort has been exceeded."""

    maxRetry : int
    """Max number of retry on failure (except if no retry specified by onAgentFailure)."""



class GenerationConfig(BaseModel):
    """Configuration for generation tasks."""

    config : AgentTaskConfig

    solutionJoin : SolutionJoin
    """Specify how multiple solutions are reconciled (when several workers)."""

    inputChannels : list[str]
    """List of channels to be read for the input data (non empty)."""

    feedbackChannels : list[str]
    """List of channels to be read for feedback 'explanations' after first iterations (can be empty)."""

    outputChannel: str
    """Channel on which to write the generated Solutions (non empty)."""


class EvaluationKind(str, Enum):
    BOOLEAN = "Boolean"
    NUMERICAL = "Numerical"
    TEXTUAL = "Textual"

class EvaluationConfig(BaseModel):
    """Configuration for evaluation tasks."""

    config : AgentTaskConfig

    consensusType : DecisionMode

    outputKind: EvaluationKind

    specificationChannels : list[str]
    """List of channels to be read for the input data used for evaluation criteria (mandatory)."""

    solutionChannels : list[str]
    """List of channels to be read for the input data to be evaluated (mandatory)."""

    evaluationChannel : list[str]
    """Channel to publish the result of the evaluation (mandatory)."""

    explanationChannel : list[str]
    """Channel to publish the explanation (optional)."""
