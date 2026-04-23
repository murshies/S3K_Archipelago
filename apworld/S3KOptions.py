from dataclasses import dataclass

from Options import (
    Choice,
    DeathLink,
    OptionGroup,
    PerGameCommonOptions,
    Range,
    Toggle
)


class Goal(Choice):
    """
    Base class for all of the goal options.
    """
    option_none = 0
    option_doomsday = 1
    option_knuckles_sky_sanctuary = 2
    option_death_egg = 3


class BigRingsGoal(Goal):
    """
    Class for option that determines which level that the big rings goal
    unlocks.
    """
    display_name = 'Big Rings Goal'
    default = Goal.option_none


class ChaosEmeraldsGoal(Goal):
    """
    Class for option that determines which level that collecting the chaos
    emeralds unlocks.
    """
    display_name = 'Chaos Emeralds Goal'
    default = Goal.option_none


class SuperEmeraldsGoal(Goal):
    """
    Class for option that determines which level that collecting the super
    emeralds unlocks.
    """
    display_name = 'Super Emeralds Goal'
    default = Goal.option_none


class BigRingsToCheck(Range):
    """
    Class for option that determines how many big rings need to be checked for
    the "big rings" goal.
    """
    display_name = '# of big rings to check for "big rings" goal'
    range_start = 1
    range_end = 77  # The total number of big rings in the game


class LogicDifficulty(Choice):
    """
    The difficulty setting that determines what is expected of the player to
    get all items in logic.

    There are two options:
    1. standard: Casual playthrough of the game, no tricky movement or
       backtracking into areas unintended for a character
    2. hard: Some tricky movement or backtracking may be required. If a
       location can be checked without a character going out of bounds, it will
       be included in logic.
    """
    display_name = 'Logic Difficulty'
    option_standard = 0
    option_hard = 1
    default = 0


class ZoneUnlocks(Choice):
    """
    This option determines how zones are unlocked. There are three choices:

    1. all_unlocked: All zones and characters are available at the start of the
       game
    2. zones_and_characters: Items will be added to the item pool for
       per-character, per-zone unlocks. For example, with this option selected,
       "Sonic Angel Island Zone" can be found as a pickup. Note that
       Sonic-specific items will unlock the zone for both the Sonic-only save
       file and the Sonic & Tails save file.
    3. zones_only: Zones are unlocked for all characters with a single
       pickup. For example, the item "Angel Island Zone" will be added to the
       item pool, and once it is found, all character will be able to visit
       Angel Island Zone.
    4. characters_only: All zones are unlocked for a character with a single
       pickup. For example, a "Tails" item will be added to the item pool,
       which will allow the player to play as Tails in any zone once found.

    Depending on the option selected, the randomizer will pick one of the
    pickups and automatically give it to the player. This will determine the
    player's starting character(s)/zone(s).
    """
    display_name = 'Zone Unlocks'
    option_all_unlocked = 0
    option_zones_and_characters = 1
    option_zones_only = 2
    option_characters_only = 3
    default = 0


class BossLocations(Toggle):
    """
    Determines whether or not defeating bosses, including minibosses, grants an
    item.
    """
    display_name = 'Bosses'


class BigRingLocations(Toggle):
    """
    Determines whether or not collecting/entering a big ring grants an item.
    """
    display_name = 'Big Rings'


class SpecialStageEmeraldLocations(Toggle):
    """
    Determines whether or not collecting a chaos/super emerald in a special
    stage grants an item.
    """
    display_name = 'Chaos/Super Emeralds'


class SpecialStagePerfectLocations(Toggle):
    """
    Determines whether or not getting a "perfect" in each special stage grants
    an item.
    """
    display_name = 'Special Stage Perfects'


class LightningShieldLocations(Toggle):
    """
    Determines whether or not each lightning shield monitor grants an item.
    """
    display_name = 'Lightning Shields'


class FlameShieldLocations(Toggle):
    """
    Determines whether or not each flame shield monitor grants an item.
    """
    display_name = 'Flame Shields'


class WaterShieldLocations(Toggle):
    """
    Determines whether or not each water shield monitor grants an item.
    """
    display_name = 'Water Shields'


class PowerSneakerLocations(Toggle):
    """
    Determines whether or not each power sneaker monitor grants an item.
    """
    display_name = 'Power Sneakers'


class OneUpLocations(Toggle):
    """
    Determines whether or not each 1 up/extra life monitor grants an item.
    """
    display_name = '1 Ups'


class SuperRingLocations(Toggle):
    """
    Determines whether or not each super ring (10 ring) monitor grants an item.
    """
    display_name = 'Super Rings'


class RobotnikLocations(Toggle):
    """
    Determines whether or not each robotnik monitor grants an item.
    """
    display_name = 'Robotnik Item Boxes'


s3k_option_groups = [
    OptionGroup('Goal Options', [
        BigRingsGoal,
        BigRingsToCheck,
        ChaosEmeraldsGoal,
        SuperEmeraldsGoal,
    ]),
    OptionGroup('Difficulty Options', [
        DeathLink,
        LogicDifficulty,
        ZoneUnlocks,
    ]),
    OptionGroup('Location Options', [
        BossLocations,
        BigRingLocations,
        SpecialStageEmeraldLocations,
        SpecialStagePerfectLocations,
        LightningShieldLocations,
        FlameShieldLocations,
        WaterShieldLocations,
        PowerSneakerLocations,
        OneUpLocations,
        SuperRingLocations,
        RobotnikLocations,
    ])
]


@dataclass
class S3KOptions(PerGameCommonOptions):
    big_rings_goal: BigRingsGoal
    big_rings_to_check: BigRingsToCheck
    chaos_emeralds_goal: ChaosEmeraldsGoal
    super_emeralds_goal: SuperEmeraldsGoal

    death_link: DeathLink
    logic_difficulty: LogicDifficulty
    zone_unlocks: ZoneUnlocks

    enable_bosses: BossLocations
    enable_big_rings: BigRingLocations
    enable_special_stage_emeralds: SpecialStageEmeraldLocations
    enable_special_stage_perfects: SpecialStagePerfectLocations
    enable_lightning_shields: LightningShieldLocations
    enable_flame_shields: FlameShieldLocations
    enable_water_shields: WaterShieldLocations
    enable_power_sneakers: PowerSneakerLocations
    enable_1_ups: OneUpLocations
    enable_super_rings: SuperRingLocations
    enable_robotnik_item_boxes: RobotnikLocations
