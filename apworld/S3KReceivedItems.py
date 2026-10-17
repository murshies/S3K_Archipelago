# This file translates the items received from the Archipelago server into
# what the game needs:
# - Level unlock bitmasks, one per character, which determine which levels can
#   be selected on the save select screen
# - The number of emeralds, which is written to every save file
# - The list of junk items (shields, traps, etc.), which are given to the
#   player one at a time through the item mailbox (see S3KMemory.item_mailbox)

from dataclasses import dataclass
import typing

from . import consts
from .S3KMemory import (
    ITEM_TYPE_FLAME_SHIELD,
    ITEM_TYPE_INVINCIBILITY,
    ITEM_TYPE_LIGHTNING_SHIELD,
    ITEM_TYPE_POISON_TRAP,
    ITEM_TYPE_POWER_SNEAKERS,
    ITEM_TYPE_ROBOTNIK_TRAP,
    ITEM_TYPE_SUPER_RING,
    ITEM_TYPE_WATER_SHIELD,
)

CHARACTERS: tuple[str, ...] = (
    consts.CHARACTER_SONIC,
    consts.CHARACTER_TAILS,
    consts.CHARACTER_KNUCKLES,
)

SPECIAL_STAGES: tuple[str, ...] = tuple(f'Special Stage {n}' for n in range(1, 15))

# The bit in a character's level unlock bitmask for each zone. Bits 0-13 follow
# the save select screen's level list (LevelList_DA6E in the disassembly), and
# bits 14-27 are the special stages.
LEVEL_BITS: dict[str, int] = {
    consts.ZONE_ANGEL_ISLAND: 0,
    consts.ZONE_HYDROCITY: 1,
    consts.ZONE_MARBLE_GARDEN: 2,
    consts.ZONE_CARNIVAL_NIGHT: 3,
    consts.ZONE_ICE_CAP: 4,
    consts.ZONE_LAUNCH_BASE: 5,
    consts.ZONE_MUSHROOM_HILL: 6,
    consts.ZONE_FLYING_BATTERY: 7,
    consts.ZONE_SANDOPOLIS: 8,
    consts.ZONE_LAVA_REEF: 9,
    consts.ZONE_HIDDEN_PALACE: 10,
    # Both versions of Sky Sanctuary share a bit. The game picks Knuckles'
    # version when playing as Knuckles.
    consts.ZONE_SKY_SANCTUARY: 11,
    consts.ZONE_KNUCKLES_SKY_SANCTUARY: 11,
    consts.ZONE_DEATH_EGG: 12,
    consts.ZONE_DOOMSDAY: 13,
    **{stage: 14 + idx for idx, stage in enumerate(SPECIAL_STAGES)},
}

_SHARED_ZONES: tuple[str, ...] = (
    consts.ZONE_ANGEL_ISLAND,
    consts.ZONE_HYDROCITY,
    consts.ZONE_MARBLE_GARDEN,
    consts.ZONE_CARNIVAL_NIGHT,
    consts.ZONE_ICE_CAP,
    consts.ZONE_LAUNCH_BASE,
    consts.ZONE_MUSHROOM_HILL,
    consts.ZONE_FLYING_BATTERY,
    consts.ZONE_SANDOPOLIS,
    consts.ZONE_LAVA_REEF,
    consts.ZONE_HIDDEN_PALACE,
)

# The zones each character can play
CHARACTER_ZONES: dict[str, frozenset[str]] = {
    consts.CHARACTER_SONIC: frozenset((
        *_SHARED_ZONES,
        consts.ZONE_SKY_SANCTUARY,
        consts.ZONE_DEATH_EGG,
        consts.ZONE_DOOMSDAY,
        *SPECIAL_STAGES,
    )),
    consts.CHARACTER_TAILS: frozenset((
        *_SHARED_ZONES,
        consts.ZONE_SKY_SANCTUARY,
        consts.ZONE_DEATH_EGG,
        *SPECIAL_STAGES,
    )),
    consts.CHARACTER_KNUCKLES: frozenset((
        *_SHARED_ZONES,
        consts.ZONE_KNUCKLES_SKY_SANCTUARY,
        *SPECIAL_STAGES,
    )),
}

GOAL_ZONES: dict[int, str] = {
    consts.GOAL_DEATH_EGG: consts.ZONE_DEATH_EGG,
    consts.GOAL_DOOMSDAY: consts.ZONE_DOOMSDAY,
    consts.GOAL_KNUCKLES_SKY_SANCTUARY: consts.ZONE_KNUCKLES_SKY_SANCTUARY,
}

# Items given to the player through the item mailbox, and their item types
JUNK_ITEM_TYPES: dict[str, int] = {
    'Super Ring': ITEM_TYPE_SUPER_RING,
    'Lightning Shield': ITEM_TYPE_LIGHTNING_SHIELD,
    'Flame Shield': ITEM_TYPE_FLAME_SHIELD,
    'Water Shield': ITEM_TYPE_WATER_SHIELD,
    'Invincibility': ITEM_TYPE_INVINCIBILITY,
    'Power Sneakers': ITEM_TYPE_POWER_SNEAKERS,
    'Robotnik Trap': ITEM_TYPE_ROBOTNIK_TRAP,
    'Poison Trap': ITEM_TYPE_POISON_TRAP,
}

BIG_RING_LOCATION_MARKER: str = ' - Big Ring '

