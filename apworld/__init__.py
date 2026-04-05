from worlds.AutoWorld import WebWorld, World

from .Options import S3KOptions
import consts


class S3KWebWorld(WebWorld):
    pass


class S3KWorld(World):
    """
    Sonic 3 & Knuckles is the third mainline game for the Sega Genesis. Play as
    Sonic, Tails, and Knuckles to thwart Dr. Robotnik's plans to steal the
    Master Emerald and relaunch the Death Egg.
    """
    game: str = consts.GAME
    options_dataclass: S3KOptions
    options: S3KOptions
    topology_present: bool = True
    web: WebWorld = S3KWebWorld()
