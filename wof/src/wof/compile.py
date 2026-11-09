"""Compile a `wof_ast.Workflow` (high-level syntax tree) into a `workflows.Workflow`
(MOSAICO orchestration tree).

Everything the source tree does not say is taken from a `Defaults` value that the
caller passes to `compile_workflow`.
"""

from __future__ import annotations

import warnings
from typing import Callable

from . import wof_ast as wof
from orchestrator.workflow_datatype.agent_task import (
    AgentTaskConfig,
    EvaluationConfig,
    GenerationConfig,
)
from orchestrator.workflow_datatype.channelStructure import ChannelStructure
from orchestrator.workflow_datatype.join import DecisionMode
from orchestrator.workflow_datatype.workflows import (
    # noqa: F401  (kept for future statements)
    ChannelDeclaration,
    EvaluationStep,
    GenerationStep,
    InputChannelDeclaration,
    ReplyStep,
    RetryUntilValidated,
    Sequence,
    Step,
    Workflow,
)
from .default_values import Defaults


# --------------------------------------------------------------------------- #
# Compiler
# --------------------------------------------------------------------------- #
_CONFIG_FIELDS = set(AgentTaskConfig.model_fields)
_GENERATION_ONLY = {"solutionJoin"}
_EVALUATION_ONLY = {"consensusType", "outputKind"}


class CompilationWarning(UserWarning):
    """Part of the source was ignored or approximated by the compiler."""


def _default_warn(message: str) -> None:
    warnings.warn(message, CompilationWarning, stacklevel=3)


class _Compiler:
    def __init__(self, defaults: Defaults, warn: Callable[[str], None]):
        self.d = defaults
        self._warn = warn
        self.inputs: dict[str, InputChannelDeclaration] = {}
        self.internals: dict[str, ChannelDeclaration] = {}
        self.type_names: dict[str, str] = {}     # channel name -> declared type name
        self.sends: list[str] = []

    # ---- channels -------------------------------------------------------- #
    def _structure(self, t: wof.TypeRef) -> ChannelStructure:
        return self.d.many_structure if t.many else self.d.atom_structure

    def _declare(self, name: str, t: wof.TypeRef, init: wof.Value | None = None) -> None:
        structure = self._structure(t)
        if name in self.inputs:
            raise ValueError(f"Channel '{name}' is already declared as an input")
        previous = self.internals.get(name)
        if previous is not None:
            if previous.structure != structure:
                raise ValueError(f"Channel '{name}' is declared with two different types")
            return
        value = self.d.channel_init_value if init is None else str(init)
        self.internals[name] = ChannelDeclaration(
            name=name, structure=structure, init_with_value=value
        )
        self.type_names[name] = t.name

    # ---- statements ------------------------------------------------------ #
    def statements(self, stmts: list[wof.Statement]) -> list[Step]:
        steps: list[Step] = []
        for s in stmts:
            step = self._statement(s)
            if step is not None:        # Input / Init only declare channels
                steps.append(step)
        return steps

    def _statement(self, s: wof.Statement) -> Step | None:
        match s:
            case wof.Input():
                if s.name in self.inputs or s.name in self.internals:
                    raise ValueError(f"Channel '{s.name}' is declared several times")
                self.inputs[s.name] = InputChannelDeclaration(
                    name=s.name, structure=self._structure(s.type_ref), init_with_part=s.name
                )
                self.type_names[s.name] = s.type_ref.name
                return None
            case wof.Init():
                if s.name in self.inputs or s.name in self.internals:
                    raise ValueError(f"Channel '{s.name}' is declared several times")
                self._declare(s.name, s.type_ref, s.value)
                return None
            case wof.Action():
                return self._agent_step(s.name, s.step_type, s.members)
            case wof.Reference():
                return self._reply_step(s)
            case wof.Spawn():
                return self._agent_step(
                    s.name, s.step_type, s.members, nb_spawns=s.count, policy=s.policy
                )
            case wof.Loop():
                return self._loop(s)
            case _:
                raise TypeError(f"Unsupported statement: {type(s).__name__}")

    def _loop(self, l: wof.Loop) -> Step:
        body = self.statements(l.body)
        if not body:
            raise ValueError(f"Loop '{l.name}' has no step in its body")
        if l.until.verdict is not wof.Verdict.ACCEPTED:
            raise ValueError(
                f"Loop '{l.name}': only `until ... accepted` is supported "
                f"(got '{l.until.verdict.value}')"
            )
        return RetryUntilValidated(
            body=_sequence(body),
            acceptanceChannel=l.until.var,
            fuel=l.max_retries,
            anchor=l.name,
        )

    # ---- reference: reply to the client ----------------------------------- #
    def _reply_step(self, r: wof.Reference) -> Step:
        sent: list[str] = []
        for m in r.members:
            match m:
                case wof.Send():
                    sent.append(m.name)
                case wof.Redefinition():
                    if m.name not in self.d.ignored_redefinitions:
                        raise ValueError(
                            f"Reference '{r.name}': unknown redefinition ':>> {m.name}'"
                        )
                    self._warn(
                        f"reference '{r.name}': ':>> {m.name}' ignored "
                        f"(no counterpart in the compiled workflow)"
                    )
                case _:
                    raise ValueError(
                        f"Reference '{r.name}': only `send` and `:>> message` are supported"
                    )
        self.sends.extend(sent)
        return ReplyStep(outputChannels=list(dict.fromkeys(sent)))

    # ---- agent steps ----------------------------------------------------- #
    def _agent_step(
        self,
        name: str,
        step_type: str,
        members: list[wof.Member],
        nb_spawns: int | None = None,
        policy: wof.Policy | None = None,
    ) -> Step:
        d = self.d
        ins: list[str] = []
        outs: list[str] = []
        overrides: dict[str, wof.Value] = {}

        for m in members:
            match m:
                case wof.In():
                    ins.append(m.name)
                case wof.Out():
                    self._declare(m.name, m.type_ref)
                    outs.append(m.name)
                case wof.Send():
                    self.sends.append(m.name)
                case wof.Redefinition():
                    overrides[m.name] = m.value

        is_eval = step_type in d.evaluation_step_types
        if policy is not None and not is_eval:
            self._warn(
                f"action '{name}': policy '{policy.value}' ignored "
                f"(only meaningful for evaluations)"
            )

        # 1. common configuration: defaults, then `spawn`, then explicit redefinitions
        cfg: dict = dict(
            skill=d.skill,
            override_repo=d.override_repo,
            nbSpawns=d.nb_spawns if nb_spawns is None else nb_spawns,
            nbDifferentAgents=d.nb_different_agents,
            nbRequiredAnswers=d.nb_required_answers,
            agentTimeout=d.agent_timeout,
            onAgentFailure=d.on_agent_failure,
            onAgentRejection=d.on_agent_rejection,
            maxEffort=d.max_effort,
            maxRetry=d.max_retry,
        )
        specific: dict = {}
        allowed_specific = _EVALUATION_ONLY if is_eval else _GENERATION_ONLY
        for key, value in overrides.items():
            if key in d.ignored_redefinitions:
                self._warn(
                    f"action '{name}': ':>> {key}' ignored "
                    f"(no counterpart in the compiled workflow)"
                )
                continue
            if key in _CONFIG_FIELDS:
                cfg[key] = value
            elif key in allowed_specific:
                specific[key] = value
            else:
                raise ValueError(f"Action '{name}': unknown redefinition ':>> {key}'")
        if cfg["nbRequiredAnswers"] is None:
            cfg["nbRequiredAnswers"] = cfg["nbSpawns"]
        config = AgentTaskConfig(**cfg)

        # 2. task-specific part
        if is_eval:
            if not outs:
                raise ValueError(f"Evaluation '{name}' needs at least one `out` (the verdict)")
            evaluation_channel = outs[0]
            if len(outs) > 1:
                explanation_channel = outs[1]
            else:
                explanation_channel = f"{name}_explanation"
                self._declare(explanation_channel, wof.TypeRef(name=d.explanation_type_name))
            consensus = (
                DecisionMode(policy.value) if policy is not None else d.consensus_type
            )
            # `in` of a workflow input = criteria (specification); other `in` = data to evaluate.
            specification = [n for n in ins if n in self.inputs]
            solutions = [n for n in ins if n not in self.inputs]
            if not solutions:               # nothing else to evaluate: everything is evaluated
                specification, solutions = [], ins
            task = EvaluationConfig(
                config=config,
                consensusType=specific.get("consensusType", consensus),
                outputKind=specific.get("outputKind", d.evaluation_kind),
                specificationChannels=specification,
                solutionChannels=solutions,
                evaluationChannel=evaluation_channel,
                explanationChannel=explanation_channel,
            )
            return EvaluationStep(task=task)

        if not outs:
            raise ValueError(f"Generation '{name}' needs at least one `out`")
        feedback = [n for n in ins if self.type_names.get(n) == d.explanation_type_name]
        regular = [n for n in ins if n not in feedback]
        task = GenerationConfig(
            config=config,
            solutionJoin=specific.get("solutionJoin", d.solution_join),
            inputChannels=regular,
            feedbackChannels=feedback,
            outputChannels=outs,
        )
        return GenerationStep(task=task)


