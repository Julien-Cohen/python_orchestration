import asyncio
from multiprocessing import Manager, Process

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
        raise ValueError("N must be non-negative")
    if n == 0:
        return []
    if not l:
        raise ValueError("Cannot fill a result from an empty list")

    full_repeats, remainder = divmod(n, len(l))
    return l * full_repeats + l[:remainder]

def choose_from_join (results, j:SolutionJoin):
    assert len(results)>0
    (name,v) = results[0]
    match j:
        case SolutionJoin.MULTIPLE_VALUE:
            return (name, [ r for (_,r) in results])
        case SolutionJoin.LIST :
            return (name, [ r for (_,r) in results]) # fixme : what's the difference betwee a bag and a list here ?
        case SolutionJoin.FIRST:
            return (name,v)
        case SolutionJoin.ARBITRATION:
            raise ValueError("FIXME : Arbitration not implemented yet.") # fixme

def _run_connect_and_send(url, params: list[str], accu):
    asyncio.run(connect_and_send(url, params, accu))


class Runner:
    """
    Object that contains all the info to orchestrate a workflow.
    """

    def __init__(self):
        self.repo = AgentRepository()

    def run_algorithmic_task(self, task : AlgorithmicTaskConfig, store:Store):
        print(task.statement.log)

    def run_generation_task(self, task: GenerationConfig, store:Store):
        config = task.config
        agents = self.repo.request(config)
        consolidated_agents = _resize_list(agents, config.nbSpawns)
        content = []
        content.append (config.skill)
        for i in task.inputChannels:
            content.append(store.store[i])
        with Manager() as manager:
            accu = manager.list() # result accumulator
            processes = []
            for url in consolidated_agents:
                process = Process(
                    target=_run_connect_and_send,
                    args=(url, content, accu),
                )
                process.start()
                processes.append((url, process))
                print("sending request to " + url)

            for (_, process) in processes:
                process.join()

            failed_agents = [ url for (url, process) in processes if process.exitcode != 0 ]
            for a in failed_agents:
                print ("Agent process failed:", a)
            if len(accu) > 0 :
                (artifact_name,v) = choose_from_join(accu, task.solutionJoin)
                if artifact_name == "solution" :
                    store.write( task.outputChannels[0], v) # FIXME: how to choose between multiple output channels?
                else:
                    print("FIXME: unrecognized write channel.")



    def run_evaluation_task(self, task, store:Store):
        pass # FIXME


    def run_retry_loop(self, body, store:Store):
        pass # FIXME


    def run_accumulate_loop(self, body, store:Store):
        pass # FIXME


    def run_reply_to_client(self, c:list[str],store:Store):
        """Send to the client the content of the specified channels."""
        pass # FIXME


    def run_step(self, s: Step, store:Store):
        match s:
            case Sequence():
                self.run_step(s.step1, store)
                self.run_step(s.step2, store)
            case AlgorithmicStep():
                self.run_algorithmic_task(s.task, store)
            case GenerationStep():
                self.run_generation_task(s.task, store)
            case EvaluationStep():
                self.run_evaluation_task(s.task, store)
            case RetryUntilValidated():
                self.run_retry_loop(s.body, store)
            case AccumulateLoop():
                self.run_accumulate_loop(s.body, store)
            case ParallelBuild():
                for branch in s.branches: # fixme : parallel
                    self.run_step(branch, store)
            case ParallelEvaluation():
                for branch in s.branches: # fixme : parallel
                    self.run_step(branch, store)
            case ReplyStep():
                self.run_reply_to_client(s.outputChannels, store)
            case _:
                raise TypeError(f"Unsupported step type: {type(s).__name__}")

    def run_workflow(self, workflow: Workflow, inputs:list[str]):
        store = Store(workflow, inputs)

        self.run_step(workflow.body, store)
        return store

