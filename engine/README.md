A datatype to specify MOSAICO workflows together with an engine to run them.


# Install the code 

```bash
  pip install -e .
```
Or:
```bash
  uv sync
```

# Generate the YAML schema

The YAML schema is generated from the Pydantic AST datatype.

## Prerequisites

Install the "yq" command.

```
    sudo snap install yq
```

## Generate the YAML schema from the JSON schema

```bash
    python -m orchestrator.yaml_schema.export_json_schema > src/orchestrator/yaml_schema/workflow_schema.json
    yq -p json -oy -P src/orchestrator/yaml_schema/workflow_schema.json > src/orchestrator/yaml_schema/workflow_schema.yaml
```


# Test read a YAML file

## Emfatic example

```bash
    python -m orchestrator.yaml_schema.read_yaml_workflow tests/emfatic/emfatic_workflow.yaml 
```

```bash
    python -m orchestrator.yaml_schema.read_yaml_workflow tests/emfatic/generated_emfatic_workflow_fresh.yaml 
```

## Requirement generation example

```bash
    python -m orchestrator.yaml_schema.read_yaml_workflow tests/requirement_generation/req_gen_workflow.yaml  
```


## Requirement patch example

```bash
    python -m orchestrator.yaml_schema.read_yaml_workflow tests/requirement_patch/req_patch_workflow.yaml 
```


# Unit tests

```bash
uv sync --extra test
uv run pytest -v
```


# Compiler WOF -> YAML

The orchestration engine reads YAML files in its own format. We provide a higher level language with a SysML-like syntax called WOF. A compiler is provided to transform high-level WOF workflow into low-level YAML orchestrations.

Concrete Syntax for MOSAICO workflows


## Run the compiler

### Compile to the low-level orchestration language

#### Emfatic

On stdout:
```bash
python -m wof wof_examples/emfatic_workflow.wof
```

In an output file:
```bash
python -m wof wof_examples/emfatic_workflow_fresh.wof > generated_emfatic_workflow_fresh.yaml
```

#### Requirement patch

In an output file:
```bash
python -m wof wof_examples/requirement_patcher_workflow.wof > generated_requirement_patcher_workflow.yaml
```

### Show intermediate steps

Show the parsed AST (WOF language):
```bash
python -m wof wof_examples/emfatic_workflow.wof --ast
```

Show the parsed raw tree (Lark):
```bash
python -m wof wof_examples/emfatic_workflow.wof --tree
```




