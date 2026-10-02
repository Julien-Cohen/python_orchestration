from pathlib import Path

import pytest
import yaml

from orchestrator.workflow_datatype.workflows import Workflow


def test_minimal_sequence_workflow_loads():
    file = (Path(__file__).parent / "minimal_sequence_workflow.yaml")
    data = yaml.safe_load(file.read_text())

    workflow = Workflow.model_validate(data)

    assert workflow.type == "workflow"
    assert workflow.body.type == "sequence"


def test_emfatic_workflow_loads():
    file = (Path(__file__).parent / "emfatic" / "emfatic_workflow.yaml")
    data = yaml.safe_load(file.read_text())

    workflow = Workflow.model_validate(data)

    assert workflow.type == "workflow"
    assert workflow.body.type == "retry-loop"


def test_req_gen_workflow_loads():
    file = (Path(__file__).parent / "requirement_generation" / "req_gen_workflow.yaml")
    data = yaml.safe_load(file.read_text())

    workflow = Workflow.model_validate(data)

    assert workflow.type == "workflow"
    assert workflow.body.type == "accumulate-loop"


def test_req_patch_workflow_loads():
    file = (Path(__file__).parent / "requirement_patch" / "req_patch_workflow.yaml")
    data = yaml.safe_load(file.read_text())

    workflow = Workflow.model_validate(data)

    assert workflow.type == "workflow"
    assert workflow.body.type == "sequence"

def test_minimal_statement_workflow_loads():
    file = (Path(__file__).parent / "minimal_statement_workflow.yaml")
    data = yaml.safe_load(file.read_text())

    workflow = Workflow.model_validate(data)

    assert workflow.type == "workflow"
    assert workflow.body.type == "algorithmic-step"

def test_duplicate_channel_names_raise_exception():
    file = (Path(__file__).parent / "error_cases" / "duplicate.yaml")
    data = yaml.safe_load(file.read_text())

    with pytest.raises(
        Exception,
        match=r"Some channels are declared several times: \['specification'\]",
    ):
        Workflow.model_validate(data)
