# Orchestrator Agent

# Requirements

Install `uv`, then:

```bash
uv sync
```

# Run the agent


```shell
uv sync
PORT=9001 uv run orchestrator-agent "default_workflows/example_generation_workflow.yaml"
```

# Test the agent by sending a message to it

Remember to have your other agents online before sending a request to the orchestrator agent.

## Testing the agent with a curl command

With `curl` installed:

```bash
./send_request.sh "generate something"
```

Use the Python code instead (see below) to have an interactive loop.

## Testing the agent with a Python script

Change `DEFAULT_BASE_URL = "http://localhost:9001"` in the Python file if needed. 

```bash
uv run send_request.py
```

```bash
uv run send_request.py --base-url="http://localhost:9000"
```

You will be then placed in a prompting loop: type the message and press Enter.
You can exit the loop by entering  `exit`.


# Build the Docker image

Run this command from the `orchestrator-agent` directory. The parent directory
is used as the build context so Docker can access both this project and the
sibling `engine` project:

```bash
  docker build -f src/orchestrator_agent/docker/Dockerfile -t test-orchestrator-agent:latest ..
```

## Run the agent image in a container

```bash 
  docker run --network host test-orchestrator-agent
```