def _sequence(steps: list[Step]) -> Step:
    """[a, b, c] -> Sequence(a, Sequence(b, c)). Requires a non-empty list."""
    result = steps[-1]
    for step in reversed(steps[:-1]):
        result = Sequence(step1=step, step2=result)
    return result


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def compile_workflow(
    workflow: wof.Workflow,
    defaults: Defaults = Defaults(),
    on_warning: Callable[[str], None] | None = None,
) -> Workflow:
    """Compile a wof_ast.Workflow into a workflows.Workflow.

    Values absent from the source tree come from `defaults`.
    Items of the source that are ignored are reported through `on_warning(message)`;
    by default they are emitted as `CompilationWarning` with `warnings.warn`.
    """
    c = _Compiler(defaults, on_warning or _default_warn)
    steps = c.statements(workflow.statements)

    # Channels that are `send`-ed become the workflow's output channels.
    outputs: list[ChannelDeclaration] = []
    for name in dict.fromkeys(c.sends):          # dedupe, keep order
        if name in c.inputs:
            raise ValueError(f"Cannot send input channel '{name}'")
        decl = c.internals.pop(name, None)
        if decl is None:
            raise ValueError(f"`send {name}`: channel is not declared")
        outputs.append(decl)

    # A trailing `reference` already replies; otherwise reply with the sent channels.
    if not steps or not isinstance(steps[-1], ReplyStep):
        steps.append(ReplyStep(outputChannels=[o.name for o in outputs]))

    return Workflow(
        inputChannels=list(c.inputs.values()),
        internalChannels=list(c.internals.values()),
        outputChannels=outputs,
        body=_sequence(steps),
    )
