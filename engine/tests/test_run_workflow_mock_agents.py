import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

from orchestrator.orchestration.run import run_workflow
from orchestrator.workflow_datatype.workflows import Workflow

@pytest.fixture
def start_mock_generator_agent():
    agent_script = (
        Path(__file__).parent
        / "unit_test_generator_agent"
        / "generator_agent_9000.py"
    )
    process = subprocess.Popen([sys.executable, str(agent_script)])

    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Agent server exited before becoming ready")
            try:
                with socket.create_connection(("127.0.0.1", 9000), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Agent server did not become ready on port 9000")

        yield
    finally:
        process.terminate()
        process.wait(timeout=5)

def test_minimal_generation_workflow_runs(start_mock_generator_agent):
    file = (Path(__file__).parent / "minimal_generation_workflow.yaml")
    data = yaml.safe_load(file.read_text())

    workflow = Workflow.model_validate(data)

    result_store = run_workflow(workflow, ["hello"])

    assert result_store.store["final-result"]=="mock generated text :-*"
