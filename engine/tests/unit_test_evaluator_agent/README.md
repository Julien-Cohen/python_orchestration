# A2A Mock Evaluator Agent


### Build a docker image 

```bash
docker build . -t unit-test-evaluator:latest
```

### Run the agent (not in a Docker container)

```
python ./tests/unit_test_evaluator_agent/evaluator_agent_9000.py --host=127.0.0.1 --port=9000
```

