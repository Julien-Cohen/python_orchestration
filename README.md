A datatype to specify MOSAICO workflows.

# Generate the JSON schema

```bash
  cd or_lang_ast
  python export_json_schema.py 
```

# Generate the YAML schema

## Install the "yq" command

```
    sudo snap install yq
```

## Generate the YAML schema from the JSON schema
```bash
  cd or_lang_ast
  python export_json_schema.py
  yq -p json -oy -P workflow_schema.json > workflow_schema.yaml
``` 

# Test read a JSON file

```bash
  cd or_lang_ast
  python read_json_workflow.py ../tests/emfatic/emfatic_workflow.json
```


# Test read a YAML file

## Emfatic example

```bash  
  cd or_lang_ast
  python read_yaml_workflow.py ../tests/emfatic/emfatic_workflow.yaml 
```

## Requirement generation example

```bash  
  cd or_lang_ast
  python read_yaml_workflow.py ../tests/requirement_generation/workflow.yaml 
```

## Requirement patch example

```bash  
  cd or_lang_ast
  python read_yaml_workflow.py ../tests/requirement_patch/workflow.yaml 
```