import math

from BaseClasses import Item, ItemClassification, MultiWorld
from worlds.AutoWorld import World

from . import consts
from . import items
from . import locations
from .S3KUtil import location_for_goal
from .S3KOptions import ZoneUnlocks


class S3KItem(Item):
    game: str = consts.GAME

    def __init__(
            self,
            name: str,
            classification: ItemClassification,
            code: int = None,
            player: int = None,
    ):
        super(S3KItem, self).__init__(name, classification, code, player)


def create_items(
        multiworld: MultiWorld,
        world: World,
        player: int,
        item_set: items.ItemSet,
        loc_set: locations.LocationSet,
):
    """
    Given a filtered list of items and the player's settings, add the player's
    items to the item pool.
    """
    # This function will place a number of items equal to the number of
    # locations enabled by the player's settings. To determine the filler item
    # count, start with the total number of locations and work backwards,
    # decreasing the count as other items are added to the pool.
    num_filler_items = len(loc_set.all_locations)

    # Place all of the items which must be in specific locations, like master
    # emerald shards. NOTE: `filter_items` guarantees that there will be
    # exactly one goal item in the item set.
    goal_item = item_set.filter_items(
        lambda item: items.ITEM_GROUP_GOAL in item.groups
    )[0]
    if world.options.big_rings_goal.value != consts.GOAL_NONE:
        goal_loc = location_for_goal(
            loc_set, world.options.big_rings_goal.value)
        multiworld.get_location(goal_loc.display_name, player).place_locked_item(
            world.create_item(goal_item.name))
        num_filler_items -= 1
    if world.options.chaos_emeralds_goal.value != consts.GOAL_NONE:
        goal_loc = location_for_goal(
            loc_set, world.options.chaos_emeralds_goal.value)
        multiworld.get_location(goal_loc.display_name, player).place_locked_item(
            world.create_item(goal_item.name))
        num_filler_items -= 1
    if world.options.super_emeralds_goal.value != consts.GOAL_NONE:
        goal_loc = location_for_goal(
            loc_set, world.options.super_emeralds_goal.value)
        multiworld.get_location(goal_loc.display_name, player).place_locked_item(
            world.create_item(goal_item.name))
        num_filler_items -= 1

    itempool: list[S3KItem] = []

    # Add chaos emeralds to the pool
    if world.options.chaos_emeralds_goal.value != consts.GOAL_NONE:
        for i in range(0, consts.EMERALDS_FOR_CHAOS_HUNT):
            itempool.append(world.create_item(consts.ITEM_CHAOS_EMERALD))
        num_filler_items -= consts.EMERALDS_FOR_CHAOS_HUNT
    if world.options.super_emeralds_goal.value != consts.GOAL_NONE:
        for i in range(0, consts.EMERALDS_FOR_SUPER_HUNT):
            itempool.append(world.create_item(consts.ITEM_CHAOS_EMERALD))
        num_filler_items -= consts.EMERALDS_FOR_SUPER_HUNT
    if (
            world.options.chaos_emeralds_goal.value == consts.GOAL_NONE and
            world.options.super_emeralds_goal.value == consts.GOAL_NONE
    ):
        # If there are no emerald hunt goals enabled, put the chaos emeralds as
        # rewards for each special stage, to make the behavior closer to the
        # base game.
        special_stage_complete_locs = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_EMERALD
        )
        assert len(special_stage_complete_locs) == 14
        for loc in special_stage_complete_locs:
            multiworld.get_location(loc.display_name, player).place_locked_item(
                world.create_item(consts.ITEM_CHAOS_EMERALD))
            num_filler_items -= 1

    # Add the zone/character items based on the player's
    # settings. `filter_items` has already taken care of putting the correct
    # items in the item set.
    zone_items = item_set.filter_items(
        lambda item: (items.ITEM_GROUP_CHARACTER in item.groups or
                      items.ITEM_GROUP_LEVEL in item.groups)
    )
    itempool += [world.create_item(item.name) for item in zone_items]
    num_filler_items -= len(zone_items)

    # Only traps and filler items are now left. Determine how many traps should
    # be added based on `trap_weight_percentage` from the player's
    # configuration, and then randomly pick from the set of traps for each one.
    num_traps = math.floor(num_filler_items * world.options.trap_weight_percentage.value / 100.0)
    num_filler_items -= num_traps
    traps = item_set.filter_items(lambda item: item.trap)
    for _ in range(num_traps):
        itempool.append(world.create_item(world.random.choice(traps).name))

    # Finally, randomly select filler items to fill in the rest.
    filler_items = item_set.filter_items(lambda item: item.filler)
    for _ in range(num_filler_items):
        itempool.append(world.create_item(world.random.choice(filler_items).name))

    multiworld.itempool += itempool


