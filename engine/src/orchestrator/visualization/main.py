import argparse
import sys
from pathlib import Path

import yaml

from orchestrator.visualization.plantuml import workflow_to_plantuml
from orchestrator.workflow_datatype.workflows import Workflow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert a workflow YAML file into a PlantUML diagram."
    )
    parser.add_argument("input", type=Path, help="path of the workflow YAML file")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="output .puml file (default: same name as the input, with .puml extension)",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        return 1

    data = yaml.safe_load(args.input.read_text())
    workflow = Workflow.model_validate(data)
    puml = workflow_to_plantuml(workflow)

    output = args.output or args.input.with_suffix(".puml")
    output.write_text(puml)
    print(f"Written: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())