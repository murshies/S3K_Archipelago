from BaseClasses import Location
from worlds.AutoWorld import World

from . import consts
from .locations import LocationSet


class S3KLocation(Location):
    game: str = consts.GAME


def filter_locations(world: World, location_set: LocationSet) -> LocationSet:
    """
    Given the entire set of possible locations, create a filtered location set
    which only includes the locations enable by the player's settings.
    """
    # Build a set of location ids to include in the filtered set returned by
    # this function. This avoids adding duplicates to the filtered set, for
    # example if two different parts of this function try to include the same
    # location.
    loc_id_set: set[int] = set()

    def add_goal_location(goal_zone: str) -> None:
        if goal_zone == consts.GOAL_DOOMSDAY:
            locs = location_set.filter_locations(
                lambda loc, ts: (loc.location_type == consts.LOCTYPE_BOSS and
                                 loc.zone == consts.ZONE_DOOMSDAY))
        elif goal_zone == consts.GOAL_KNUCKLES_SKY_SANCTUARY:
            locs = location_set.filter_locations(
                lambda loc, ts: (any(req.character == consts.CHARACTER_KNUCKLES
                                     for req in loc.requirements) and
                                 loc.zone == consts.ZONE_SKY_SANCTUARY))
        elif goal_zone == consts.GOAL_DEATH_EGG:
            locs = location_set.filter_locations(
                lambda loc, ts: (loc.location_type == consts.LOCTYPE_BOSS and
                                 loc.zone == consts.ZONE_DEATH_EGG))
        else:
            raise Exception(f'Invalid goal zone "{goal_zone}"')
        assert len(locs) == 1
        loc_id_set.update(locs[0].location_id)

    # Goal based checks
    # Each zone goal adds a "master emerald" item, and the player wins the game
    # when all master emerald pieces are collected. This means that the boss of
    # each goal zone needs to be added as a location.
    if world.options.big_rings_goal.value != consts.GOAL_NONE:
        add_goal_location(world.options.big_rings_goal)
    if world.options.chaos_emeralds_goal.value != consts.GOAL_NONE:
        add_goal_location(world.options.chaos_emeralds_goal)
    if world.options.super_emeralds_goal.value != consts.GOAL_NONE:
        add_goal_location(world.options.super_emeralds_goal)

    # Item box locations
    if world.options.enable_boss_locations:
        locs = location_set.filter_locations(
            lambda loc, ts: consts.LOCTYPE_BOSS in ts.types_for(loc.location_type))
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_big_ring_locations:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_BIG_RING)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_special_stage_emerald_locations:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_EMERALD)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_special_stage_perfect_locations:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_SPECIAL_STAGE_PERFECT)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_lightning_shield_locations:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_LIGHTNING_SHIELD)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_flame_shield_locations:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_FLAME_SHIELD)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_water_shield_locations:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_WATER_SHIELD)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_invincibility_locations:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_INVINCIBILITY)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_power_sneaker_locations:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_POWER_SNEAKERS)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_1_up_locations:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_ONE_UP)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_super_ring_locations:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_SUPER_RING)
        loc_id_set.update(loc.location_id for loc in locs)
    if world.options.enable_robotnik_locations:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_ROBOTNIK)
        loc_id_set.update(loc.location_id for loc in locs)

    return LocationSet(
        locations=[
            loc
            for loc in location_set.all_locations
            if loc.location_id in loc_id_set
        ],
        types=location_set.types,
    )
