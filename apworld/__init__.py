import importlib
import yaml

from BaseClasses import ItemClassification, Tutorial
from worlds.AutoWorld import WebWorld, World

from . import consts, items, locations, S3KItems, S3KLocations, S3KRegions, S3KRules
from .S3KOptions import S3KOptions, s3k_option_groups


class S3KWebWorld(WebWorld):
    setup_en = Tutorial(
        'Multiworld Setup Guide',
        'A guide to setting up Sonic 3 & Knuckles for Archipelago',
        'English',
        'setup_en.md',
        'setup/en',
        ['murshies']
    )

    tutorials = [setup_en]
    option_groups = s3k_option_groups
    options_preset = {}  # TODO: Define some presets


class S3KWorld(World):
    """
    Sonic 3 & Knuckles is the third mainline game for the Sega Genesis. Play as
    Sonic, Tails, and Knuckles to thwart Dr. Robotnik's plans to steal the
    Master Emerald and relaunch the Death Egg.
    """
    game: str = consts.GAME
    options_dataclass = S3KOptions
    options: S3KOptions
    topology_present: bool = False
    web: WebWorld = S3KWebWorld()

    # These will be filled in later, during world generation.
    item_name_to_id = {}
    location_name_to_id = {}

    def generate_early(self) -> None:
        locs_path = importlib.resources.files(__name__) / 'locations'

        loc_types_file = locs_path / 'types.yaml'
        with importlib.resources.as_file(loc_types_file) as types_file:
            loc_types = locations.LocationTypeSet.from_file(types_file)

        loc_defs = []
        for f in locs_path.iterdir():
            if str(f).endswith('.yaml') and not str(f).endswith('types.yaml'):
                with f.open('r', encoding='utf-8') as loc_file:
                    loc_defs += yaml.safe_load(loc_file)

        loc_set = locations.LocationSet.from_definitions(loc_defs, loc_types)
        self.loc_set = S3KLocations.filter_locations(self, loc_set)
        for loc in self.loc_set.all_locations:
            self.location_name_to_id[loc.display_name] = loc.location_id

        item_yaml_filename = importlib.resources.files(__name__) / 'items.yaml'
        with importlib.resources.as_file(item_yaml_filename) as items_file:
            item_set = items.ItemSet.from_file(items_file)
        self.item_set = S3KItems.filter_items(self, item_set)
        for item in self.item_set.all_items:
            self.item_name_to_id[item.name] = item.code

    def create_regions(self) -> None:
        S3KRegions.create_regions(self.multiworld, self.player, self.loc_set)

    def create_items(self) -> None:
        S3KItems.create_items(self.multiworld, self, self.player, self.item_set, self.loc_set)

    def create_item(self, item_name: str) -> S3KItems.S3KItem:
        item = self.item_set.item_with_name(item_name)
        classification = ItemClassification.filler
        if item.progression:
            classification |= ItemClassification.progression | ItemClassification.useful
        if item.trap:
            classification |= ItemClassification.trap
        return S3KItems.S3KItem(
            name=item.name,
            classification=classification,
            code=item.code,
            player=self.player,
        )

    def set_rules(self) -> None:
        S3KRules.set_rules(self.multiworld, self, self.player, self.loc_set)

    def generate_output(self, output_directory: str) -> None:
        pass
