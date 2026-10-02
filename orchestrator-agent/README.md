# Orchestrator Agent


```bash
  pip install -e ../engine
  pip install -e . --index-url https://gitlab.eclipse.org/api/v4/projects/12942/packages/pypi/simple --extra-index-url https://pypi.org/simple
```

## Running the agent

```shell
uv sync
uv run orchestrator-agent
```

## Testing the agent from Bash

With `curl` installed:

```bash
./send_request.sh "2 * 4 + 5"
```

## Testing the agent from Python

Please ensure that `AGENT_CARD_HOST` is set to `localhost` for this case first.

```bash
uv run send_request.py
```

You will be then placed in a prompting loop: type the message and press Enter.
You can exit the loop by entering  `exit`.