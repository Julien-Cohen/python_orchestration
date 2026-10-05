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

repo = AgentRepository()


def _run_connect_and_send(url, params:list[str], accu):
    asyncio.run(connect_and_send(url, params, accu))


def run_algorithmic_task(task : AlgorithmicTaskConfig, store:Store):
    print(task.statement.log)


def _resize_list(l:list, n:int):
    """Returns a list of n elements made from the elements of l. Used to generate n urls of agents when we know len(l) urls."""
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


def run_generation_task(task: GenerationConfig, store:Store):
    config = task.config
    agents = repo.request(config)
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



def run_evaluation_task(task, store:Store):
    pass # FIXME


def run_retry_loop(body, store:Store):
    pass # FIXME


def run_accumulate_loop(body, store:Store):
    pass # FIXME


def run_reply_to_client(store:Store):
    pass # FIXME


def run_step(s: Step, store:Store):
    match s:
        case Sequence():
            run_step(s.step1, store)
            run_step(s.step2, store)
        case AlgorithmicStep():
            run_algorithmic_task(s.task, store)
        case GenerationStep():
            run_generation_task(s.task, store)
        case EvaluationStep():
            run_evaluation_task(s.task, store)
        case RetryUntilValidated():
            run_retry_loop(s.body, store)
        case AccumulateLoop():
            run_accumulate_loop(s.body, store)
        case ParallelBuild():
            for branch in s.branches: # fixme : parallel
                run_step(branch, store)
        case ParallelEvaluation():
            for branch in s.branches: # fixme : parallel
                run_step(branch, store)
        case ReplyStep():
            run_reply_to_client(store)
        case _:
            raise TypeError(f"Unsupported step type: {type(s).__name__}")

def run_workflow(workflow: Workflow, inputs:list[str]):
    store = Store(workflow, inputs)

    run_step(workflow.body, store)
    return store

