from src.orchestrator.workflow_datatype.workflows import Workflow, ChannelDeclaration

class Store:
    """A store collects the states of channels during the orchestration of a workflow."""

    def __init__(self, workflow: Workflow, input_values):
        self.store = {}
        for c in workflow.inputChannels:
            self.init_input_channel(c, input_values)
        for c in workflow.internalChannels:
            self.init_channel(c)
        for c in workflow.outputChannels:
            self.init_channel(c)

    def init_channel (self, c:ChannelDeclaration):
        self.store[c.name] = c.init

    def init_input_channel (self, c:ChannelDeclaration, input_values):
        self.store[c.name] = c.init
