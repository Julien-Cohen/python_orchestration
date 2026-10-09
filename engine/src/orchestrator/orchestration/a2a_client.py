import json
import uuid

from typing import Any

import grpc
import httpx

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_artifact_text, get_message_text
from a2a.helpers.agent_card import display_agent_card
from a2a.types import Message, Part, Role, SendMessageRequest, TaskState
from google.protobuf.json_format import MessageToDict


async def _handle_stream(
    stream: Any,
    current_task_id: str | None,
    accu
) -> str | None:
    seen = set()  # artifact_ids already collected, to avoid duplicates

    def collect(artifact):
        if artifact.artifact_id in seen:
            return
        seen.add(artifact.artifact_id)

        name = artifact.name
        chunks = []

        for part in artifact.parts:
            kind = part.WhichOneof('content')
            if kind == 'text':
                chunks.append(part.text)
            elif kind == 'data':
                data = MessageToDict(part.data)  # Python dict / list / scalar
                chunks.append(json.dumps(data, indent=2))
            elif kind == 'raw':
                chunks.append(part.raw.decode('utf-8', errors='replace'))
            elif kind == 'url':
                chunks.append(part.url)

        content = '\n'.join(chunks)
        accu.append((name, content))
        print(f'Artifact [name={name}]:', content)

    async for event in stream:

        #print("Event received. " + repr(event))

        if event.HasField('message'):
            print('Message:', get_message_text(event.message, delimiter=' '))
            return None

        if event.HasField('task'):
            current_task_id = event.task.id
            print('--- Task Started ---')
            print(f'Task [state={TaskState.Name(event.task.status.state)}]')
            for artifact in event.task.artifacts:  # artifacts already on the task
                collect(artifact)


        elif event.HasField('status_update'):
            state_name = TaskState.Name(event.status_update.status.state)
            message_text = (
                ': '
                + get_message_text(
                    event.status_update.status.message, delimiter=' '
                )
                if event.status_update.status.HasField('message')
                else ''
            )
            print(f'TaskStatusUpdate [state={state_name}]{message_text}')
            if state_name in (
                'TASK_STATE_COMPLETED',
                'TASK_STATE_FAILED',
                'TASK_STATE_CANCELED',
                'TASK_STATE_REJECTED',
            ):
                current_task_id = None
                print('--- Task Finished ---')

        elif event.HasField('artifact_update'):
            collect(event.artifact_update.artifact)

        else:
            print('Unhandled event:', repr(event))

    return current_task_id


async def connect_and_send(target_url, parameters:list[str], accu) -> None:
    """Run an A2A client."""

    config = ClientConfig( grpc_channel_factory=grpc.aio.insecure_channel )

    print( f'Connecting to {target_url}.' )

    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(httpx_client, target_url)
        card = await resolver.get_agent_card()
        print('\n✓ Agent Card Found.')
        #display_agent_card(card)

    client = await create_client(card, client_config=config)

    actual_transport = getattr(client, '_transport', client)
    print(f'  Picked Transport: {actual_transport.__class__.__name__}')

    print('\nConnected! Going to send a message.')

    current_task_id = None
    current_context_id = str(uuid.uuid4())

    parts = [Part(text=p) for p in parameters] # FIXME :does not work with emfatic syntax checker
    #parts = [Part(text="\n ".join(parameters))] # Only one part for emfatic syntactic supervisor (does not work either)

    message = Message(
        role=Role.ROLE_USER,
        message_id=str(uuid.uuid4()),
        parts=parts,
        task_id=current_task_id,
        context_id=current_context_id,
    )

    request = SendMessageRequest(message=message)

    try:
        stream = client.send_message(request)
        current_task_id = await _handle_stream(stream, current_task_id, accu)
    except (httpx.RequestError, grpc.RpcError) as e:
        print(f'Error communicating with agent: {e}')
    finally:
        await client.close()

