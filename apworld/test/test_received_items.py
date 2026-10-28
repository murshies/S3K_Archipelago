"""
Checks how received items are translated into level unlocks, emeralds, and
junk items for the item mailbox.
"""

import unittest

from .. import ALL_ITEMS, ALL_LOCATIONS, consts, items, S3KMemory, S3KReceivedItems
from ..S3KUtil import location_for_goal
from ..S3KReceivedItems import (
    CHARACTER_ZONES,
    CHARACTERS,
    LEVEL_BITS,
    SlotSettings,
    level_bitmasks,
    unlocked_zones,
)

SONIC = consts.CHARACTER_SONIC
TAILS = consts.CHARACTER_TAILS
KNUCKLES = consts.CHARACTER_KNUCKLES


def settings(
        zone_unlocks: int = consts.ZONE_UNLOCKS_ZONES_AND_CHARACTERS,
        big_rings_goal: int = consts.GOAL_NONE,
        chaos_emeralds_goal: int = consts.GOAL_NONE,
        super_emeralds_goal: int = consts.GOAL_NONE,
        big_rings_to_check: int = 50,
) -> SlotSettings:
    return SlotSettings(
        zone_unlocks=zone_unlocks,
        big_rings_goal=big_rings_goal,
        chaos_emeralds_goal=chaos_emeralds_goal,
        super_emeralds_goal=super_emeralds_goal,
        big_rings_to_check=big_rings_to_check,
    )


class TestItemDefinitions(unittest.TestCase):
    def test_character_zones_match_items(self) -> None:
        # Every "<zone> - <character>" item should be a zone that character
        # can play, and vice versa
        for char in CHARACTERS:
            with self.subTest(character=char):
                item_zones = {
                    item.name.rsplit(' - ', 1)[0]
                    for item in ALL_ITEMS.filter_items(
                        lambda item: items.ITEM_GROUP_LEVEL in item.groups and
                        item.name.endswith(f' - {char}'))
                }
                self.assertEqual(item_zones, set(CHARACTER_ZONES[char]))

    def test_level_items_have_bits(self) -> None:
        for item in ALL_ITEMS.filter_items(lambda item: item.groups == [items.ITEM_GROUP_LEVEL]):
            with self.subTest(item=item.name):
                self.assertIn(item.name, LEVEL_BITS)

    def test_level_bits_unique(self) -> None:
        # Only the two versions of Sky Sanctuary share a bit
        bits = [bit for zone, bit in LEVEL_BITS.items()
                if zone != consts.ZONE_KNUCKLES_SKY_SANCTUARY]
        self.assertEqual(len(bits), len(set(bits)))
        self.assertEqual(set(range(28)), set(bits))

    def test_junk_items(self) -> None:
        # The filler and trap items are exactly the items sent through the
        # mailbox. An item that isn't marked as filler or a trap never gets
        # into the item pool.
        junk = {item.name for item in ALL_ITEMS.filter_items(lambda item: item.filler or item.trap)}
        self.assertEqual(junk, set(S3KReceivedItems.JUNK_ITEM_TYPES))


