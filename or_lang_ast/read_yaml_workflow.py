import sys
from pydantic import ValidationError, TypeAdapter

from workflows import Step
import yaml

step_adapter = TypeAdapter(Step)

if len(sys.argv) != 2:
    print(f"Usage: python {sys.argv[0]} <path_to_yaml_file>")
    sys.exit(1)

with open(sys.argv[1], "r") as f:
    raw_data = yaml.safe_load(f)




print("-- Trying to read a Workflow. --")

try:
    step = step_adapter.validate_python(raw_data)
    print("Step:", step)

except ValidationError as e:
    print("Invalid Step file:", e)



