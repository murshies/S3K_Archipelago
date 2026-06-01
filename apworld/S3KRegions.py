from BaseClasses import MultiWorld, Region, World

from . import locations


def create_regions(
        multiworld: MultiWorld,
        world: World,
        player: int,
        location_set: locations.LocationSet,
) -> None:
    zone_set = set(loc.zone for loc in location_set.all_locations)
    regions = []
    for zone in zone_set:
        regions.append(Region(zone, player, multiworld))
    multiworld.regions += regions
