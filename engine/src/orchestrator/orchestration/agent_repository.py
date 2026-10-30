import requests

from orchestrator.workflow_datatype.agent_task import AgentTaskConfig

def extract_agent_card_url(a):
    return a['agent']['a2aAgentCardUrl'].removesuffix('.well-known/agent-card.json')

class AgentRepository:

    MOSAICO_REPOSITORY = "http://mosaico-app:8080" # FIXME : get the URL from REPOSITORY_API environment variable.
    URL = f"{MOSAICO_REPOSITORY}/api/agents/search"


    def request(self, text : str, nb: int, role:str):
        payload = {
            "query": text,
            "role" : role,
            "filters": {},
            "topK": nb,
            "llms": []
        }

        print("[REPO][REQUEST]", str(payload))
        response = requests.post(self.URL, json=payload, timeout=60)

        print("[REPO][RESPONSE CODE]", response.status_code)
        json_object = response.json()
        for a in json_object:
            print("[REPO][PROPOSED AGENT]", a)

        return [ extract_agent_card_url(a) for a in json_object] # Example: 'http://10.144.36.189:12000/.well-known/agent-card.json'


    def requestSolutionAgent(self, param: AgentTaskConfig)-> list[str]:
        print("[REPO] REQUEST SOLUTION AGENT")
        if param.override_repo:
            return [param.override_repo]
        else:
            return self.request(param.skill, param.nbDifferentAgents, "solution agent")
            # return [("http://127.0.0.1:9000") for i in range(param.nbDifferentAgents)]

    def requestEvaluationAgent(self, param: AgentTaskConfig)-> list[str]:
        print("[REPO] REQUEST EVALUATION AGENT")
        if param.override_repo:
            return [param.override_repo]
        else:
            return self.request(param.skill, param.nbDifferentAgents, "evaluation agent")
            # return [("http://127.0.0.1:9000") for i in range(param.nbDifferentAgents)]
