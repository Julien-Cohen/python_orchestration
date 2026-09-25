from pydantic import TypeAdapter

from workflows import Step
import json

adapter = TypeAdapter(Step)
schema = adapter.json_schema()

with open("workflow_schema.json", "w") as f:
    json.dump(schema, f, indent=2)
