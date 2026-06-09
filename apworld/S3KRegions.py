from BaseClasses import MultiWorld, Region

from . import locations
from . import S3KLocations


def create_regions(
        multiworld: MultiWorld,
        player: int,
        loc_set: locations.LocationSet,
) -> None:
    # Archipelago requires a Menu region, which in the case of Sonic 3 &
    # Knuckles will be connected to each zone/special stage.
    menu = Region('Menu', player, multiworld)
    multiworld.regions.append(menu)
    zone_set = set(loc.zone for loc in loc_set.all_locations)
    for zone in zone_set:
        region = Region(zone, player, multiworld)
        multiworld.regions.append(region)
        # Add the locations corresponding to this region to the multiworld's
        # location pool.
        zone_locs = [loc for loc in loc_set.all_locations if loc.zone == zone]
        for loc in zone_locs:
            s3k_loc = S3KLocations.Location(
                player, loc.display_name, loc.location_id, region)
            region.locations.append(s3k_loc)
            menu.connect(region)
