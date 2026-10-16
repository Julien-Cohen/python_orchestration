"""Export of a Workflow as a PlantUML activity diagram."""

from orchestrator.workflow_datatype.workflows import (
    Workflow, Step, Sequence, AlgorithmicStep, GenerationStep, EvaluationStep,
    RetryUntilValidated, AccumulateLoop, ParallelBuild, ParallelEvaluation, ReplyStep,
)


def _esc(text) -> str:
    """Make a text safe inside a PlantUML action (':' ... ';') or a condition."""
    return str(text).replace(";", ",").replace("\n", "\\n").replace("(", "[").replace(")", "]")


def _chan(label: str, names: list[str]) -> str | None:
    return f"{label}: {', '.join(names)}" if names else None


def _action(title: str, lines: list[str | None]) -> str:
    parts = [f"<b>{_esc(title)}</b>"] + [_esc(l) for l in lines if l]
    return ":" + "\\n".join(parts) + ";"


def _render(s: Step, depth: int, out: list[str]) -> None:
    pad = "  " * depth
    match s:
        case Sequence():
            _render(s.step1, depth, out)
            _render(s.step2, depth, out)

        case AlgorithmicStep():
            t = s.task
            out.append(pad + _action("Algorithmic task", [
                t.statement.log,
                _chan("read", t.readChannels),
                _chan("write", t.writeChannels),
            ]))

        case GenerationStep():
            t = s.task
            c = t.config
            out.append(pad + _action("Generation", [
                f"{c.skill}",
                f"{c.nbSpawns} workers ({c.nbDifferentAgents} different)",
                f"(join mode: {t.solutionJoin.value})",
                _chan("< ", t.inputChannels),
                _chan("< feedback", t.feedbackChannels),
                _chan("> ", t.outputChannels),
            ]))

        case EvaluationStep():
            t = s.task
            c = t.config
            out.append(pad + _action("Evaluation", [
                f"{c.skill}",
                f"{c.nbSpawns} workers ({c.nbDifferentAgents} different)",
                f"({t.consensusType.value})",
                _chan("< spec", t.specificationChannels),
                _chan("< solution", t.solutionChannels),
                f"> evaluation: {t.evaluationChannel}",
                f"> explanation: {t.explanationChannel}",
            ]))
        case RetryUntilValidated():
            out.append(pad + f"while ({_esc(s.acceptanceChannel)} ?) is (false)")
            out.append(pad + f"  note right: Retry\\nLoop")
            _render(s.body, depth + 1, out)
            out.append(pad + "endwhile (true)")

        case AccumulateLoop():
            out.append(pad + f"while ({_esc(s.stopChannel)} ?) is (false)")
            out.append(pad + f"  note right: Accumulate\\nLoop")
            _render(s.body, depth + 1, out)
            out.append(pad + "endwhile (true)")

        case ParallelBuild() | ParallelEvaluation():
            kind = "Parallel build" if isinstance(s, ParallelBuild) else "Parallel evaluation"
            rec = s.reconciliation.value
            branches = s.branches
            out.append(pad + _action(kind, [f"({rec})"]))
            if len(branches) == 1:
                _render(branches[0], depth, out)
            elif len(branches) > 1:
                for i, b in enumerate(branches):
                    out.append(pad + ("fork" if i == 0 else "fork again"))
                    _render(b, depth + 1, out)
                out.append(pad + "end fork")

        case ReplyStep():
            out.append(pad + _action("Reply to client", [_chan("channels", s.outputChannels)]))

        case _:
            raise TypeError(f"Unsupported step type: {type(s).__name__}")


def workflow_to_plantuml(workflow: Workflow) -> str:
    """Return a PlantUML activity diagram describing the workflow."""
    out = ["@startuml", "title Workflow", "start"]

    inputs = [c.name for c in workflow.inputChannels]
    if inputs:
        out.append("note right: " + _esc("inputs: " + ", ".join(inputs)))

    _render(workflow.body, 0, out)

    outputs = [c.name for c in workflow.outputChannels]
    if outputs:
        out.append("note right: " + _esc("outputs: " + ", ".join(outputs)))

    out += ["stop", "@enduml"]
    return "\n".join(out)