class TestUnlocks(unittest.TestCase):
    def test_nothing_received(self) -> None:
        self.assertEqual((0, 0, 0), level_bitmasks(unlocked_zones([], settings(), 0, 0)))

    def test_zone_and_character_item(self) -> None:
        zones = unlocked_zones(
            ['Hydrocity - Tails', 'Special Stage 2 - Knuckles'], settings(), 0, 0)
        self.assertEqual((0, 1 << 1, 1 << 15), level_bitmasks(zones))

    def test_zone_item(self) -> None:
        zones = unlocked_zones(
            ['Sky Sanctuary', 'Doomsday'], settings(consts.ZONE_UNLOCKS_ZONES_ONLY), 0, 0)
        # Knuckles' Sky Sanctuary is a separate zone, and only Sonic can play
        # Doomsday
        self.assertEqual({consts.ZONE_SKY_SANCTUARY, consts.ZONE_DOOMSDAY}, zones[SONIC])
        self.assertEqual({consts.ZONE_SKY_SANCTUARY}, zones[TAILS])
        self.assertEqual(set(), zones[KNUCKLES])

    def test_character_item(self) -> None:
        zones = unlocked_zones([KNUCKLES], settings(consts.ZONE_UNLOCKS_CHARACTERS_ONLY), 0, 0)
        self.assertEqual(set(), zones[SONIC])
        self.assertEqual(set(CHARACTER_ZONES[KNUCKLES]), zones[KNUCKLES])

    def test_all_unlocked(self) -> None:
        zones = unlocked_zones([], settings(consts.ZONE_UNLOCKS_ALL_UNLOCKED), 0, 0)
        for char in CHARACTERS:
            self.assertEqual(set(CHARACTER_ZONES[char]), zones[char])
        # Knuckles can't play Death Egg or Doomsday, but Sky Sanctuary's bit is
        # set for him through his version of it
        self.assertEqual(0x0FFF_CFFF, level_bitmasks(zones)[2])

    def test_goal_zone_locked_until_goal_met(self) -> None:
        slot = settings(consts.ZONE_UNLOCKS_ALL_UNLOCKED,
                        chaos_emeralds_goal=consts.GOAL_DEATH_EGG,
                        super_emeralds_goal=consts.GOAL_DOOMSDAY)
        zones = unlocked_zones([], slot, 6, 0)
        self.assertNotIn(consts.ZONE_DEATH_EGG, zones[SONIC])
        self.assertNotIn(consts.ZONE_DOOMSDAY, zones[SONIC])

        zones = unlocked_zones([], slot, 7, 0)
        self.assertIn(consts.ZONE_DEATH_EGG, zones[SONIC])
        self.assertIn(consts.ZONE_DEATH_EGG, zones[TAILS])
        self.assertNotIn(consts.ZONE_DOOMSDAY, zones[SONIC])

        zones = unlocked_zones([], slot, 14, 0)
        self.assertIn(consts.ZONE_DOOMSDAY, zones[SONIC])
        self.assertNotIn(consts.ZONE_DOOMSDAY, zones[TAILS])

    def test_big_rings_goal(self) -> None:
        slot = settings(big_rings_goal=consts.GOAL_KNUCKLES_SKY_SANCTUARY, big_rings_to_check=3)
        self.assertNotIn(consts.ZONE_KNUCKLES_SKY_SANCTUARY,
                         unlocked_zones([], slot, 0, 2)[KNUCKLES])
        self.assertIn(consts.ZONE_KNUCKLES_SKY_SANCTUARY,
                      unlocked_zones([], slot, 0, 3)[KNUCKLES])

    def test_big_rings_checked(self) -> None:
        self.assertEqual(2, S3KReceivedItems.big_rings_checked([
            'Hydrocity Act 1 - Big Ring 1',
            'Hydrocity Act 1 - Item Box 3',
            'Ice Cap Act 2 - Big Ring 3',
        ]))


class TestEmeralds(unittest.TestCase):
    def test_count(self) -> None:
        names = [consts.ITEM_CHAOS_EMERALD] * 16 + ['Sonic']
        self.assertEqual(consts.EMERALDS_FOR_SUPER_HUNT, S3KReceivedItems.emerald_count(names))

    def test_save_file_encoding(self) -> None:
        self.assertEqual((0x1, 0x0000),
                         (S3KMemory.save_game_state(0), S3KMemory.save_emerald_bitmask(0)))
        self.assertEqual((0x1, 0x4000),
                         (S3KMemory.save_game_state(1), S3KMemory.save_emerald_bitmask(1)))
        # Each emerald uses 2 bits, starting at the top. The lowest 2 bits are
        # unused.
        self.assertEqual((0x2, 0x5554),
                         (S3KMemory.save_game_state(7), S3KMemory.save_emerald_bitmask(7)))
        # The 8th emerald turns the first one into a super emerald
        self.assertEqual((0x2, 0xD554),
                         (S3KMemory.save_game_state(8), S3KMemory.save_emerald_bitmask(8)))
        self.assertEqual((0x3, 0xFFFC),
                         (S3KMemory.save_game_state(14), S3KMemory.save_emerald_bitmask(14)))


