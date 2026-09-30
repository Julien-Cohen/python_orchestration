from src.orchestrator.orchestration.state import Store
from src.orchestrator.workflow_datatype.workflows import Workflow


def run_workflow(workflow: Workflow, inputs):
    store = Store(workflow, inputs)
