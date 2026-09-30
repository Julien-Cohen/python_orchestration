from orchestration.state import Store
from workflow_datatype.workflows import Workflow


def run(workflow: Workflow, inputs):
    store = Store(workflow, inputs)