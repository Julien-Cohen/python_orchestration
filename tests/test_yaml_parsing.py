from pathlib import Path

import yaml

from orchestrator.workflow_datatype.workflows import Workflow


def test_minimal_sequence_workflow_loads():
    path = Path(__file__).parent / "minimal_sequence_workflow.yaml"
    data = yaml.safe_load(path.read_text())

    workflow = Workflow.model_validate(data)

    assert workflow.type == "workflow"
    assert workflow.body.type == "sequence"