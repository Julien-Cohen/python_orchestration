import logging
import sys

from dotenv import load_dotenv

from mosaico.base.config import MosaicoConfig
from mosaico.base.langfuse import initialize_langfuse
from mosaico.base.main import MosaicoAgentMain
from .card import create_card
from .executor import OrchestrationExecutor


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <path_to_yaml_file>")
        sys.exit(1)
    else:
        filename = sys.argv[1]

        logging.basicConfig(level=logging.INFO)
        load_dotenv()
        config = MosaicoConfig.from_env()
        initialize_langfuse(blocked_scopes=["a2a-python-sdk"])

        main = MosaicoAgentMain(
            agent_card=create_card(config),
            agent_executor=OrchestrationExecutor(agent_name="orchestrator-agent", workflow_file=filename)
        )
        main.run(config)


if __name__ == "__main__":
    main()
