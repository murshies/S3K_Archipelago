import os
import pathlib

from BaseClasses import ItemClassification, Tutorial
from worlds.AutoWorld import WebWorld, World

from . import consts, items, locations, S3KItems, S3KLocations, S3KOptions, S3KRegions, S3KRules


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
    option_groups = S3KOptions.s3k_option_groups
    options_preset = {}  # TODO: Define some presets


class S3KWorld(World):
    """
    Sonic 3 & Knuckles is the third mainline game for the Sega Genesis. Play as
    Sonic, Tails, and Knuckles to thwart Dr. Robotnik's plans to steal the
    Master Emerald and relaunch the Death Egg.
    """
    game: str = consts.GAME
    options_dataclass: S3KOptions.S3KOptions
    options: S3KOptions
    topology_present: bool = False
    web: WebWorld = S3KWebWorld()

    def generate_early(self) -> None:
        # Locations and items are defined in YAML files, read them in this step
        # so that they are available for location and item generation in later
        # steps.
        locs_base_dir = pathlib.Path('.') / 'locations'
        loc_types = locations.LocationTypeSet.from_file(locs_base_dir / 'types.yaml')
        loc_def_files = [
            locs_base_dir / f for f in os.listdir(locs_base_dir)
            if f.endswith('.yaml') and f != 'types.yaml'
        ]
        loc_set = locations.LocationSet.from_files(loc_def_files, loc_types)
        self.loc_set = S3KLocations.filter_locations(self, loc_set)

        item_yaml_filename = pathlib.Path('.') / 'items.yaml'
        item_set = items.ItemSet.from_file(item_yaml_filename)
        self.item_set = S3KItems.filter_items(self, item_set)

    def create_regions(self) -> None:
        S3KRegions.create_regions(self.multiworld, self.player, self.loc_set)

    def create_items(self) -> None:
        S3KItems.create_items(self.multiworld, self, self.player, self.item_set)

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
