from dataclasses import dataclass

from Options import Choice, PerGameCommonOptions


@dataclass
class S3KOptions(PerGameCommonOptions):
    pass


class S3KGoal(Choice):
    """
    Base class for all of the goal options.
    """
    option_none = 0
    option_doomsday = 1
    option_knuckles_sky_sanctuary = 2
    option_death_egg = 3


class S3KBigRingsGoal(S3KGoal):
    """
    Class for option that determines which level that the big rings goal
    unlocks.
    """
    display_name = 'Big Rings Goal'
    default = S3KGoal.option_none


class S3KChaosEmeraldsGoal(S3KGoal):
    """
    Class for option that determines which level that collecting the chaos
    emeralds unlocks.
    """
    display_name = 'Chaos Emeralds Goal'
    default = S3KGoal.option_none


class S3KSuperEmeraldsGoal(S3KGoal):
    """
    Class for option that determines which level that collecting the super
    emeralds unlocks.
    """
    display_name = 'Super Emeralds Goal'
    default = S3KGoal.option_none
