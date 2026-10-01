from orchestrator.orchestration.agent_repository import AgentRepository
from orchestrator.workflow_datatype.agent_task import GenerationConfig
from orchestrator.workflow_datatype.algorithmic_task import AlgorithmicTaskConfig
from orchestrator.orchestration.state import Store
from orchestrator.workflow_datatype.workflows import Workflow, Step, Sequence, AlgorithmicStep, GenerationStep, \
    EvaluationStep, RetryUntilValidated, AccumulateLoop, ParallelBuild, ParallelEvaluation, ReplyStep

repo = AgentRepository()

def run_algorithmic_task(task : AlgorithmicTaskConfig, store:Store):
    print(task.statement.log)


def run_generation_task(task: GenerationConfig, store:Store):
    config = task.config
    agents = repo.request(config)
    outChan = task.outputChannels
    for url in agents:
        print("sending request to " + url)
    for c in outChan:
        store.write(c, "done")


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

def run_workflow(workflow: Workflow, inputs):
    store = Store(workflow, inputs)

    run_step(workflow.body, store)
    return store


