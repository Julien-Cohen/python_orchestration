from orchestrator.workflow_datatype.agent_task import AgentTaskConfig


class AgentRepository:

    def requestSolutionAgent(self, param: AgentTaskConfig):
        return [("http://127.0.0.1:9000") for i in range(param.nbDifferentAgents)]

    def requestEvaluationAgent(self, param: AgentTaskConfig):
        return [("http://127.0.0.1:9000") for i in range(param.nbDifferentAgents)]
