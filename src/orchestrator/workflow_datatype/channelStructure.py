from enum import Enum


class ChannelStructure(str, Enum):
    """Specify how data is structured in a channel."""

    Atom = "Atom"
    """A number or a string."""

    List = "List"
    """Data is accumulated in a list."""

    Bag = "Bag"
    """Multiple values are accumulated in a bag (unordered set)"""
