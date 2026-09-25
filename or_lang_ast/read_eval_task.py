import json
import sys
from pathlib import Path
from agent_task import EvaluationConfig
from pydantic import ValidationError

if len(sys.argv) != 2:
    print(f"Usage: python {sys.argv[0]} <path_to_json_file>")
    sys.exit(1)

file_path = Path(sys.argv[1])

data = json.loads(file_path.read_text())

print("-- Trying to read an EvaluationConfig. --")


try:
    config = EvaluationConfig.model_validate(data)
    print("Skill:", config.config.skill)
    print("Evaluation Channel:", config.evaluationChannel)
    print("Full Config:", config)
except ValidationError as e:
    print("Invalid EvaluationConfig file:", e)


