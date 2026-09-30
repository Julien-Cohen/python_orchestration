from pydantic import BaseModel

class Statement(BaseModel):
    """Statements that act on data or on logs."""
    log:str

class AlgorithmicTaskConfig(BaseModel):
    """Specification of an algorithmic task."""

    statement : Statement
    """The statement to be executed."""

    readChannels : list[str]
    """The channels that can be read by this task."""

    writeChannels : list[str]
    """The channels that can be written by this task."""