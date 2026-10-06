from pathlib import Path

import yaml

from orchestrator.orchestration.run import Runner
from orchestrator.workflow_datatype.workflows import Workflow



async def test_minimal_statement_workflow_runs(capsys):
    file = (Path(__file__).parent / "minimal_statement_workflow.yaml")
    data = yaml.safe_load(file.read_text())

    workflow = Workflow.model_validate(data)

    await Runner(None).run_workflow(workflow, ["foo"])

    assert capsys.readouterr().out.strip() == "hello"
