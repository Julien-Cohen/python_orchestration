import sys
from pathlib import Path
from pydantic import ValidationError, TypeAdapter

from workflows import Step

step_adapter = TypeAdapter(Step)

if len(sys.argv) != 2:
    print(f"Usage: python {sys.argv[0]} <path_to_json_file>")
    sys.exit(1)

json_bytes = Path(sys.argv[1]).read_bytes()


print("-- Trying to read a Workflow. --")

try:
    step = step_adapter.validate_json(json_bytes)
    print("Step:", step)

except ValidationError as e:
    print("Invalid Step file:", e)



