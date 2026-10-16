
# What 
Generate a PlantUML activity diagram from an orchestration described in a .yaml file.
Produces a .puml file that can be copied into a PlantUML server to produce a visual representation.

# How 
```bash
cd src/orchestrator/visualization
python main.py ../../../tests/requirement_generation/req_gen_workflow.yaml
```

```bash
cd src/orchestrator/visualization
python main.py ../../../../orchestrator-agent/default_workflows/emfatic_workflow.yaml 
```

# Where

If you don't have a PlantUML server, you can use the following one:

https://www.plantuml.com/plantuml/uml