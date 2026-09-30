import json
import sys

from orchestrator.workflow_datatype.workflows import Workflow

def main():
    workflow_schema = Workflow.model_json_schema()

    print(json.dumps(workflow_schema, indent=2))


if __name__ == "__main__":
    main()