import typing

from BaseClasses import CollectionState, MultiWorld, Region
from worlds.AutoWorld import World

from . import consts
from . import locations
from . import S3KLocations


def create_regions(
        multiworld: MultiWorld,
        world: World,
        player: int,
        loc_set: locations.LocationSet,
        starting_zone: typing.Optional[str],
) -> None:
    # Archipelago requires a Menu region, which in the case of Sonic 3 &
    # Knuckles will be connected to each zone/special stage.
    menu = Region('Menu', player, multiworld)
    multiworld.regions.append(menu)
    zone_char_map: dict[str, set[str]] = {}
    for loc in loc_set.all_locations:
        zone = loc.zone
        if zone not in zone_char_map:
            zone_char_map[zone] = set()
        for req in loc.requirements:
            if req.character is not None:
                zone_char_map[zone].add(req.character)
    for zone, chars in zone_char_map.items():
        region = Region(zone, player, multiworld)
        multiworld.regions.append(region)
        # Add the locations corresponding to this region to the multiworld's
        # location pool.
        zone_locs = [loc for loc in loc_set.all_locations if loc.zone == zone]
        for loc in zone_locs:
            s3k_loc = S3KLocations.S3KLocation(
                player, loc.display_name, loc.location_id, region)
            region.locations.append(s3k_loc)

        # Determine the rule for accessing the zone for the character. This
        # will depend on the zone unlock settings, as well as which goal zones
        # are enabled.

        # Handle the goal zones first
        if goal_applicable(world.options.big_rings_goal.value, zone):
            menu.connect(
                region,
                rule=lambda state: can_check_required_num_big_rings(
                    world, state, player, loc_set, world.options.big_rings_to_check.value))
        elif goal_applicable(world.options.chaos_emeralds_goal.value, zone):
            menu.connect(
                region,
                rule=lambda state: state.has(
                    consts.ITEM_CHAOS_EMERALD, player, consts.EMERALDS_FOR_CHAOS_HUNT))
        elif goal_applicable(world.options.super_emeralds_goal.value, zone):
            menu.connect(
                region,
                rule=lambda state: state.has(
                    consts.ITEM_CHAOS_EMERALD, player, consts.EMERALDS_FOR_SUPER_HUNT))
        # Make sure no access requirements are added to the starting zone, if one exists.
        elif zone == starting_zone:
            menu.connect(region)
        # Next, handle access to other zones based on zone unlock logic
        elif world.options.zone_unlocks.value == consts.ZONE_UNLOCKS_ZONES_ONLY:
            menu.connect(
                region,
                rule=lambda state: state.has(zone, player))
        elif world.options.zone_unlocks.value == consts.ZONE_UNLOCKS_ZONES_AND_CHARACTERS:
            menu.connect(
                region,
                rule=lambda state: any(state.has(f"{zone} - {char}", player)
                                       for char in chars))
        # Otherwise, there are two options:
        # 1. All zones and characters are unlocked from the start
        # 2. The player has their settings to get character unlocks, meaning a
        #    single item like "Sonic" will unlock all zones for Sonic. In order
        #    for the player to do anything at the start, they must be given one
        #    character unlock, meaning that all zones will be available to the
        #    player from the start.
        # The only exception is goal zones, but those have already been given
        # their rules above.
        else:
            menu.connect(region)


def goal_applicable(goal_value: int, zone: str) -> bool:
    """
    Given a goal value and a target zone, return a bool indicating whether or
    not the goal is for the zone.
    """
    return (
        (
            goal_value == consts.GOAL_KNUCKLES_SKY_SANCTUARY and
            zone == consts.ZONE_KNUCKLES_SKY_SANCTUARY
        ) or (
            goal_value == consts.GOAL_DEATH_EGG and
            zone == consts.ZONE_DEATH_EGG
        ) or (
            goal_value == consts.GOAL_DOOMSDAY and
            zone == consts.ZONE_DOOMSDAY
        )
    )


def can_check_required_num_big_rings(
        world: World,
        state: CollectionState,
        player: int,
        loc_set: locations.LocationSet,
        num_required: int,
) -> bool:
    """
    Helper function used in rules to determine whether or not the player can
    reach the required number of big rings for the big ring hunt goal.
    """
    if world.options.zone_unlocks.value == consts.ZONE_UNLOCKS_ALL_UNLOCKED:
        # All big rings are reachable from the start
        return True
    elif world.options.zone_unlocks.value == consts.ZONE_UNLOCKS_CHARACTERS_ONLY:
        big_ring_locations = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_BIG_RING
        )
        num_reachable = 0
        for big_ring_loc in big_ring_locations:
            for req in big_ring_loc.requirements:
                if state.has(req.character, player):
                    num_reachable += 1
                    break
        return num_reachable >= num_required
    elif world.options.zone_unlocks.value == consts.ZONE_UNLOCKS_ZONES_ONLY:
        big_ring_locations = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_BIG_RING
        )
        num_reachable = 0
        for big_ring_loc in big_ring_locations:
            if state.has(big_ring_loc.zone, player):
                num_reachable += 1
        return num_reachable >= num_required
    else:
        # Zones are unlocked per character
        big_ring_locations = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_BIG_RING
        )
        num_reachable = 0
        for big_ring_loc in big_ring_locations:
            for req in big_ring_loc.requirements:
                required_item = f"{big_ring_loc.zone} - {req.character}"
                if state.has(required_item, player):
                    num_reachable += 1
                    break
        return num_reachable >= num_required
