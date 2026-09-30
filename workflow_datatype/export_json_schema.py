from workflows import Workflow
import json


workflow_schema = Workflow.model_json_schema()

with open("workflow_schema.json", "w") as f:
    json.dump(workflow_schema, f, indent=2)