class TestGoal(unittest.TestCase):
    def test_goal_items_exist(self) -> None:
        goal_items = {item.name for item in ALL_ITEMS.filter_items(
            lambda item: items.ITEM_GROUP_GOAL in item.groups)}
        self.assertEqual(goal_items, set(S3KReceivedItems.GOAL_ITEMS))

    def test_single_goal(self) -> None:
        slot = settings(chaos_emeralds_goal=consts.GOAL_DOOMSDAY)
        self.assertFalse(S3KReceivedItems.goal_complete(
            [consts.ITEM_CHAOS_EMERALD] * 7, slot))
        self.assertTrue(S3KReceivedItems.goal_complete(
            [consts.ITEM_CHAOS_EMERALD] * 7 + ['Master Emerald'], slot))

    def test_multiple_goals(self) -> None:
        slot = settings(big_rings_goal=consts.GOAL_DEATH_EGG,
                        chaos_emeralds_goal=consts.GOAL_DOOMSDAY)
        self.assertFalse(S3KReceivedItems.goal_complete(['Master Emerald Shard'], slot))
        self.assertTrue(S3KReceivedItems.goal_complete(['Master Emerald Shard'] * 2, slot))


class TestEndingZones(unittest.TestCase):
    DEATH_EGG = 1 << S3KMemory.ENDING_ZONE_BITS[consts.GOAL_DEATH_EGG]
    DOOMSDAY = 1 << S3KMemory.ENDING_ZONE_BITS[consts.GOAL_DOOMSDAY]
    KNUCKLES_SSZ = 1 << S3KMemory.ENDING_ZONE_BITS[consts.GOAL_KNUCKLES_SKY_SANCTUARY]

    def test_goal_locations_match(self) -> None:
        for goal, name in S3KReceivedItems.GOAL_LOCATIONS.items():
            with self.subTest(goal=goal):
                self.assertEqual(location_for_goal(ALL_LOCATIONS, goal).display_name, name)

    def test_no_goals(self) -> None:
        self.assertEqual(0, S3KReceivedItems.ending_zones(settings(), []))

    def test_single_goal(self) -> None:
        # The only goal always finishes the game
        slot = settings(chaos_emeralds_goal=consts.GOAL_DOOMSDAY)
        self.assertEqual(self.DOOMSDAY, S3KReceivedItems.ending_zones(slot, []))

    def test_multiple_goals(self) -> None:
        slot = settings(big_rings_goal=consts.GOAL_DEATH_EGG,
                        chaos_emeralds_goal=consts.GOAL_DOOMSDAY,
                        super_emeralds_goal=consts.GOAL_KNUCKLES_SKY_SANCTUARY)
        death_egg, doomsday, knuckles_ssz = (
            S3KReceivedItems.GOAL_LOCATIONS[goal]
            for goal in (consts.GOAL_DEATH_EGG, consts.GOAL_DOOMSDAY,
                         consts.GOAL_KNUCKLES_SKY_SANCTUARY))
        self.assertEqual(0, S3KReceivedItems.ending_zones(slot, []))
        self.assertEqual(0, S3KReceivedItems.ending_zones(slot, [death_egg]))
        # Only the last remaining goal plays the ending
        self.assertEqual(self.KNUCKLES_SSZ,
                         S3KReceivedItems.ending_zones(slot, [death_egg, doomsday]))
        # Once every goal is complete, any of them plays the ending again
        self.assertEqual(self.DEATH_EGG | self.DOOMSDAY | self.KNUCKLES_SSZ,
                         S3KReceivedItems.ending_zones(slot, [death_egg, doomsday, knuckles_ssz]))

    def test_unrelated_locations_ignored(self) -> None:
        slot = settings(big_rings_goal=consts.GOAL_DEATH_EGG,
                        chaos_emeralds_goal=consts.GOAL_DOOMSDAY)
        self.assertEqual(0, S3KReceivedItems.ending_zones(
            slot, ['Death Egg Act 1 - Complete', 'Doomsday - Boss']))


class TestJunkItems(unittest.TestCase):
    def test_order_kept(self) -> None:
        names = [
            'Flame Shield', 'Hydrocity', 'Poison Trap', consts.ITEM_CHAOS_EMERALD, 'Flame Shield',
        ]
        self.assertEqual([
            ('Flame Shield', S3KMemory.ITEM_TYPE_FLAME_SHIELD),
            ('Poison Trap', S3KMemory.ITEM_TYPE_POISON_TRAP),
            ('Flame Shield', S3KMemory.ITEM_TYPE_FLAME_SHIELD),
        ], S3KReceivedItems.junk_items(names))
