
from . import consts
from .locations import Location, LocationSet


def location_for_goal(loc_set: LocationSet, goal_zone: str) -> Location:
    """
    Given a goal zone, return the location where the goal item should be
    placed.
    """
    if goal_zone == consts.GOAL_DOOMSDAY:
        locs = loc_set.filter_locations(
            lambda loc, ts: (loc.location_type == consts.LOCTYPE_BOSS and
                             loc.zone == consts.ZONE_DOOMSDAY))
    elif goal_zone == consts.GOAL_KNUCKLES_SKY_SANCTUARY:
        locs = loc_set.filter_locations(
            lambda loc, ts: (any(req.character == consts.CHARACTER_KNUCKLES
                                 for req in loc.requirements) and
                             loc.zone == consts.ZONE_SKY_SANCTUARY))
    elif goal_zone == consts.GOAL_DEATH_EGG:
        locs = loc_set.filter_locations(
            lambda loc, ts: (loc.location_type == consts.LOCTYPE_BOSS and
                             loc.zone == consts.ZONE_DEATH_EGG))
    else:
        raise Exception(f'Invalid goal zone "{goal_zone}"')
    assert len(locs) == 1
    return locs[0]
