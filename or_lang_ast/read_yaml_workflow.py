import sys
from pydantic import ValidationError

from workflows import Workflow, find_duplicate_channel_names
import yaml


if len(sys.argv) != 2:
    print(f"Usage: python {sys.argv[0]} <path_to_yaml_file>")
    sys.exit(1)

with open(sys.argv[1], "r") as f:
    raw_data = yaml.safe_load(f)




print("-- Trying to read a Workflow. --")

try:
    workflow = Workflow.model_validate(raw_data)
    duplicates = find_duplicate_channel_names(workflow)
    if (duplicates != []):
        raise Exception("Some channels are declared several times: " + str(duplicates))
    print("Workflow:", workflow)

except ValidationError as e:
    print("Invalid Workflow file:", e)



