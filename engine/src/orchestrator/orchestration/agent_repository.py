from orchestrator.workflow_datatype.agent_task import AgentTaskConfig


class AgentRepository:

    def requestSolutionAgent(self, param: AgentTaskConfig)-> list[str]:
        if param.override_repo:
            return [param.override_repo]
        else:
            print("[FIXME] MOSAICO Repository not implemented.")
            return [("http://127.0.0.1:9000") for i in range(param.nbDifferentAgents)] # FIXME

    def requestEvaluationAgent(self, param: AgentTaskConfig)-> list[str]:
        if param.override_repo:
            return [param.override_repo]
        else:
            print("[FIXME] MOSAICO Repository not implemented.")
            return [("http://127.0.0.1:9000") for i in range(param.nbDifferentAgents)] # FIXME
