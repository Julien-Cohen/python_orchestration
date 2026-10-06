from orchestrator.workflow_datatype.channelStructure import ChannelStructure
from orchestrator.workflow_datatype.workflows import Workflow, ChannelDeclaration, InputChannelDeclaration


class Store:
    """A store collects the states of channels during the orchestration of a workflow.

    Attributes:
        channels: Maps channel names to their declarations.
        store: Maps channel names to their current values.
    """

    def __init__(self, inputChannels: list[InputChannelDeclaration], otherChannels: list[ChannelDeclaration], input_values:list[str]):

        self.channels : dict[str, (ChannelDeclaration | InputChannelDeclaration)] = {}

        for c in (inputChannels + otherChannels ):
            self.channels[c.name] = c

        self.store :dict[str, (str | list[str])] = {}

        if len(inputChannels) != len(input_values):
            raise ValueError("The number of input values in parameters should correspond to the number of input channels.")

        for i in range(len (inputChannels)):
            self.init_input_channel(inputChannels[i], input_values[i])

        for c in otherChannels:
            self.init_other_channel(c)



    def init_atom_channel(self, channel_name, atom):
        self.store[channel_name] = atom

    def init_list_channel(self, channel_name, list_value):
        if isinstance(list_value, list):
            raise ValueError("List Channels can only be initialized with a list.")
        else:
            self.store[channel_name] = list_value

    def init_bag_channel(self, channel_name, bag_value):
        if isinstance(bag_value, list):
            raise ValueError("Bag Channels can only be initialized with a list.")
        else:
            self.store[channel_name] = bag_value

    def init_channel(self, c, val):
        match c.structure:
            case ChannelStructure.Atom:
                self.init_atom_channel(c.name, val)
            case ChannelStructure.List:
                self.init_list_channel(c.name, val)
            case ChannelStructure.Bag:
                self.init_bag_channel(c.name, val)
            case _:
                raise ValueError("Unrecognized Channel Structure.")

    def init_other_channel (self, c:ChannelDeclaration):
        self.store[c.name] = c.init_with_value

    def init_input_channel (self, c:InputChannelDeclaration, input_value: str):
        self.store[c.name] = input_value # FIXME : get part named c.init_with_part in input_values

    def write (self, channel_name: str, value: str):
        if not(channel_name in self.channels):
            raise ValueError("Channel " + channel_name + " is not referenced in this store.")
        channel = self.channels[channel_name]
        match channel.structure:
            case ChannelStructure.Atom:
                self.store[channel_name] = value
            case ChannelStructure.List:
                self.store[channel_name].append(value)
            case ChannelStructure.Bag:
                self.store[channel_name].append(value)
            case _:
                raise ValueError("Unrecognized Channel Structure.")

    def __str__(self) -> str:
        return "STORE CONTENT: " + str(self.store)