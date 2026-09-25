import json
import sys
from pathlib import Path
from agent_task import GenerationConfig, EvaluationConfig
from pydantic import ValidationError

if len(sys.argv) != 2:
    print(f"Usage: python {sys.argv[0]} <path_to_json_file>")
    sys.exit(1)

file_path = Path(sys.argv[1])

data = json.loads(file_path.read_text())

print("-- Trying to read a GenerationConfig. --")

try:
    config = GenerationConfig.model_validate(data)
    print("Skill:", config.config.skill)
    print("Output Solution Channel:", config.outputChannel)
    print("Full Configuration:", config)
except ValidationError as e:
    print("Invalid GenerationConfig file:", e)



