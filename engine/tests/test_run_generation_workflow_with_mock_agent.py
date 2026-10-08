import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

from orchestrator.orchestration.run import Runner
from orchestrator.workflow_datatype.workflows import Workflow
from mock_tools import start_mock_agent

@pytest.fixture
def start_mock_generator_agent():
    yield from start_mock_agent(agent_dir="unit_test_generator_agent", agent_file="generator_agent_9000.py", port=9010)


async def test_minimal_generation_workflow_runs(start_mock_generator_agent):
    file = (Path(__file__).parent / "minimal_generation_workflow.yaml")
    data = yaml.safe_load(file.read_text())

    workflow = Workflow.model_validate(data)

    result_store = await Runner(None).run_workflow(workflow, ["hello"])

    assert result_store.read("final-result")=="mock generated text :-*"

async def test_alt_generation_workflow_runs(start_mock_generator_agent):
    file = (Path(__file__).parent / "alt_generation_workflow.yaml")
    data = yaml.safe_load(file.read_text())

    workflow = Workflow.model_validate(data)

    result_store = await Runner(None).run_workflow(workflow, ["hello"])

    assert result_store.read("final-result")== ["mock generated text :-*", "mock generated text :-*"]

async def test_accumulation_workflow_runs(start_mock_generator_agent):
    file = (Path(__file__).parent / "minimal_accumulation_workflow.yaml")
    data = yaml.safe_load(file.read_text())

    workflow = Workflow.model_validate(data)

    result_store = await Runner(None).run_workflow(workflow, ["hello"])

    assert result_store.read("accu")== 5*["mock generated text :-*"]