# The items placed at the goal locations. With one goal there's a single Master
# Emerald, otherwise there's one Master Emerald Shard per goal.
GOAL_ITEMS: tuple[str, ...] = ('Master Emerald', 'Master Emerald Shard')


@dataclass(frozen=True)
class SlotSettings:
    """The player options the client needs, sent by the world in slot data."""
    zone_unlocks: int
    big_rings_goal: int
    chaos_emeralds_goal: int
    super_emeralds_goal: int
    big_rings_to_check: int

    @staticmethod
    def from_slot_data(slot_data: dict[str, typing.Any]) -> 'SlotSettings':
        return SlotSettings(
            zone_unlocks=slot_data['zone_unlocks'],
            big_rings_goal=slot_data['big_rings_goal'],
            chaos_emeralds_goal=slot_data['chaos_emeralds_goal'],
            super_emeralds_goal=slot_data['super_emeralds_goal'],
            big_rings_to_check=slot_data['big_rings_to_check'],
        )

    @property
    def goal_zones(self) -> set[str]:
        """The zones which are only unlocked by meeting a goal condition."""
        return {
            GOAL_ZONES[goal]
            for goal in (self.big_rings_goal, self.chaos_emeralds_goal, self.super_emeralds_goal)
            if goal != consts.GOAL_NONE
        }

    @property
    def num_goals(self) -> int:
        return len([
            goal for goal in (self.big_rings_goal, self.chaos_emeralds_goal, self.super_emeralds_goal)
            if goal != consts.GOAL_NONE
        ])


def emerald_count(item_names: typing.Iterable[str]) -> int:
    count = sum(1 for name in item_names if name == consts.ITEM_CHAOS_EMERALD)
    return min(count, consts.EMERALDS_FOR_SUPER_HUNT)


def goal_complete(item_names: typing.Iterable[str], settings: SlotSettings) -> bool:
    """
    Whether every goal has been completed. This mirrors the completion condition
    set in S3KItems.create_items: each goal location holds a goal item, and the
    game is complete once all of them have been received.
    """
    goal_items = sum(1 for name in item_names if name in GOAL_ITEMS)
    return goal_items >= settings.num_goals


def big_rings_checked(checked_location_names: typing.Iterable[str]) -> int:
    return sum(1 for name in checked_location_names if BIG_RING_LOCATION_MARKER in name)


def unlocked_goal_zones(settings: SlotSettings, emeralds: int, big_rings: int) -> set[str]:
    """
    The goal zones whose conditions have been met. These mirror the region
    rules in S3KRegions.create_regions.
    """
    unlocked = set()
    if settings.big_rings_goal != consts.GOAL_NONE and big_rings >= settings.big_rings_to_check:
        unlocked.add(GOAL_ZONES[settings.big_rings_goal])
    if (settings.chaos_emeralds_goal != consts.GOAL_NONE and
            emeralds >= consts.EMERALDS_FOR_CHAOS_HUNT):
        unlocked.add(GOAL_ZONES[settings.chaos_emeralds_goal])
    if (settings.super_emeralds_goal != consts.GOAL_NONE and
            emeralds >= consts.EMERALDS_FOR_SUPER_HUNT):
        unlocked.add(GOAL_ZONES[settings.super_emeralds_goal])
    return unlocked


def unlocked_zones(
        item_names: typing.Iterable[str],
        settings: SlotSettings,
        emeralds: int,
        big_rings: int,
) -> dict[str, set[str]]:
    """The zones each character can enter."""
    unlocked: dict[str, set[str]] = {char: set() for char in CHARACTERS}
    if settings.zone_unlocks == consts.ZONE_UNLOCKS_ALL_UNLOCKED:
        for char in CHARACTERS:
            unlocked[char].update(CHARACTER_ZONES[char])

    for name in item_names:
        if name in CHARACTER_ZONES:
            # Character unlock, e.g. "Sonic": every zone for that character
            unlocked[name].update(CHARACTER_ZONES[name])
        elif ' - ' in name:
            # Zone and character unlock, e.g. "Hydrocity - Sonic"
            zone, char = name.rsplit(' - ', 1)
            if char in CHARACTER_ZONES and zone in CHARACTER_ZONES[char]:
                unlocked[char].add(zone)
        elif name in LEVEL_BITS:
            # Zone unlock, e.g. "Hydrocity": the zone for every character
            for char in CHARACTERS:
                if name in CHARACTER_ZONES[char]:
                    unlocked[char].add(name)

    # Goal zones are never unlocked by items, only by meeting their goal
    # condition
    goal_zones = settings.goal_zones
    goals_met = unlocked_goal_zones(settings, emeralds, big_rings)
    for char in CHARACTERS:
        unlocked[char] -= goal_zones
        unlocked[char] |= goals_met & CHARACTER_ZONES[char]
    return unlocked


def level_bitmasks(zones: dict[str, set[str]]) -> tuple[int, ...]:
    """The level unlock bitmasks for Sonic, Tails, and Knuckles, in that order."""
    return tuple(
        sum(1 << LEVEL_BITS[zone] for zone in zones[char])
        for char in CHARACTERS
    )


def junk_items(item_names: typing.Iterable[str]) -> list[tuple[str, int]]:
    """(item name, mailbox item type) for each junk item, in the order received."""
    return [(name, JUNK_ITEM_TYPES[name]) for name in item_names if name in JUNK_ITEM_TYPES]
