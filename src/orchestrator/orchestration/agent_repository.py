from orchestrator.workflow_datatype.agent_task import AgentTaskConfig


class AgentRepository:

    def request(self, param: AgentTaskConfig):
        return [("agent_" + str(i)) for i in range(param.nbDifferentAgents)]
