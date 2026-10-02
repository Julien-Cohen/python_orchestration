# SPDX-FileCopyright: 2026 University of York
# SPDX-License: MIT

from typing import List, override
from mosaico.base.testing import create_data_part, create_text_part, create_context, AgentExecutorTest

from a2a.types import Message, Part
from orchestrator_agent.executor import ArithmeticExecutor

class TestArithmeticExecutor(AgentExecutorTest):
    @override
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.executor = ArithmeticExecutor()

    async def test_no_parts(self):
        context = create_context([])
        obtained_text = await self.call_agent(context)
        self.assertEqual(obtained_text, 'Message did not have exactly one part')

    async def test_calc(self):
        context = create_context([
            create_text_part('1 + 1')
        ])
        obtained_text = await self.call_agent(context)
        self.assertEqual(obtained_text, '2')

    async def test_not_calc(self):
        context = create_context([
            create_text_part('foo')
        ])
        obtained_text = await self.call_agent(context)
        self.assertEqual(obtained_text, 'Failed to evaluate expression')

    async def test_bad_syntax(self):
        context = create_context([
            create_text_part('very bad syntax')
        ])
        obtained_text = await self.call_agent(context)
        self.assertEqual(obtained_text, 'Failed to evaluate expression')

    async def test_not_text(self):
        context = create_context([
            create_data_part({'foo': 'bar'})
        ])
        obtained_text = await self.call_agent(context)
        self.assertEqual(obtained_text, 'Agent expected a TextPart')

    async def call_agent(self, context):
        await self.executor.execute_agent(context, self.mock_bus, None)
        self.mock_bus.enqueue_event.assert_called()
        message: Message = self.mock_bus.enqueue_event.call_args[0][0]
        parts: List[Part] = message.parts
        self.assertEqual(len(parts), 1)
        obtained_text = parts[0].text
        return obtained_text
