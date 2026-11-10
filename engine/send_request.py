#!/usr/bin/env python

# SPDX-FileCopyright: 2026 University of York
# SPDX-License: MIT

import asyncio
import httpx
import uuid

from a2a.client import ClientConfig, create_client, A2ACardResolver
from a2a.helpers import new_text_message
from a2a.types import AgentCard, Role, SendMessageRequest

from mosaico.base.observability import OBSERVABILITY_KEY_ROOT_TASK_NAME

DEFAULT_BASE_URL = "http://localhost:9001"


def generate_lf_uuid():
    return str(uuid.uuid4()).replace("-", "")


def generate_lf_half_uuid():
    return generate_lf_uuid()[:16]


async def get_agent_card(url) -> AgentCard:
    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=url
        )
        return await resolver.get_agent_card()


async def send_message(url: str, text: str, context_id: str):
    card = await get_agent_card(url)

    async with httpx.AsyncClient(timeout=60) as httpx_client:
        config = ClientConfig(streaming=True, httpx_client=httpx_client)
        client = await create_client(agent=card, client_config=config)
        message = new_text_message(
            text,
            role=Role.ROLE_USER,
            context_id=context_id
        )

        # Example for sending some of the observability metadata (we don't have a
        # specific root ID or super-task ID to go for, but we can at least specify
        # the root task name)
        message.metadata[OBSERVABILITY_KEY_ROOT_TASK_NAME] = "send-request-py"

        request = SendMessageRequest(message=message)
        async for chunk in client.send_message(request):
            print(chunk)

        await client.close()


def main(base_url: str):
    context_id = str(uuid.uuid4())
    print("\nStarting interactive session with [{}]".format(base_url))
    print("Using [{}] as context ID.".format(context_id))
    print("\nEnter 'exit' to quit.")
    prompt = input("user> ")
    while prompt and prompt != 'exit':
        asyncio.run(send_message(url=base_url, text=prompt, context_id=context_id))
        prompt = input("user> ")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Sends prompts to the arithmetic-agent for testing"
    )
    parser.add_argument("-B", "--base-url",
        default=DEFAULT_BASE_URL, help="Base URL for the agent")

    args = parser.parse_args()
    main(base_url=args.base_url)