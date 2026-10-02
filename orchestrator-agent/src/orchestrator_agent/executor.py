# Sample agent that evaluates an arithmetic expression
#
# Based on answer from:
# https://stackoverflow.com/questions/2371436/
#
# SPDX-FileCopyright: 2026 University of York
# SPDX-License: MIT

from typing import Optional
from typing import override

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from mosaico.base.executor import MosaicoAgentExecutor, HEALTH_OK
from mosaico.base.observability import MosaicoObservabilityMetadata


import logging
logger = logging.getLogger(__name__)

def orchestrate(prompt:str):
    return 0

class OrchestrationExecutor(MosaicoAgentExecutor):
    @override
    async def execute_agent(
            self,
            context: RequestContext,
            event_queue: EventQueue,
            observability_metadata: Optional[MosaicoObservabilityMetadata]) -> None:

        if len(context.message.parts) != 1:
            await self.send_text_message(context, event_queue, 'Message did not have exactly one part')
        elif not context.message.parts[0].HasField('text'):
            await self.send_text_message(context, event_queue, 'Agent expected a TextPart')
        else:
            try:
                result = orchestrate(context.message.parts[0].text)
                await self.send_text_message(context, event_queue, str(result))
            except (ValueError, TypeError, SyntaxError) as _:
                logger.exception("failed to evaluate expression")
                await self.send_text_message(context, event_queue, 'Failed to evaluate expression')

    @override
    async def health(self) -> str:
        return HEALTH_OK
