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
    topology_present: bool = True
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

        # Determine the starting zone/character here, if one is needed. This
        # needs to happen here because region generation happens before item
        # generation, so we can't rely on the item creation step to handle
        # this.
        self.starting_zone: str = None
        self.starting_item: items.Item = None
        zone_item_list = self.item_set.filter_items(
            lambda item: (items.ITEM_GROUP_CHARACTER in item.groups or
                          items.ITEM_GROUP_LEVEL in item.groups)
        )
        if len(zone_item_list) > 0:
            self.starting_item = self.pick_starting_zone_item(zone_item_list)
            if (
                    self.options.zone_unlocks.value == consts.ZONE_UNLOCKS_ZONES_ONLY or
                    self.options.zone_unlocks.value == consts.ZONE_UNLOCKS_ZONES_AND_CHARACTERS
            ):
                self.starting_zone = self.starting_item.name.split('-')[0].strip()

    def pick_starting_zone_item(self, zone_item_list: list[items.Item]) -> items.Item:
        """
        Given the filtered list of zone/character items, pick a starting
        zone/character.
        """
        valid_choices = []
        for item in zone_item_list:
            if self.item_is_goal_zone(item):
                continue
            valid_choices.append(item)
        return self.random.choice(valid_choices)

    def item_is_goal_zone(self, item: items.Item) -> bool:
        """
        Determines if an item would unlock a goal zone. Used in item set filtering
        to avoid putting goal zone unlocks into the item pool.
        """
        for goal_value in (
                self.options.big_rings_goal.value,
                self.options.chaos_emeralds_goal.value,
                self.options.super_emeralds_goal.value,
        ):
            if (
                    (goal_value == consts.GOAL_DEATH_EGG and
                     consts.ZONE_DEATH_EGG in item.name) or
                    (goal_value == consts.GOAL_KNUCKLES_SKY_SANCTUARY and
                     consts.ZONE_KNUCKLES_SKY_SANCTUARY in item.name) or
                    (goal_value == consts.GOAL_DOOMSDAY and
                     consts.ZONE_DOOMSDAY in item.name)
            ):
                return True
        return False

    def create_regions(self) -> None:
        S3KRegions.create_regions(self.multiworld, self, self.player, self.loc_set, self.starting_zone)

    def create_items(self) -> None:
        # If one exists, S3KRegions.create_regions needs to know the starting
        # zone so that it doesn't add any access requirements to it.
        S3KItems.create_items(self.multiworld, self, self.player, self.item_set, self.loc_set, self.starting_item)

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

    def hyper_state_available(self) -> bool:
        """
        Determines whether or not hyper state is obtainable, given the player's
        settings.

        Without any chaos/super emerald hunt goals, the emeralds will be in
        their regular locations, i.e. rewarded for beating special stages. With
        emerald hunt goals enabled, super emeralds will only be available when
        super emerald hunt is enabled. Therefore, enabling chaos emerald hunt
        without super emerald hunt makes hyper state unobtainable. There are a
        few locations which only Hyper Sonic can reach, so the absence of Hyper
        Sonic removes those locations from the pool.
        """
        chaos_emeralds_goal_enabled = self.options.chaos_emeralds_goal.value != consts.GOAL_NONE
        super_emeralds_goal_enabled = self.options.super_emeralds_goal.value != consts.GOAL_NONE
        return super_emeralds_goal_enabled or not chaos_emeralds_goal_enabled
