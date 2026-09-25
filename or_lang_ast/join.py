"""Datatypes to specified multiple data are reconciled and how multiple evaluations are arbitrated. """

from enum import Enum


class SolutionJoin(str, Enum):
    """Specify what to do with solutions produced in parallel for a same channel."""

    MULTIPLE_VALUE = "MultipleValue"
    """Solutions are accumulated in a multiple-valuated channel."""

    LIST = "List"
    """Solutions are accumulated in a list channel."""

    FIRST = "First"
    """First solution to be produced is selected, other ones will be discarded."""

    ARBITRATION = "Arbitration"
    """Decision is passed to a consensus agent."""


class DecisionMode(str, Enum):
    """Specify how boolean decisions must be arbitrated."""

    MAJORITY = "Majority"
    """Decide on the majority of received evaluations. If several evaluations have the same greatest number of votes, returns one of them."""

    UNANIMITY = "Unanimity"
    """Validate if all the received evaluations are validations. Otherwise invalidate."""

    DEBATE = "Debate"
    """Validate if all the received evaluations are validations. Otherwise organise a debate before deciding."""
