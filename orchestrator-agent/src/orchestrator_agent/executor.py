# Sample agent that evaluates an arithmetic expression
#
# Based on answer from:
# https://stackoverflow.com/questions/2371436/
#
# SPDX-FileCopyright: 2026 University of York
# SPDX-License: MIT
from typing import Optional
from typing import override

from a2a.helpers import new_text_part
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Task, TaskState, TaskStatus
from mosaico.base.executor import MosaicoAgentExecutor, HEALTH_OK
from mosaico.base.observability import MosaicoObservabilityMetadata


import logging
logger = logging.getLogger(__name__)

def orchestrate(prompt:str):
    return str(0) # fixme

class OrchestrationExecutor(MosaicoAgentExecutor):

    def __init__(self, agent_name:str) -> None:
        super().__init__(agent_name=agent_name) # fixme : check the parameters
        self.running_tasks: set[str] = set() # fixme : do we really need that ?

    @override
    async def execute_agent(
            self,
            context: RequestContext,
            event_queue: EventQueue,
            observability_metadata: Optional[MosaicoObservabilityMetadata]) -> None:

        # fixme : use observability_metadata above
        user_message = context.message
        task_id = context.task_id
        context_id = context.context_id

        task = context.current_task

        if not user_message or not task_id or not context_id:
            logger.info(
                '[Mock Generator Agent] Abort',
            )
            return

        self.running_tasks.add(task_id)

        if not task:
            task = Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
                history=[user_message],
            )
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task_id,
            context_id=context_id,
        )

        if len(context.message.parts) != 1:
            await self.send_text_message(context, event_queue, 'Message did not have exactly one part')
        elif not context.message.parts[0].HasField('text'):
            await self.send_text_message(context, event_queue, 'Agent expected a TextPart')
        else:
            try:
                result = orchestrate(context.message.parts[0].text)

                await updater.add_artifact(
                    parts=[new_text_part(result)],
                    name='solution',
                    last_chunk=True,
                )

                await updater.complete()

            except (ValueError, TypeError, SyntaxError) as _:
                logger.exception("failed to evaluate expression")
                await self.send_text_message(context, event_queue, 'Failed to evaluate expression')

    @override
    async def health(self) -> str:
        return HEALTH_OK
