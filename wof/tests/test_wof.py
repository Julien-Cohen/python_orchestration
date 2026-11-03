from pathlib import Path

import pytest

from wof import (
    ActionStep,
    BoolLiteral,
    InitStep,
    InputStep,
    LexError,
    LoopStep,
    ParseError,
    Reference,
    StartStep,
    StringLiteral,
    Workflow,
    parse,
    parse_file,
    parse_with_warnings,
    tokenize,
)

EXAMPLES = Path(__file__).parent.parent / "examples"
FIXED = EXAMPLES / "emfatic_workflow_test.wof"
ORIGINAL = EXAMPLES / "emfatic_workflow_original.wof"


# ---------------------------------------------------------------- lexer


def kinds_and_values(src):
    return [(t.kind, t.value) for t in tokenize(src)][:-1]


def test_symbols_use_longest_match():
    assert kinds_and_values(":>> := :: .. : ;") == [
        ("SYM", ":>>"), ("SYM", ":="), ("SYM", "::"), ("SYM", ".."), ("SYM", ":"), ("SYM", ";"),
    ]


def test_keywords_identifiers_and_repeat_marker():
    toks = kinds_and_values("action x3 with max")
    assert toks == [("KW", "action"), ("IDENT", "x3"), ("KW", "with"), ("IDENT", "max")]


def test_string_escapes_and_comments():
    src = '"a\\"b\\n" // line\n/* block\n comment */ 42 3.5'
    assert kinds_and_values(src) == [("STRING", 'a"b\n'), ("INT", 42), ("FLOAT", 3.5)]


def test_positions_are_one_based():
    toks = tokenize("a\n  b")
    assert (toks[0].loc.line, toks[0].loc.column) == (1, 1)
    assert (toks[1].loc.line, toks[1].loc.column) == (2, 3)


def test_unterminated_string_and_comment():
    with pytest.raises(LexError, match="unterminated string"):
        tokenize('"abc')
    with pytest.raises(LexError, match="unterminated block comment"):
        tokenize("/* abc")
    with pytest.raises(LexError, match="unexpected character"):
        tokenize("init @")


# ---------------------------------------------------------------- parser: small inputs


def test_simple_steps():
    wf = parse("first start; then init a := true; then input x : String*; then output y : T[1..2];")
    start, init, inp, out = wf.steps
    assert isinstance(start, StartStep)
    assert isinstance(init, InitStep) and init.value == BoolLiteral(value=True, loc=init.value.loc)
    assert isinstance(inp, InputStep)
    assert (inp.type.multiplicity.lower, inp.type.multiplicity.upper) == (0, None)
    assert (out.type.multiplicity.lower, out.type.multiplicity.upper) == (1, 2)


def test_action_header_variants():
    wf = parse("then action a : T x3 with Unanimity { in p : P; out q : Q+; :>> k = 1; }")
    (a,) = wf.steps
    assert isinstance(a, ActionStep)
    assert (a.type, a.repeat, a.aggregation) == ("T", 3, "Unanimity")
    assert [p.name for p in a.inputs] == ["p"]
    assert [p.name for p in a.outputs] == ["q"]
    assert a.outputs[0].type.multiplicity.lower == 1
    assert a.redefinitions["k"].value == 1


def test_loop_without_until_and_without_retries():
    wf = parse("then loop action L { then init a := 1; }")
    (loop,) = wf.steps
    assert isinstance(loop, LoopStep)
    assert loop.max_retries is None and loop.until is None


def test_qualified_and_quoted_names():
    wf = parse("then init 'my var' := a::b::c;")
    assert wf.steps[0].name == "my var"
    assert wf.steps[0].value == Reference(name="a::b::c", loc=wf.steps[0].value.loc)


def test_bad_multiplicity():
    with pytest.raises(ParseError, match="invalid multiplicity"):
        parse("then input x : T[3..1];")


def test_errors_carry_location():
    with pytest.raises(ParseError) as exc:
        parse("first start;\nthen init := 1;")
    assert (exc.value.loc.line, exc.value.loc.column) == (2, 11)
    assert "expected a variable name" in str(exc.value)


