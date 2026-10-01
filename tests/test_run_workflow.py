from pathlib import Path

import yaml

from orchestrator.orchestration.run import run_workflow
from orchestrator.workflow_datatype.workflows import Workflow



def test_minimal_statement_workflow_runs(capsys):
    file = (Path(__file__).parent / "minimal_statement_workflow.yaml")
    data = yaml.safe_load(file.read_text())

    workflow = Workflow.model_validate(data)

    run_workflow(workflow, [])

    assert capsys.readouterr().out.strip() == "hello"
