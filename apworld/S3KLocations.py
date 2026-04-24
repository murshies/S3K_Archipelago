from BaseClasses import Location
from worlds.AutoWorld import World

from . import consts
from .locations import LocationSet


class S3KLocation(Location):
    game: str = consts.GAME


def setup_locations(world: World, location_set: LocationSet) -> dict[str, int]:
    locations: dict[str, str] = {}

    # Item box locations
    if world.options.enable_bosses:
        locs = location_set.filter_locations(
            lambda loc, ts: 'boss' in ts.types_for(loc.location_type))
        locations.update({loc.display_name: loc.id for loc in locs})
    if world.options.enable_big_rings:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == 'big_ring')
        locations.update({loc.display_name: loc.id for loc in locs})
    if world.options.enable_special_stage_emeralds:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == 'emerald')
        locations.update({loc.display_name: loc.id for loc in locs})
    if world.options.enable_special_stage_perfects:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == 'special_stage_perfect')
        locations.update({loc.display_name: loc.id for loc in locs})
    if world.options.enable_lightning_shields:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == 'lightning_shield')
        locations.update({loc.display_name: loc.id for loc in locs})
    if world.options.enable_flame_shields:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == 'flame_shield')
        locations.update({loc.display_name: loc.id for loc in locs})
    if world.options.enable_water_shields:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == 'water_shield')
        locations.update({loc.display_name: loc.id for loc in locs})
    if world.options.enable_power_sneakers:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == 'power_sneakers')
        locations.update({loc.display_name: loc.id for loc in locs})
    if world.options.enable_1_ups:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == '1_up')
        locations.update({loc.display_name: loc.id for loc in locs})
    if world.options.enable_super_rings:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == 'super_ring')
        locations.update({loc.display_name: loc.id for loc in locs})
    if world.options.enable_robotnik_item_boxes:
        locs = location_set.filter_locations(
            lambda loc, ts: loc.location_type == 'robotnik')
        locations.update({loc.display_name: loc.id for loc in locs})
