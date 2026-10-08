from pathlib import Path

import pytest
import yaml

from orchestrator.orchestration.run import Runner
from orchestrator.workflow_datatype.workflows import Workflow
from mock_tools import start_mock_agent


@pytest.fixture
def start_mock_generator_agent():
    yield from start_mock_agent(agent_dir="unit_test_generator_agent", agent_file="generator_agent_9000.py", port=9010)


@pytest.fixture
def start_mock_evaluator_agent():
    yield from start_mock_agent(agent_dir="unit_test_evaluator_agent", agent_file="evaluator_agent_9000.py", port=9020, mock="ko")


async def test_minimal_evaluation_workflow_runs(start_mock_generator_agent, start_mock_evaluator_agent):
    file = (Path(__file__).parent / "minimal_evaluation_workflow.yaml")
    data = yaml.safe_load(file.read_text())

    workflow = Workflow.model_validate(data)

    result_store = await Runner(None).run_workflow(workflow, ["hello"])

    assert result_store.read("generated")=="mock generated text :-*"
    assert result_store.read("correctness")=="ko"

async def test_minimal_retry_workflow_runs(start_mock_generator_agent, start_mock_evaluator_agent):
    file = (Path(__file__).parent / "minimal_retry_workflow.yaml")
    data = yaml.safe_load(file.read_text())

    workflow = Workflow.model_validate(data)

    result_store = await Runner(None).run_workflow(workflow, ["hello"])

    assert result_store.read("generated")=="mock generated text :-*"
    assert result_store.read("correctness")=="ko"