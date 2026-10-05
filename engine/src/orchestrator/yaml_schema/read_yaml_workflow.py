import sys
from pydantic import ValidationError

import yaml

from orchestrator.workflow_datatype.workflows import Workflow


def read_file(filename) -> Workflow:
    with open(filename, "r") as f:
        raw_data = yaml.safe_load(f)

    return Workflow.model_validate(raw_data)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <path_to_yaml_file>")
        sys.exit(1)

    print("-- Trying to read a Workflow. --")

    try:
        workflow = read_file(sys.argv[1])
        print("Workflow:", workflow)

    except ValidationError as e:
        print("Invalid Workflow file:", e)

if __name__ == "__main__":
    main()
