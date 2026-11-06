Concrete Syntax for MOSAICO workflows


# Run 

## Compile to the low-level orchestration language

Emfatic:
```bash
python -m wof examples/emfatic_workflow.wof
```

Requirement patch:
```bash
python -m wof examples/requirement_patcher_workflow.wof
```

## Show intermediate steps

Show the parsed AST (WOF language):
```bash
python -m wof examples/emfatic_workflow.wof --ast
```

Show the parsed raw tree (Lark):
```bash
python -m wof examples/emfatic_workflow.wof --tree
```


Save the AST as a json file:
```bash
python -m wof examples/emfatic_workflow.wof -o out.json
```


# Tests

(FIXME)
```bash
uv sync --extra test
uv run pytest -v
```

# To use the compiler, install the engine module

(In the IDE, install the package from the GUI, it may appear as mosaico-orchestrator)
```bash
 pip install -e ../engine/
```