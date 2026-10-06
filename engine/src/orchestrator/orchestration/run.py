import asyncio

from orchestrator.orchestration.a2a_client import connect_and_send
from orchestrator.orchestration.agent_repository import AgentRepository
from orchestrator.workflow_datatype.agent_task import GenerationConfig
from orchestrator.workflow_datatype.algorithmic_task import AlgorithmicTaskConfig
from orchestrator.orchestration.state import Store
from orchestrator.workflow_datatype.join import SolutionJoin
from orchestrator.workflow_datatype.workflows import Workflow, Step, Sequence, AlgorithmicStep, GenerationStep, \
    EvaluationStep, RetryUntilValidated, AccumulateLoop, ParallelBuild, ParallelEvaluation, ReplyStep


def _resize_list(l: list, n: int):
    """
    Returns a list of n elements made from the elements of l.
    Used to generate n urls of agents when we know len(l) urls.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return []
    if l == []:
        raise ValueError("Empty list.")

    (full_repeats, remainder) = divmod(n, len(l))
    return l * full_repeats + l[:remainder]

def join_results (results:list, j:SolutionJoin):
    """Build a result from a list of results from several agents and a reconciliation strategy."""

    assert len(results)>0
    (name,v) = results[0]
    match j:
        case SolutionJoin.MULTIPLE_VALUE:
            return (name, [ r for (_,r) in results])
        case SolutionJoin.LIST :
            return (name, [ r for (_,r) in results]) # fixme : what's the difference between a bag and a list here ?
        case SolutionJoin.FIRST:
            return (name,v)
        case SolutionJoin.ARBITRATION:
            raise ValueError("FIXME : Arbitration not implemented yet.") # fixme


class Runner:
    """
    Object that contains all the info to orchestrate a workflow.
    """

    def __init__(self, push_artifact_callback):
        self.repo = AgentRepository()
        self.push_artifact = push_artifact_callback

    async def run_algorithmic_task(self, task : AlgorithmicTaskConfig, store:Store):
        print(task.statement.log)

    async def run_generation_task(self, task: GenerationConfig, store:Store):
        config = task.config
        agents = self.repo.request(config)
        consolidated_agents = _resize_list(agents, config.nbSpawns)
        message_content = []
        message_content.append (config.skill)
        for i in task.inputChannels:
            message_content.append(store.store[i])


        accu = [] # result accumulator

        results = await asyncio.gather(
            *(connect_and_send(url, message_content, accu) for url in consolidated_agents),
            return_exceptions=True,
        )

        for (url, r) in zip(consolidated_agents, results):
            if isinstance(r, BaseException):
                print("Agent failed or canceled:", url, r)

        if len(accu) > 0 :
            (artifact_name,v) = join_results(accu, task.solutionJoin)
            if artifact_name == "solution" :
                store.write( task.outputChannels[0], v) # FIXME: how to choose between multiple output channels?
            else:
                print("FIXME: unrecognized write channel.")
        else:
            raise RuntimeError("No output produced for this generation task")


    async def run_evaluation_task(self, task, store:Store):
        pass # FIXME


    async def run_retry_loop(self, body, store:Store):
        pass # FIXME


    async def run_accumulate_loop(self, body, store:Store):
        pass # FIXME


    async def run_reply_to_client(self, c:list[str], store:Store):
        """Send to the client the content of the specified channels."""
        for n in c:
            v = store.store[n]
            if v is not None:
                await self.push_artifact(v)


    async def run_step(self, s: Step, store:Store):
        match s:
            case Sequence():
                await self.run_step(s.step1, store)
                await self.run_step(s.step2, store) # step 2 runs after step1 is finished
            case AlgorithmicStep():
                await self.run_algorithmic_task(s.task, store)
            case GenerationStep():
                await self.run_generation_task(s.task, store)
            case EvaluationStep():
                await self.run_evaluation_task(s.task, store)
            case RetryUntilValidated():
                await self.run_retry_loop(s.body, store)
            case AccumulateLoop():
                await self.run_accumulate_loop(s.body, store)
            case ParallelBuild():
                await self.run_in_parallel(s, store)
            case ParallelEvaluation():
                await self.run_in_parallel(s, store)
            case ReplyStep():
                await self.run_reply_to_client(s.outputChannels, store)
            case _:
                raise TypeError(f"Unsupported step type: {type(s).__name__}")

    async def run_in_parallel(self, s: ParallelBuild | ParallelEvaluation, store: Store):
        results = await asyncio.gather(*(self.run_step(b, store) for b in s.branches), return_exceptions=True)
        for r in results:
            if isinstance(r, BaseException):
                print("[WARNING] Branch failure:", repr(r))

    async def run_workflow(self, workflow: Workflow, inputs:list[str]):
        store = Store(workflow.inputChannels, workflow.internalChannels + workflow.outputChannels, inputs)

        await self.run_step(workflow.body, store)
        return store

