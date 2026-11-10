from __future__ import annotations

from typing import Optional

from dataclasses import dataclass

from orchestrator.workflow_datatype.agent_task import OnAgentFailure, EvaluationKind
from orchestrator.workflow_datatype.channelStructure import ChannelStructure
from orchestrator.workflow_datatype.join import SolutionJoin, DecisionMode


# --------------------------------------------------------------------------- #
# Defaults: everything that the wof_ast does not express
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Defaults:
    # --- AgentTaskConfig ---
    skill: str = "default"
    override_repo: Optional[str] = None
    nb_spawns: int = 1
    nb_different_agents: int = 1
    nb_required_answers: Optional[int] = None  # None -> same as nbSpawns
    agent_timeout: int = 60                # seconds
    on_agent_failure: OnAgentFailure = OnAgentFailure.RETRY_SAME
    on_agent_rejection: OnAgentFailure = OnAgentFailure.NO_RETRY
    max_effort: int = 500
    max_retry: int = 1

    # --- GenerationConfig / EvaluationConfig ---
    solution_join: SolutionJoin = SolutionJoin.FIRST
    consensus_type: DecisionMode = DecisionMode.MAJORITY
    evaluation_kind: EvaluationKind = EvaluationKind.BOOLEAN

    # --- channels ---
    channel_init_value: str = ""                           # for channels created by `out`
    atom_structure: ChannelStructure = ChannelStructure.Atom   # TypeRef.many == False
    many_structure: ChannelStructure = ChannelStructure.List   # TypeRef.many == True

    # --- which `step_type` names are evaluations (all others are generations) ---
    evaluation_step_types: frozenset[str] = frozenset({"EvaluationStep"})

    # --- `:>> name = value` redefinitions that have no counterpart in the target
    #     datatypes (the target has no field for prompts or messages): dropped with a warning.
    ignored_redefinitions: frozenset[str] = frozenset({"prompt", "message"})

    # --- an `in` of a channel whose declared type has this name is a *feedback*
    #     channel of a generation (not one of its regular inputs).
    explanation_type_name: str = "Explanation"
