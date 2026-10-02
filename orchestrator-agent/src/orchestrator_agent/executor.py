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

import ast
import operator as op

import logging
logger = logging.getLogger(__name__)

operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
             ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
             ast.USub: op.neg}

max_value = 10**100

def eval_expr(expr):
    """
    >>> eval_expr('2^6')
    4
    >>> eval_expr('2**6')
    64
    >>> eval_expr('1 + 2*3**(4^5) / (6 + -7)')
    -5.0
    """
    result = eval_ast(ast.parse(expr, mode='eval').body)
    if result > max_value:
        raise ValueError(f"intermediate result too high: {result}")
    return result


def eval_limited(node):
    result = eval_ast(node)
    if result > max_value:
        raise ValueError(f"intermediate result too high: {result}")
    return result


def eval_ast(node):
    match node:
        case ast.Constant(value) if isinstance(value, int):
            return value  # integer
        case ast.BinOp(left, op, right):
            return operators[type(op)](eval_limited(left), eval_limited(right))
        case ast.UnaryOp(op, operand):  # e.g., -1
            return operators[type(op)](eval_limited(operand))
        case _:
            raise TypeError(node)


class ArithmeticExecutor(MosaicoAgentExecutor):
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
                result = eval_expr(context.message.parts[0].text)
                await self.send_text_message(context, event_queue, str(result))
            except (ValueError, TypeError, SyntaxError) as _:
                logger.exception("failed to evaluate expression")
                await self.send_text_message(context, event_queue, 'Failed to evaluate expression')

    @override
    async def health(self) -> str:
        return HEALTH_OK
