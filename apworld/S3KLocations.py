from BaseClasses import Location
from worlds.AutoWorld import World

from . import consts
from . import locations
from .S3KUtil import location_for_goal


class S3KLocation(Location):
    game: str = consts.GAME


def filter_locations(world: World, loc_set: locations.LocationSet) -> locations.LocationSet:
    """
    Given the entire set of possible locations, create a filtered location set
    which only includes the locations enables by the player's settings.
    """
    # Build a set of location ids to include in the filtered set returned by
    # this function. This avoids adding duplicates to the filtered set, for
    # example if two different parts of this function try to include the same
    # location.
    loc_id_set: set[int] = set()
    disallowed_id_set: set[int] = set()

    # Goal based checks
    # Each zone goal adds a "master emerald" item, and the player wins the game
    # when all master emerald pieces are collected. This means that the boss of
    # each goal zone needs to be added as a location.
    if world.options.big_rings_goal.value != consts.GOAL_NONE:
        loc_id_set.add(location_for_goal(
            loc_set, world.options.big_rings_goal.value).location_id)
    if world.options.chaos_emeralds_goal.value != consts.GOAL_NONE:
        loc_id_set.add(location_for_goal(
            loc_set, world.options.chaos_emeralds_goal.value).location_id)
    if world.options.super_emeralds_goal.value != consts.GOAL_NONE:
        loc_id_set.add(location_for_goal(
            loc_set, world.options.super_emeralds_goal.value).location_id)

    # Act completion locations are always enabled. This prevents the player
    # from creating a configuration with no checks in it. It also prevents
    # Knuckles' Hidden Palace Zone from having no checks.
    locs = loc_set.filter_locations(
        lambda loc, ts: loc.location_type == consts.LOCTYPE_COMPLETE
    )
    loc_id_set.update(loc.location_id for loc in locs)

    # There are a few locations that are only accessible by Hyper Sonic. If
    # Hyper Sonic is not obtainable with the player's settings, remove those
    # locations from the pool.
    if not world.hyper_state_available():
        locs = loc_set.filter_locations(
            lambda loc, ts: (len(loc.requirements) == 1 and
                             loc.requirements[0].character == consts.CHARACTER_SONIC and
                             loc.requirements[0].super_state == consts.SUPER_STATE_HYPER)
        )
        disallowed_id_set.update(loc.location_id for loc in locs)

    # Item box locations
    if world.options.enable_boss_locations:
        locs = loc_set.filter_locations(
            lambda loc, ts: consts.LOCTYPE_BOSS in ts.types_for(loc.location_type))
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_big_ring_locations:
        locs = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_BIG_RING)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_special_stage_emerald_locations:
        locs = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_EMERALD)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_special_stage_perfect_locations:
        locs = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_SPECIAL_STAGE_PERFECT)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_lightning_shield_locations:
        locs = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_LIGHTNING_SHIELD)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_flame_shield_locations:
        locs = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_FLAME_SHIELD)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_water_shield_locations:
        locs = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_WATER_SHIELD)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_invincibility_locations:
        locs = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_INVINCIBILITY)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_power_sneaker_locations:
        locs = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_POWER_SNEAKERS)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_1_up_locations:
        locs = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_ONE_UP)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_super_ring_locations:
        locs = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_SUPER_RING)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_robotnik_locations:
        locs = loc_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_ROBOTNIK)
        loc_id_set.update(loc.location_id for loc in locs)

    return locations.LocationSet(
        locations=[
            loc
            for loc in loc_set.all_locations
            if loc.location_id in loc_id_set and loc.location_id not in disallowed_id_set
        ],
        types=loc_set.types,
    )
