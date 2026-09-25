

# Generate the JSON schema

```bash
  python export_json_schema.py 
```

# Generate the  YAML schema

## Install the "yq" command
```bash
    sudo snap install yq
```

## Generate from the JSON schema
```bash
  cd or_lang_ast
  yq -p json -oy -P workflow_schema.json > workflow_schema.yaml
``` 

# Test read a JSON file
```bash
  cd or_lang_ast
  python read_json_workflow.py ../tests/emfatic/emfatic_workflow.json
```
# Test read a YAML file
```bash  
  cd or_lang_ast
  python read_yaml_workflow.py ../tests/emfatic/emfatic_workflow.yaml 
```