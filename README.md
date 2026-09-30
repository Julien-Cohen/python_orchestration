A datatype to specify MOSAICO workflows.


# Generate the YAML schema

## Install the "yq" command

```
    sudo snap install yq
```

## Generate the YAML schema from the JSON schema

```bash
  cd workflow_datatype
  python export_json_schema.py
  yq -p json -oy -P workflow_schema.json > workflow_schema.yaml
``` 


# Test read a YAML file

## Emfatic example

```bash  
  cd workflow_datatype
  python read_yaml_workflow.py ../tests/emfatic/emfatic_workflow.yaml 
```

## Requirement generation example

```bash  
  cd workflow_datatype
  python read_yaml_workflow.py ../tests/requirement_generation/req_gen_workflow.yaml 
```

## Requirement patch example

```bash  
  cd workflow_datatype
  python read_yaml_workflow.py ../tests/requirement_patch/req_patch_workflow.yaml 
```