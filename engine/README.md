A datatype to specify MOSAICO workflows.


# Install the code

```bash
  pip install -e .
```
Or:
```bash
  uv sync
```

# Generate the YAML schema

## Prerequisites: Install the "yq" command

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
python -m pip install -e ".[test]"
python -m pytest -v
```

Or:

```bash
uv sync --extra test
uv run pytest -v
```