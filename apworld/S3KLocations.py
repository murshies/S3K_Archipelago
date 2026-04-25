from BaseClasses import Location
from worlds.AutoWorld import World

from . import consts
from .locations import LocationSet


class S3KLocation(Location):
    game: str = consts.GAME


def setup_locations(world: World, location_set: LocationSet) -> dict[str, int]:
    locations: dict[str, str] = {}

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
        locations[locs[0].display_name] = locs[0].location_id

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
    if world.options.enable_bosses:
        locs = location_set.filter_locations(
            lambda loc, ts: consts.LOCTYPE_BOSS in ts.types_for(loc.location_type))
        locations.update({loc.display_name: loc.location_id for loc in locs})
    if world.options.enable_big_rings:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_BIG_RING)
        locations.update({loc.display_name: loc.location_id for loc in locs})
    if world.options.enable_special_stage_emeralds:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_EMERALD)
        locations.update({loc.display_name: loc.location_id for loc in locs})
    if world.options.enable_special_stage_perfects:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_SPECIAL_STAGE_PERFECT)
        locations.update({loc.display_name: loc.location_id for loc in locs})
    if world.options.enable_lightning_shields:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_LIGHTNING_SHIELD)
        locations.update({loc.display_name: loc.location_id for loc in locs})
    if world.options.enable_flame_shields:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_FLAME_SHIELD)
        locations.update({loc.display_name: loc.location_id for loc in locs})
    if world.options.enable_water_shields:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_WATER_SHIELD)
        locations.update({loc.display_name: loc.location_id for loc in locs})
    if world.options.enable_power_sneakers:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_POWER_SNEAKERS)
        locations.update({loc.display_name: loc.location_id for loc in locs})
    if world.options.enable_1_ups:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_ONE_UP)
        locations.update({loc.display_name: loc.location_id for loc in locs})
    if world.options.enable_super_rings:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_SUPER_RING)
        locations.update({loc.display_name: loc.location_id for loc in locs})
    if world.options.enable_robotnik_item_boxes:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == consts.LOCTYPE_ROBOTNIK)
        locations.update({loc.display_name: loc.location_id for loc in locs})

    return locations
