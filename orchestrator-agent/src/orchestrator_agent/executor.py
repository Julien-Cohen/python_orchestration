from typing import Optional
from typing import override

from a2a.helpers import new_text_part
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Task, TaskState, TaskStatus
from langfuse._client.get_client import get_client
from mosaico.base.executor import MosaicoAgentExecutor, HEALTH_OK
from mosaico.base.observability import MosaicoObservabilityMetadata


import logging

from orchestrator.orchestration.run import Runner
from orchestrator.workflow_datatype.workflows import Workflow
from orchestrator.yaml_schema import read_yaml_workflow

logger = logging.getLogger(__name__)

def orchestrate(prompt:str, workflow: Workflow):
    runner = Runner()
    result_store = runner.run_workflow(workflow, [prompt])
    return str(result_store)

class OrchestrationExecutor(MosaicoAgentExecutor):

    def __init__(self, agent_name:str, workflow_file) -> None:
        super().__init__(agent_name=agent_name) # fixme : check the parameters
        self.running_tasks: set[str] = set() # fixme : do we really need that ?
        self.workflow = read_yaml_workflow.read_file(workflow_file)

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

        async def push(text:str):
            await updater.add_artifact(
                parts=[new_text_part(text)],
                name='solution',
                last_chunk=True,
            )

        if len(context.message.parts) != 1:
            await self.send_text_message(context, event_queue, 'Message did not have exactly one part')
        elif not context.message.parts[0].HasField('text'):
            await self.send_text_message(context, event_queue, 'Agent expected a TextPart')
        else:

            prompt = context.message.parts[0].text

            get_client().update_current_span(input={"prompt": prompt})
            try:

                result = orchestrate(prompt, self.workflow)
                get_client().update_current_span(output={"solution": result}) # langfuse
                await push(result)

                await updater.complete()

            except (ValueError, TypeError, SyntaxError) as _:
                logger.exception("failed to evaluate expression")
                await self.send_text_message(context, event_queue, 'Failed to evaluate expression')

    @override
    async def health(self) -> str:
        return HEALTH_OK
