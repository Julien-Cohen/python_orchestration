Concrete Syntax for MOSAICO workflows


# Run main 

Emfatic:
```bash
python -m wof examples/emfatic_workflow.wof
```

Requirement patch:
```bash
python -m wof examples/requirement_patcher_workflow.wof
```

Show the parse raw tree:
```bash
python -m wof examples/emfatic_workflow.wof --tree
```

Save the AST as a json file:
```bash
python -m wof examples/emfatic_workflow.wof -o out.json
```


# Tests

```bash
uv sync --extra test
uv run pytest -v
```