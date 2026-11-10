"""Tests for the WOF parser, AST transformer, compiler and CLI.

Layout assumed:
    <repo>/
        wof/            (the package: __main__.py, compile.py, transformer.py, wof_ast.py, wof_ast.lark)
        orchestrator/   (the MOSAICO datatypes)
        test_wof_ast.py     (this file)

Run with:  pytest -v test_wof_ast.py
Any *.wof file located next to this file (or in ./examples) is also parsed and
compiled by `test_example_files`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from lark import Lark
from lark.exceptions import UnexpectedInput, VisitError

from wof import wof_ast



from orchestrator.workflow_datatype.agent_task import EvaluationKind, OnAgentFailure
from orchestrator.workflow_datatype.channelStructure import ChannelStructure
from orchestrator.workflow_datatype.join import DecisionMode, SolutionJoin
from orchestrator.workflow_datatype.workflows import (
    EvaluationStep,
    GenerationStep,
    ReplyStep,
    RetryUntilValidated,
    Sequence,
)
from wof.__main__ import GRAMMAR_PATH, main
from wof.compile import compile_workflow, _sequence, CompilationWarning
from wof.default_values import Defaults
from wof.transformer import ToAst

# =========================================================================== #
# Helpers
# =========================================================================== #
_PARSER = Lark(GRAMMAR_PATH.read_text(encoding="utf-8"), start="workflow", parser="lalr")


def parse_tree(src: str):
    return _PARSER.parse(src)


def parse(src: str) -> wof_ast.Workflow:
    """text -> wof AST (what the CLI does in steps 1 and 2)."""
    return ToAst().transform(parse_tree(src))


def compile_src(src: str, defaults: Defaults | None = None):
    """text -> compiled workflow + the list of warnings emitted."""
    warnings_seen: list[str] = []
    wf = compile_workflow(parse(src), defaults or Defaults(), on_warning=warnings_seen.append)
    return wf, warnings_seen


def leaves(step):
    """Flatten nested Sequence(a, Sequence(b, c)) into [a, b, c] (loops stay opaque)."""
    if isinstance(step, Sequence):
        return leaves(step.step1) + leaves(step.step2)
    return [step]


def names(decls):
    return [d.name for d in decls]


# --------------------------------------------------------------------------- #
# Reusable source snippets
# --------------------------------------------------------------------------- #
SIMPLE = """
first start;
then input spec : String ;
then action gen : SolutionStep {
    :>> skill = "generate" ;
    in spec ;
    out result : Solution ;
}
then action check : EvaluationStep {
    :>> skill = "check" ;
    in spec ;
    in result ;
    out ok : Evaluation ;
}
then reference action reply : ReferenceStep {
    send result ;
}
"""

LOOP = """
first start;
then input spec : String ;
then loop action retry with max 3 retries {
    then action gen : SolutionStep { in spec ; out result : Solution ; }
    then action check : EvaluationStep { in spec ; in result ; out ok : Evaluation ; }
} until ok is accepted ;
then reference action reply : ReferenceStep { send result ; }
"""


# =========================================================================== #
# 1. Parser + transformer (text -> wof AST)
# =========================================================================== #
class TestParser:
    def test_minimal_workflow(self):
        assert parse("first start;").statements == []

    def test_input_atom_and_many(self):
        wf = parse("first start; then input a : String ; then input b : String* ;")
        a, b = wf.statements
        assert isinstance(a, wof_ast.Input) and a.type_ref == wof_ast.TypeRef(name="String", many=False)
        assert isinstance(b, wof_ast.Input) and b.type_ref == wof_ast.TypeRef(name="String", many=True)

    def test_init_string_and_int_values(self):
        wf = parse('first start; then init a : Explanation := "hi" ; then init n : Int := 42 ;')
        a, n = wf.statements
        assert a.value == "hi" and isinstance(a.value, str)
        assert n.value == 42 and isinstance(n.value, int)

    def test_string_escapes_are_decoded(self):
        wf = parse(r'first start; then init a : String := "say \"x\"\nbye" ;')
        assert wf.statements[0].value == 'say "x"\nbye'

    def test_action_members(self):
        wf = parse(SIMPLE)
        _, gen, check, ref = wf.statements
        assert isinstance(gen, wof_ast.Action) and gen.name == "gen" and gen.step_type == "SolutionStep"
        assert gen.members == [
            wof_ast.Redefinition(name="skill", value="generate"),
            wof_ast.In(name="spec"),
            wof_ast.Out(name="result", type_ref=wof_ast.TypeRef(name="Solution")),
        ]
        assert isinstance(check, wof_ast.Action) and check.step_type == "EvaluationStep"
        assert isinstance(ref, wof_ast.Reference) and ref.members == [wof_ast.Send(name="result")]

    def test_redefinition_with_int(self):
        wf = parse("first start; then action a : SolutionStep { :>> nbSpawns = 4 ; }")
        assert wf.statements[0].members == [wof_ast.Redefinition(name="nbSpawns", value=4)]

    def test_empty_body(self):
        wf = parse("first start; then action a : SolutionStep { }")
        assert wf.statements[0].members == []

    @pytest.mark.parametrize("policy", ["Majority", "Unanimity"])
    def test_spawn(self, policy):
        wf = parse(f"first start; then spawn 3 action s : EvaluationStep with {policy} {{ in x ; }}")
        s = wf.statements[0]
        assert isinstance(s, wof_ast.Spawn)
        assert (s.count, s.name, s.step_type, s.policy.value) == (3, "s", "EvaluationStep", policy)
        assert s.members == [wof_ast.In(name="x")]

    def test_loop(self):
        wf = parse(LOOP)
        loop = wf.statements[1]
        assert isinstance(loop, wof_ast.Loop)
        assert loop.name == "retry" and loop.max_retries == 3
        assert [type(s) for s in loop.body] == [wof_ast.Action, wof_ast.Action]
        assert loop.until == wof_ast.Condition(var="ok", verdict=wof_ast.Verdict.ACCEPTED)

    def test_nested_loops(self):
        src = """
        first start;
        then loop action outer with max 2 retries {
            then loop action inner with max 5 retries {
                then action a : SolutionStep { out x : Solution ; }
            } until x is rejected ;
        } until x is accepted ;
        """
        outer = parse(src).statements[0]
        inner = outer.body[0]
        assert isinstance(inner, wof_ast.Loop)
        assert inner.max_retries == 5 and inner.until.verdict is wof_ast.Verdict.REJECTED
        assert isinstance(inner.body[0], wof_ast.Action)

    def test_empty_loop_body_parses(self):
        wf = parse("first start; then loop action l with max 1 retries { } until x is accepted ;")
        assert wf.statements[0].body == []

    def test_comments_whitespace_and_newlines_ignored(self):
        wf = parse("first\n\n  start ;\n\tthen   input   a:String;")
        assert len(wf.statements) == 1

    def test_identifiers_starting_with_keywords(self):
        # `in...`, `out...`, `send...` identifiers must not be mistaken for keywords
        wf = parse("first start; then input initial_requirements : String ; "
                   "then action outputToUser : ReferenceStep { send initial_requirements ; }")
        assert wf.statements[0].name == "initial_requirements"
        assert wf.statements[1].name == "outputToUser"

    def test_ast_nodes_are_frozen(self):
        wf = parse("first start;")
        with pytest.raises(Exception):
            wf.statements = []  # type: ignore[misc]

    def test_raw_tree_is_available(self):
        assert "workflow" in parse_tree(SIMPLE).pretty()


class TestParserErrors:
    @pytest.mark.parametrize(
        "src",
        [
            "",                                                          # no header
            "first start",                                               # missing ';'
            "start;",                                                    # missing 'first'
            "first start; input a : String ;",                           # missing 'then'
            "first start; then input a String ;",                        # missing ':'
            "first start; then input a : String",                        # missing final ';'
            "first start; then action a : T { in x }",                   # member without ';'
            "first start; then action a : T { in x ; ",                  # unclosed body
            "first start; then spawn 3 action a : T with Foo { }",       # unknown policy
            "first start; then spawn x action a : T with Majority { }",  # count not INT
            "first start; then loop action l with max 3 retries { } until x is maybe ;",  # bad verdict
            "first start; then loop action l with max 3 retries { } until x is accepted",  # no ';'
            "first start; then init a : String := ;",                    # missing literal
            "first start; then init a : String := 1.5 ;",                # floats unsupported
            "first start; then action a : T { :>> x = foo ; }",          # bare identifier as value
        ],
    )
    def test_syntax_errors(self, src):
        with pytest.raises(UnexpectedInput):
            parse_tree(src)

    @pytest.mark.parametrize(
        "src",
        [
            "first start; then loop action l with max 0 retries { } until x is accepted ;",
            "first start; then spawn 0 action a : T with Majority { }",
        ],
    )
    def test_non_positive_counts_rejected_by_ast(self, src):
        parse_tree(src)  # syntactically fine ...
        with pytest.raises(VisitError):  # ... but PositiveInt validation fails in the transformer
            parse(src)


# =========================================================================== #
# 2. Compiler (wof AST -> workflows.Workflow)
# =========================================================================== #
class TestCompilerStructure:
    def test_empty_workflow(self):
        wf, _ = compile_src("first start;")
        assert wf.inputChannels == [] and wf.internalChannels == [] and wf.outputChannels == []
        assert isinstance(wf.body, ReplyStep) and wf.body.outputChannels == []

    def test_simple_workflow_shape(self):
        wf, warns = compile_src(SIMPLE)
        assert warns == []

        # channels
        assert names(wf.inputChannels) == ["spec"]
        assert wf.inputChannels[0].init_with_part == "spec"
        assert wf.inputChannels[0].structure == ChannelStructure.Atom
        assert names(wf.outputChannels) == ["result"]           # sent => moved to outputs
        assert set(names(wf.internalChannels)) == {"ok", "check_explanation"}

        # body: Sequence(gen, Sequence(check, reply))
        gen, check, reply = leaves(wf.body)
        assert isinstance(gen, GenerationStep)
        assert isinstance(check, EvaluationStep)
        assert isinstance(reply, ReplyStep) and reply.outputChannels == ["result"]
        assert isinstance(wf.body, Sequence) and isinstance(wf.body.step2, Sequence)

    def test_trailing_reply_is_not_duplicated(self):
        wf, _ = compile_src(SIMPLE)
        assert sum(isinstance(s, ReplyStep) for s in leaves(wf.body)) == 1

    def test_implicit_reply_when_no_reference(self):
        src = """
        first start;
        then action gen : SolutionStep { out result : Solution ; send result ; }
        """
        wf, _ = compile_src(src)
        steps = leaves(wf.body)
        assert isinstance(steps[-1], ReplyStep) and steps[-1].outputChannels == ["result"]
        assert names(wf.outputChannels) == ["result"]

    def test_sends_are_deduplicated(self):
        src = """
        first start;
        then action gen : SolutionStep { out r : Solution ; send r ; }
        then reference action ref : ReferenceStep { send r ; send r ; }
        """
        wf, _ = compile_src(src)
        assert names(wf.outputChannels) == ["r"]
        assert leaves(wf.body)[-1].outputChannels == ["r"]

    def test_sequence_helper_is_right_nested(self):
        a, b, c = (ReplyStep(outputChannels=[x]) for x in "abc")
        s = _sequence([a, b, c])
        assert isinstance(s, Sequence)
        assert s.step1 is a and isinstance(s.step2, Sequence)
        assert s.step2.step1 is b and s.step2.step2 is c
        assert _sequence([a]) is a

    def test_compiled_workflow_roundtrips_through_json(self):
        wf, _ = compile_src(LOOP)
        again = type(wf).model_validate_json(wf.model_dump_json())
        assert again == wf


class TestCompilerChannels:
    def test_input_many_uses_list_structure(self):
        wf, _ = compile_src("first start; then input xs : String* ;")
        assert wf.inputChannels[0].structure == ChannelStructure.List

    def test_init_creates_internal_channel_with_value(self):
        src = 'first start; then init e : Explanation := "(none)" ; then init n : Int := 7 ;'
        wf, _ = compile_src(src)
        by_name = {c.name: c for c in wf.internalChannels}
        assert by_name["e"].init_with_value == "(none)"
        assert by_name["n"].init_with_value == "7"             # ints are stringified

    def test_out_channel_gets_default_init_value(self):
        wf, _ = compile_src("first start; then action a : SolutionStep { out r : Solution ; }")
        assert wf.internalChannels[0].init_with_value == ""

    def test_out_many_uses_list_structure(self):
        wf, _ = compile_src("first start; then action a : SolutionStep { out r : Solution* ; }")
        assert wf.internalChannels[0].structure == ChannelStructure.List

    def test_redeclaring_out_with_same_structure_is_fine(self):
        src = """
        first start;
        then init e : Explanation := "x" ;
        then action a : SolutionStep { out e : Explanation ; }
        """
        wf, _ = compile_src(src)
        assert names(wf.internalChannels) == ["e"]
        assert wf.internalChannels[0].init_with_value == "x"   # the first declaration wins

    def test_redeclaring_out_with_other_structure_fails(self):
        src = """
        first start;
        then action a : SolutionStep { out r : Solution ; }
        then action b : SolutionStep { out r : Solution* ; }
        """
        with pytest.raises(ValueError, match="two different types"):
            compile_src(src)

    def test_duplicate_input(self):
        with pytest.raises(ValueError, match="declared several times"):
            compile_src("first start; then input a : String ; then input a : String ;")

    def test_input_then_init_same_name(self):
        with pytest.raises(ValueError, match="declared several times"):
            compile_src('first start; then input a : String ; then init a : String := "x" ;')

    def test_out_on_input_name(self):
        src = """
        first start;
        then input a : String ;
        then action g : SolutionStep { out a : Solution ; }
        """
        with pytest.raises(ValueError, match="already declared as an input"):
            compile_src(src)

    def test_cannot_send_input(self):
        src = """
        first start;
        then input a : String ;
        then reference action r : ReferenceStep { send a ; }
        """
        with pytest.raises(ValueError, match="Cannot send input channel"):
            compile_src(src)

    def test_send_undeclared_channel(self):
        src = "first start; then reference action r : ReferenceStep { send ghost ; }"
        with pytest.raises(ValueError, match="not declared"):
            compile_src(src)

    def test_undeclared_input_channel_is_caught_by_target_validation(self):
        src = """
        first start;
        then action g : SolutionStep { in ghost ; out r : Solution ; }
        """
        with pytest.raises(Exception, match="not declared"):
            compile_src(src)


class TestCompilerGeneration:
    def test_defaults(self):
        wf, _ = compile_src(SIMPLE)
        gen = leaves(wf.body)[0].task
        cfg = gen.config
        d = Defaults()
        assert cfg.skill == "generate"                        # explicit redefinition
        assert cfg.nbSpawns == d.nb_spawns == 1
        assert cfg.nbRequiredAnswers == cfg.nbSpawns          # None -> nbSpawns
        assert cfg.nbDifferentAgents == d.nb_different_agents
        assert cfg.agentTimeout == d.agent_timeout
        assert cfg.onAgentFailure == OnAgentFailure.RETRY_SAME
        assert cfg.maxEffort == d.max_effort and cfg.maxRetry == d.max_retry
        assert gen.solutionJoin == SolutionJoin.FIRST
        assert gen.inputChannels == ["spec"]
        assert gen.feedbackChannels == []
        assert gen.outputChannels == ["result"]

    def test_default_skill_when_not_redefined(self):
        wf, _ = compile_src("first start; then action a : SolutionStep { out r : Solution ; }")
        assert leaves(wf.body)[0].task.config.skill == "default"

    def test_explanation_inputs_become_feedback_channels(self):
        src = """
        first start;
        then input spec : String ;
        then init errors : Explanation := "(none)" ;
        then action g : SolutionStep { in spec ; in errors ; out r : Solution ; }
        """
        wf, _ = compile_src(src)
        gen = leaves(wf.body)[0].task
        assert gen.inputChannels == ["spec"]
        assert gen.feedbackChannels == ["errors"]

    def test_config_overrides(self):
        src = """
        first start;
        then action g : SolutionStep {
            :>> skill = "s" ;
            :>> nbSpawns = 3 ;
            :>> nbDifferentAgents = 2 ;
            :>> agentTimeout = 1234 ;
            :>> maxRetry = 5 ;
            :>> override_repo = "http://127.0.0.1:9001" ;
            out r : Solution ;
        }
        """
        wf, _ = compile_src(src)
        cfg = leaves(wf.body)[0].task.config
        assert (cfg.nbSpawns, cfg.nbDifferentAgents, cfg.agentTimeout, cfg.maxRetry) == (3, 2, 1234, 5)
        assert cfg.nbRequiredAnswers == 3                     # follows nbSpawns
        assert cfg.override_repo == "http://127.0.0.1:9001"

    def test_explicit_nb_required_answers_wins(self):
        src = """
        first start;
        then action g : SolutionStep { :>> nbSpawns = 3 ; :>> nbRequiredAnswers = 2 ; out r : Solution ; }
        """
        wf, _ = compile_src(src)
        cfg = leaves(wf.body)[0].task.config
        assert (cfg.nbSpawns, cfg.nbRequiredAnswers) == (3, 2)

    def test_solution_join_override(self):
        src = 'first start; then action g : SolutionStep { :>> solutionJoin = "List" ; out r : Solution ; }'
        wf, _ = compile_src(src)
        assert leaves(wf.body)[0].task.solutionJoin == SolutionJoin.LIST

    def test_generation_requires_an_output(self):
        with pytest.raises(ValueError, match="needs at least one `out`"):
            compile_src("first start; then action g : SolutionStep { }")

    def test_evaluation_only_field_rejected_on_generation(self):
        src = 'first start; then action g : SolutionStep { :>> consensusType = "Majority" ; out r : Solution ; }'
        with pytest.raises(ValueError, match="unknown redefinition"):
            compile_src(src)

    def test_unknown_redefinition(self):
        src = 'first start; then action g : SolutionStep { :>> bogus = 1 ; out r : Solution ; }'
        with pytest.raises(ValueError, match="unknown redefinition ':>> bogus'"):
            compile_src(src)

    def test_prompt_is_ignored_with_a_warning(self):
        src = 'first start; then action g : SolutionStep { :>> prompt = "hi" ; out r : Solution ; }'
        wf, warns = compile_src(src)
        assert len(warns) == 1 and "prompt" in warns[0]
        assert isinstance(leaves(wf.body)[0], GenerationStep)

    def test_spawn_on_generation_sets_nb_spawns_and_warns_about_policy(self):
        src = """
        first start;
        then spawn 4 action g : SolutionStep with Majority { out r : Solution ; }
        """
        wf, warns = compile_src(src)
        cfg = leaves(wf.body)[0].task.config
        assert (cfg.nbSpawns, cfg.nbRequiredAnswers) == (4, 4)
        assert any("policy 'Majority' ignored" in w for w in warns)


class TestCompilerEvaluation:
    def get_eval(self, src):
        wf, warns = compile_src(src)
        ev = next(s for s in leaves(wf.body) if isinstance(s, EvaluationStep))
        return wf, ev.task, warns

    def test_defaults_and_channel_roles(self):
        wf, ev, _ = self.get_eval(SIMPLE)
        assert ev.consensusType == DecisionMode.MAJORITY
        assert ev.outputKind == EvaluationKind.BOOLEAN
        assert ev.specificationChannels == ["spec"]           # workflow input => criteria
        assert ev.solutionChannels == ["result"]              # other channel => data to evaluate
        assert ev.evaluationChannel == "ok"
        assert ev.explanationChannel == "check_explanation"   # synthesized
        decl = {c.name: c for c in wf.internalChannels}
        assert "check_explanation" in decl

    def test_second_out_is_the_explanation_channel(self):
        src = """
        first start;
        then input spec : String ;
        then action g : SolutionStep { out r : Solution ; }
        then action c : EvaluationStep { in spec ; in r ; out ok : Evaluation ; out why : Explanation ; }
        """
        wf, ev, _ = self.get_eval(src)
        assert (ev.evaluationChannel, ev.explanationChannel) == ("ok", "why")
        assert "c_explanation" not in names(wf.internalChannels)

    def test_only_inputs_means_everything_is_evaluated(self):
        src = """
        first start;
        then input spec : String ;
        then action c : EvaluationStep { in spec ; out ok : Evaluation ; }
        """
        _, ev, _ = self.get_eval(src)
        assert ev.specificationChannels == [] and ev.solutionChannels == ["spec"]

    @pytest.mark.parametrize("policy,mode", [("Majority", DecisionMode.MAJORITY),
                                             ("Unanimity", DecisionMode.UNANIMITY)])
    def test_spawn_policy_sets_consensus(self, policy, mode):
        src = f"""
        first start;
        then action g : SolutionStep {{ out r : Solution ; }}
        then spawn 3 action c : EvaluationStep with {policy} {{ in r ; out ok : Evaluation ; }}
        """
        _, ev, warns = self.get_eval(src)
        assert ev.consensusType == mode
        assert (ev.config.nbSpawns, ev.config.nbRequiredAnswers) == (3, 3)
        assert warns == []

    def test_evaluation_overrides(self):
        src = """
        first start;
        then action g : SolutionStep { out r : Solution ; }
        then action c : EvaluationStep {
            :>> consensusType = "Debate" ;
            :>> outputKind = "Numerical" ;
            in r ; out ok : Evaluation ;
        }
        """
        _, ev, _ = self.get_eval(src)
        assert ev.consensusType == DecisionMode.DEBATE
        assert ev.outputKind == EvaluationKind.NUMERICAL

    def test_generation_only_field_rejected_on_evaluation(self):
        src = """
        first start;
        then action g : SolutionStep { out r : Solution ; }
        then action c : EvaluationStep { :>> solutionJoin = "List" ; in r ; out ok : Evaluation ; }
        """
        with pytest.raises(ValueError, match="unknown redefinition"):
            compile_src(src)

    def test_evaluation_requires_an_output(self):
        src = """
        first start;
        then action g : SolutionStep { out r : Solution ; }
        then action c : EvaluationStep { in r ; }
        """
        with pytest.raises(ValueError, match="needs at least one `out`"):
            compile_src(src)


class TestCompilerLoops:
    def test_loop_shape(self):
        wf, _ = compile_src(LOOP)
        loop = leaves(wf.body)[0]
        assert isinstance(loop, RetryUntilValidated)
        assert loop.acceptanceChannel == "ok"
        assert loop.fuel == 3
        assert loop.anchor == "retry"
        gen, check = leaves(loop.body)
        assert isinstance(gen, GenerationStep) and isinstance(check, EvaluationStep)

    def test_single_step_body_is_not_wrapped_in_a_sequence(self):
        src = """
        first start;
        then loop action l with max 2 retries {
            then action c : EvaluationStep { out ok : Evaluation ; }
        } until ok is accepted ;
        """
        wf, _ = compile_src(src)
        loop = leaves(wf.body)[0]
        assert isinstance(loop.body, EvaluationStep)

    def test_nested_loops(self):
        src = """
        first start;
        then input spec : String ;
        then loop action outer with max 2 retries {
            then loop action inner with max 4 retries {
                then action g : SolutionStep { in spec ; out r : Solution ; }
                then action c1 : EvaluationStep { in r ; out syntax_ok : Evaluation ; }
            } until syntax_ok is accepted ;
            then action c2 : EvaluationStep { in spec ; in r ; out sem_ok : Evaluation ; }
        } until sem_ok is accepted ;
        """
        wf, _ = compile_src(src)
        outer = leaves(wf.body)[0]
        assert isinstance(outer, RetryUntilValidated) and outer.fuel == 2
        inner, c2 = leaves(outer.body)
        assert isinstance(inner, RetryUntilValidated) and inner.fuel == 4
        assert inner.acceptanceChannel == "syntax_ok"
        assert isinstance(c2, EvaluationStep)

    def test_only_accepted_is_supported(self):
        src = """
        first start;
        then loop action l with max 2 retries {
            then action c : EvaluationStep { out ok : Evaluation ; }
        } until ok is rejected ;
        """
        with pytest.raises(ValueError, match="only `until ... accepted`"):
            compile_src(src)

    def test_empty_loop_body_rejected(self):
        src = "first start; then loop action l with max 2 retries { } until ok is accepted ;"
        with pytest.raises(ValueError, match="no step in its body"):
            compile_src(src)

    def test_loop_with_only_declarations_is_rejected(self):
        src = """
        first start;
        then loop action l with max 2 retries {
            then init ok : Evaluation := "no" ;
        } until ok is accepted ;
        """
        with pytest.raises(ValueError, match="no step in its body"):
            compile_src(src)

    def test_undeclared_acceptance_channel(self):
        src = """
        first start;
        then loop action l with max 2 retries {
            then action g : SolutionStep { out r : Solution ; }
        } until nope is accepted ;
        """
        with pytest.raises(Exception, match="not declared"):
            compile_src(src)


class TestCompilerReference:
    def test_message_redefinition_is_ignored_with_warning(self):
        src = """
        first start;
        then action g : SolutionStep { out r : Solution ; }
        then reference action ref : ReferenceStep { :>> message = "done" ; send r ; }
        """
        wf, warns = compile_src(src)
        assert len(warns) == 1 and "message" in warns[0]
        assert leaves(wf.body)[-1].outputChannels == ["r"]

    def test_unknown_redefinition_rejected(self):
        src = """
        first start;
        then action g : SolutionStep { out r : Solution ; }
        then reference action ref : ReferenceStep { :>> bogus = "x" ; send r ; }
        """
        with pytest.raises(ValueError, match="unknown redefinition"):
            compile_src(src)

    @pytest.mark.parametrize("member", ["in r ;", "out z : Solution ;"])
    def test_only_send_and_message_supported(self, member):
        src = f"""
        first start;
        then action g : SolutionStep {{ out r : Solution ; }}
        then reference action ref : ReferenceStep {{ {member} send r ; }}
        """
        with pytest.raises(ValueError, match="only `send` and `:>> message`"):
            compile_src(src)

    def test_reference_in_the_middle_does_not_suppress_final_reply(self):
        src = """
        first start;
        then action g : SolutionStep { out r : Solution ; send r ; }
        then reference action ref : ReferenceStep { send r ; }
        then action g2 : SolutionStep { out r2 : Solution ; }
        """
        wf, _ = compile_src(src)
        steps = leaves(wf.body)
        assert isinstance(steps[1], ReplyStep)
        assert isinstance(steps[-1], ReplyStep)               # implicit trailing reply


class TestCompilerDefaultsAndWarnings:
    def test_custom_defaults_are_applied(self):
        d = Defaults(
            skill="custom", nb_spawns=2, agent_timeout=5, max_retry=9,
            solution_join=SolutionJoin.LIST, consensus_type=DecisionMode.UNANIMITY,
            evaluation_kind=EvaluationKind.TEXTUAL, channel_init_value="?",
            many_structure=ChannelStructure.Bag,
        )
        src = """
        first start;
        then input xs : String* ;
        then action g : SolutionStep { in xs ; out r : Solution ; }
        then action c : EvaluationStep { in xs ; in r ; out ok : Evaluation ; }
        """
        wf, _ = compile_src(src, d)
        gen, ev = leaves(wf.body)[:2]
        assert wf.inputChannels[0].structure == ChannelStructure.Bag
        assert gen.task.config.skill == "custom"
        assert (gen.task.config.nbSpawns, gen.task.config.nbRequiredAnswers) == (2, 2)
        assert gen.task.config.agentTimeout == 5 and gen.task.config.maxRetry == 9
        assert gen.task.solutionJoin == SolutionJoin.LIST
        assert ev.task.consensusType == DecisionMode.UNANIMITY
        assert ev.task.outputKind == EvaluationKind.TEXTUAL
        assert all(c.init_with_value == "?" for c in wf.internalChannels)

    def test_custom_evaluation_step_types(self):
        d = Defaults(evaluation_step_types=frozenset({"Judge"}))
        src = """
        first start;
        then action g : SolutionStep { out r : Solution ; }
        then action c : Judge { in r ; out ok : Evaluation ; }
        then action c2 : EvaluationStep { in r ; out z : Solution ; }
        """
        wf, _ = compile_src(src, d)
        kinds = [type(s) for s in leaves(wf.body)[:3]]
        assert kinds == [GenerationStep, EvaluationStep, GenerationStep]

    def test_ignored_redefinitions_configurable(self):
        d = Defaults(ignored_redefinitions=frozenset())
        src = 'first start; then action g : SolutionStep { :>> prompt = "x" ; out r : Solution ; }'
        with pytest.raises(ValueError, match="unknown redefinition"):
            compile_src(src, d)

    def test_default_warning_channel_uses_warnings_module(self):
        src = 'first start; then action g : SolutionStep { :>> prompt = "x" ; out r : Solution ; }'
        with pytest.warns(CompilationWarning, match="prompt"):
            compile_workflow(parse(src))

    def test_compile_does_not_mutate_the_ast(self):
        ast = parse(SIMPLE)
        before = ast.model_dump()
        compile_workflow(ast)
        assert ast.model_dump() == before

    def test_compilation_is_deterministic(self):
        a, _ = compile_src(LOOP)
        b, _ = compile_src(LOOP)
        assert a == b


# =========================================================================== #
# 3. End-to-end: realistic workflows
# =========================================================================== #
EMFATIC = """
first start;
then input domainDescription : String ;
then init syntaxErrors : Explanation := "(no comment yet)" ;
then init semanticExplanation : Explanation := "(no comment yet)" ;
then loop action generateAndCheck with max 3 retries {
    then loop action generateAndSyntacticCheck with max 3 retries {
        then action generation : SolutionStep {
            :>> skill = "Generate Emfatic metamodels" ;
            :>> prompt = "Generate a domain model." ;
            in domainDescription ; in syntaxErrors ; in semanticExplanation ;
            out domainModel : Solution;
        }
        then action syntacticCheck : EvaluationStep {
            :>> skill = "Check the syntax" ;
            in domainModel ;
            out isSyntacticallyCorrect : Evaluation;
            out syntaxErrors : Explanation;
        }
    } until isSyntacticallyCorrect is accepted ;
    then spawn 3 action semanticCheck : EvaluationStep with Unanimity {
        :>> skill = "Check semantics" ;
        in domainDescription ; in domainModel ;
        out isSemanticallyCorrect : Evaluation ;
        out semanticExplanation : Explanation;
    }
} until isSemanticallyCorrect is accepted;
then reference action outputToUser : ReferenceStep {
    :>> message = "Here is the model." ;
    send domainModel ;
}
"""


def test_emfatic_like_workflow():
    wf, warns = compile_src(EMFATIC)
    assert len(warns) == 2                                    # prompt + message ignored
    assert names(wf.inputChannels) == ["domainDescription"]
    assert names(wf.outputChannels) == ["domainModel"]
    assert {"syntaxErrors", "semanticExplanation", "isSyntacticallyCorrect",
            "isSemanticallyCorrect"} <= set(names(wf.internalChannels))

    outer, reply = leaves(wf.body)
    assert isinstance(outer, RetryUntilValidated) and isinstance(reply, ReplyStep)
    inner, sem = leaves(outer.body)
    assert isinstance(inner, RetryUntilValidated)
    gen, syn = leaves(inner.body)
    assert gen.task.feedbackChannels == ["syntaxErrors", "semanticExplanation"]
    assert gen.task.inputChannels == ["domainDescription"]
    assert syn.task.explanationChannel == "syntaxErrors"
    assert sem.task.config.nbSpawns == 3
    assert sem.task.consensusType == DecisionMode.UNANIMITY
    assert sem.task.specificationChannels == ["domainDescription"]
    assert sem.task.solutionChannels == ["domainModel"]


EXAMPLE_DIRS = [Path(__file__).parent, Path(__file__).parent / "examples"]
EXAMPLE_FILES = sorted({p for d in EXAMPLE_DIRS if d.is_dir() for p in d.glob("*.wof")})


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.name)
def test_example_files(path):
    wf = compile_workflow(parse(path.read_text(encoding="utf-8")), on_warning=lambda _m: None)
    assert leaves(wf.body)[-1].__class__ is ReplyStep


# =========================================================================== #
# 4. Command line interface
# =========================================================================== #
@pytest.fixture
def wof_file(tmp_path):
    p = tmp_path / "w.wof"
    p.write_text(SIMPLE, encoding="utf-8")
    return p


class TestCli:
    def test_full_compilation_to_stdout(self, wof_file, capsys):
        assert main([str(wof_file)]) == 0
        assert capsys.readouterr().out.strip() != ""

    def test_output_file(self, wof_file, tmp_path):
        out = tmp_path / "out.txt"
        assert main([str(wof_file), "-o", str(out)]) == 0
        content = out.read_text(encoding="utf-8")
        assert content.strip() != "" and content.endswith("\n")

    def test_ast_mode_prints_valid_json(self, wof_file, capsys):
        assert main([str(wof_file), "--ast"]) == 0
        data = json.loads(capsys.readouterr().out)
        assert [s["kind"] for s in data["statements"]] == ["input", "action", "action", "reference"]

    def test_tree_mode(self, wof_file, capsys):
        assert main([str(wof_file), "--tree"]) == 0
        assert "workflow" in capsys.readouterr().out

    def test_missing_file_returns_2(self, tmp_path, capsys):
        assert main([str(tmp_path / "nope.wof")]) == 2
        assert "cannot read" in capsys.readouterr().err

    def test_syntax_error_returns_1_with_location(self, tmp_path, capsys):
        p = tmp_path / "bad.wof"
        p.write_text("first start;\nthen input a String ;\n", encoding="utf-8")
        assert main([str(p)]) == 1
        err = capsys.readouterr().err
        assert "syntax error" in err and ":2:" in err

    def test_invalid_workflow_returns_1(self, tmp_path, capsys):
        p = tmp_path / "bad.wof"
        p.write_text("first start; then spawn 0 action a : T with Majority { }", encoding="utf-8")
        assert main([str(p)]) == 1
        assert "invalid workflow" in capsys.readouterr().err

    def test_compilation_error_returns_1(self, tmp_path, capsys):
        p = tmp_path / "bad.wof"
        p.write_text("first start; then action g : SolutionStep { }", encoding="utf-8")
        assert main([str(p)]) == 1
        assert "compilation error" in capsys.readouterr().err

    def test_ast_mode_skips_compilation(self, tmp_path):
        # would fail to compile (generation without `out`) but is a valid AST
        p = tmp_path / "ok.wof"
        p.write_text("first start; then action g : SolutionStep { }", encoding="utf-8")
        assert main([str(p), "--ast"]) == 0