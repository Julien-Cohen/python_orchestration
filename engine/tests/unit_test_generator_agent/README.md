# A2A Mock Generator Agent


### Build a docker image 

```bash
docker build . -t unit-test-generator:latest
```

### Run the agent (not in a Docker container)

```
python ./tests/unit_test_generator_agent/generator_agent_9000.py --host=127.0.0.1 --port 9000
```