def test_unclosed_block_reports_where_it_opened():
    with pytest.raises(ParseError) as exc:
        parse("then action a {\n in p : P;")
    assert "never closed" in exc.value.hint and "line 1" in exc.value.hint


# ---------------------------------------------------------------- leniency


def test_tolerated_slips_become_warnings():
    src = 'then action a { :>> k : "v" . :>> m = 1 in p : P; }'
    wf, warnings = parse_with_warnings(src)
    assert [m.name for m in wf.steps[0].members] == ["k", "m", "p"]
    messages = [w.message for w in warnings]
    assert any("'.'" in m for m in messages)
    assert any("missing ';'" in m for m in messages)


def test_strict_mode_rejects_them():
    with pytest.raises(ParseError, match="missing ';'"):
        parse("then init a := 1", strict=True)
    with pytest.raises(ParseError, match="'.' used"):
        parse("then init a := 1 .", strict=True)


def test_missing_then_is_a_warning():
    wf, warnings = parse_with_warnings("first start; init a := 1;")
    assert len(wf.steps) == 2 and len(warnings) == 1


# ---------------------------------------------------------------- the Emfatic workflow


def test_fixed_example_structure():
    wf = parse_file(str(FIXED))
    first, *rest = wf.steps
    assert isinstance(first, StartStep)
    names = [s.name for s in rest]
    assert names == ["allCorrect", "domainDescription", "syntaxErrors", "generateAndCheck", "outputToUser"]

    outer = wf.steps[4]
    assert isinstance(outer, LoopStep) and outer.max_retries == 3
    assert outer.until == Reference(name="isSemanticallyCorrect", loc=outer.until.loc)

    inner, semantic = outer.body
    assert isinstance(inner, LoopStep) and inner.name == "generateAndSyntacticCheck"
    assert inner.until.name == "isSyntacticallyCorrect"
    assert [s.name for s in inner.body] == ["generation", "syntacticCheck"]

    generation = inner.body[0]
    assert generation.type == "SolutionStep"
    assert generation.redefinitions["skill"].value.startswith("Generate Emfatic")
    explanations = next(p for p in generation.inputs if p.name == "explanations")
    assert (explanations.type.multiplicity.lower, explanations.type.multiplicity.upper) == (0, None)

    assert isinstance(semantic, ActionStep)
    assert (semantic.repeat, semantic.aggregation) == (3, "Unanimity")
    assert semantic.redefinitions["prompt"].value.startswith("Check if the given domain model")

    last = wf.steps[-1]
    assert last.type == "ReferenceStep"
    assert last.redefinitions["agent"] == Reference(name="referenceAgent", loc=last.redefinitions["agent"].loc)
    assert isinstance(last.redefinitions["description"], StringLiteral)


def test_fixed_example_warnings_are_the_three_known_slips():
    _, warnings = parse_with_warnings(FIXED.read_text())
    assert [w.loc.line for w in warnings] == [22, 30, 31]


def test_original_example_reports_the_missing_brace():
    with pytest.raises(ParseError) as exc:
        parse(ORIGINAL.read_text())
    assert exc.value.loc.line == 36
    assert "'}' is probably missing" in exc.value.hint
    assert "line 8" in exc.value.hint


def test_walk_visits_nested_steps():
    wf = parse_file(str(FIXED))
    first, *rest = wf.steps
    assert isinstance(first, StartStep)
    assert [s.name for s in rest.walk()] == [
        "allCorrect", "domainDescription", "syntaxErrors",
        "generateAndCheck", "generateAndSyntacticCheck", "generation", "syntacticCheck",
        "semanticCheck", "outputToUser",
    ]


def test_json_round_trip():
    wf = parse_file(str(FIXED))
    assert Workflow.model_validate(wf.model_dump()) == wf
    assert Workflow.model_validate_json(wf.model_dump_json()) == wf
    assert "loc" not in str(wf.to_dict())
    assert "loc" in str(wf.to_dict(include_loc=True))
