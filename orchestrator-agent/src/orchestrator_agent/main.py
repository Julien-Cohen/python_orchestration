# SPDX-FileCopyright: 2026 University of York
# SPDX-License: MIT

from dotenv import load_dotenv

from mosaico.base.config import MosaicoConfig
from mosaico.base.langfuse import initialize_langfuse
from mosaico.base.main import MosaicoAgentMain
from .card import create_card
from .executor import ArithmeticExecutor


def main():
    load_dotenv()
    config = MosaicoConfig.from_env()
    initialize_langfuse(blocked_scopes=["a2a-python-sdk"])

    main = MosaicoAgentMain(
        agent_card=create_card(config),
        agent_executor=ArithmeticExecutor(agent_name="arithmetic-agent")
    )
    main.run(config)


if __name__ == "__main__":
    main()
