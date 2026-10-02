# SPDX-FileCopyright: 2026 University of York
# SPDX-License: MIT

from pathlib import Path

from a2a.types import AgentCard
from mosaico.base.config import MosaicoConfig
import mosaico.base.card as base_card

CARD_JSON = Path(__file__).with_name(base_card.AGENT_CARD_FILENAME)


def create_card(config: MosaicoConfig) -> AgentCard:
    return base_card.load_card(CARD_JSON, config)