def filter_items(world: World, item_set: items.ItemSet) -> items.ItemSet:
    """
    Given the entire set of possible items, create a filtered item set which
    only includes the items enabled by the player's settings.
    """
    item_code_set: set[int] = set()

    # Determine how many goals are enabled. This will determine which goal item
    # is added to the filtered item set.
    num_enabled_goals = 0
    if world.options.big_rings_goal.value != consts.GOAL_NONE:
        num_enabled_goals += 1
    if world.options.chaos_emeralds_goal.value != consts.GOAL_NONE:
        num_enabled_goals += 1
    if world.options.super_emeralds_goal.value != consts.GOAL_NONE:
        num_enabled_goals += 1

    # There will always be at least one goal item (master emerald/master
    # emerald shard) in the item pool.
    if num_enabled_goals == 1:
        matching = item_set.filter_items(
            lambda item: (items.ITEM_GROUP_GOAL in item.groups and
                          items.ITEM_GROUP_MULTIGOAL not in item.groups)
        )
    else:
        matching = item_set.filter_items(
            lambda item: items.ITEM_GROUP_MULTIGOAL in item.groups
        )
    assert len(matching) == 1
    item_code_set.add(matching[0].code)

    # Determine if chaos emeralds should be added to the item pool.
    if (
            world.options.chaos_emeralds_goal.value != consts.GOAL_NONE or
            world.options.super_emeralds_goal.value != consts.GOAL_NONE
    ):
        matching = item_set.filter_items(
            lambda item: 'chaos_emerald' in item.groups
        )
        item_code_set.update(item.code for item in matching)

    # Next, add the zone & character items depending on what the player
    # selected in their configuration for zone_unlocks. Note that no items are
    # added for ZONE_UNLOCKS_ALL_UNLOCKED, since all characters and zones will
    # be available to the player at the start of the game.
    if world.options.zone_unlocks.value == ZoneUnlocks.option_characters_only:
        # Sonic/Tails/Knuckles items that each unlock all zones for the given
        # character
        matching = item_set.filter_items(
            lambda item: (items.ITEM_GROUP_CHARACTER in item.groups and
                          items.ITEM_GROUP_LEVEL not in item.groups)
        )
        item_code_set.update(item.code for item in matching)
    elif world.options.zone_unlocks.value == ZoneUnlocks.option_zones_and_characters:
        # Per-character, per-zone items, for example Sonic - Angel Island Zone
        matching = item_set.filter_items(
            lambda item: (items.ITEM_GROUP_CHARACTER in item.groups and
                          items.ITEM_GROUP_LEVEL in item.groups)
        )
        item_code_set.update(item.code for item in matching)
    elif world.options.zone_unlocks.value == ZoneUnlocks.option_zones_only:
        # Zone items that unlock a single zone for all characters
        matching = item_set.filter_items(
            lambda item: (items.ITEM_GROUP_CHARACTER not in item.groups and
                          items.ITEM_GROUP_LEVEL in item.groups)
        )
        item_code_set.update(item.code for item in matching)

    # Add trap items, if enabled
    if world.options.traps_enabled:
        matching = item_set.filter_items(
            lambda item: item.trap
        )
        item_code_set.update(item.code for item in matching)

    # Filler items are always be included
    matching = item_set.filter_items(
        lambda item: item.filler
    )
    item_code_set.update(item.code for item in matching)

    return items.ItemSet([
        item
        for item in item_set.all_items
        if item.code in item_code_set
    ])
