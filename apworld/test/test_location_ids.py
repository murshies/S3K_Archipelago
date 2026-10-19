"""
Checks the mapping from location buffer entries to location names against the
location definitions, and the parsing of the location buffer itself.
"""

import pathlib
import unittest

from .. import ALL_LOCATIONS, S3KLocationIds, S3KMemory
from ..S3KMemory import LocationBufferEntry, Zone

# The disassembly's object layouts, which are only available when running the
# tests from the repository
DISASM_LEVELS = pathlib.Path(__file__).resolve().parents[2] / 'submodules' / 'skdisasm' / 'Levels'
# Current_zone_and_act -> object layout file, matching SpriteLocPtrs in the
# disassembly
LAYOUT_FILES = {
    (Zone.ANGEL_ISLAND.value, 0): 'AIZ/Object Pos/1.bin',
    (Zone.ANGEL_ISLAND.value, 1): 'AIZ/Object Pos/2.bin',
    (Zone.HYDROCITY.value, 0): 'HCZ/Object Pos/1.bin',
    (Zone.HYDROCITY.value, 1): 'HCZ/Object Pos/2.bin',
    (Zone.MARBLE_GARDEN.value, 0): 'MGZ/Object Pos/1.bin',
    (Zone.MARBLE_GARDEN.value, 1): 'MGZ/Object Pos/2.bin',
    (Zone.CARNIVAL_NIGHT.value, 0): 'CNZ/Object Pos/1.bin',
    (Zone.CARNIVAL_NIGHT.value, 1): 'CNZ/Object Pos/2.bin',
    (Zone.FLYING_BATTERY.value, 0): 'FBZ/Object Pos/1.bin',
    (Zone.FLYING_BATTERY.value, 1): 'FBZ/Object Pos/2.bin',
    (Zone.ICE_CAP.value, 0): 'ICZ/Object Pos/1.bin',
    (Zone.ICE_CAP.value, 1): 'ICZ/Object Pos/2.bin',
    (Zone.LAUNCH_BASE.value, 0): 'LBZ/Object Pos/1.bin',
    (Zone.LAUNCH_BASE.value, 1): 'LBZ/Object Pos/2.bin',
    (Zone.MUSHROOM_HILL.value, 0): 'MHZ/Object Pos/1.bin',
    (Zone.MUSHROOM_HILL.value, 1): 'MHZ/Object Pos/2.bin',
    (Zone.SANDOPOLIS.value, 0): 'SOZ/Object Pos/1.bin',
    (Zone.SANDOPOLIS.value, 1): 'SOZ/Object Pos/2.bin',
    (Zone.LAVA_REEF.value, 0): 'LRZ/Object Pos/1.bin',
    (Zone.LAVA_REEF.value, 1): 'LRZ/Object Pos/2.bin',
    (Zone.HIDDEN_PALACE.value, 0): 'LRZ/Object Pos/3.bin',
    (Zone.HIDDEN_PALACE.value, 1): 'HPZ/Object Pos/1.bin',
    (Zone.SKY_SANCTUARY.value, 0): 'SSZ/Object Pos/1.bin',
    (Zone.SKY_SANCTUARY.value, 1): 'SSZ/Object Pos/2.bin',
    (Zone.DEATH_EGG.value, 0): 'DEZ/Object Pos/1.bin',
    (Zone.DEATH_EGG.value, 1): 'DEZ/Object Pos/2.bin',
}
OBJ_ID_MONITOR = 1
OBJ_ID_BIG_RING = 133


def all_buffer_entries() -> list[S3KMemory.LocationBufferEntry]:
    """Every location buffer entry that the mapping knows about."""
    entries = []
    for (zone, act), act_locs in S3KLocationIds.ACTS.items():
        entries.append(LocationBufferEntry(zone, act, S3KMemory.LOC_ACT_COMPLETE))
        if act_locs.boss is not None:
            entries.append(LocationBufferEntry(zone, act, S3KMemory.LOC_BOSS))
        for special_id in act_locs.special_locations:
            entries.append(LocationBufferEntry(zone, act, special_id))
        for respawn_idx in act_locs.big_rings:
            entries.append(LocationBufferEntry(zone, act, respawn_idx))
        for respawn_idx in act_locs.item_boxes:
            entries.append(LocationBufferEntry(zone, act, respawn_idx))
    for stage in range(S3KMemory.NUM_SPECIAL_STAGES):
        entries.append(LocationBufferEntry(0, 0, S3KMemory.LOC_SS_EMERALD + stage))
        entries.append(LocationBufferEntry(0, 0, S3KMemory.LOC_SS_PERFECT + stage))
    return entries


class TestLocationIds(unittest.TestCase):
    def setUp(self) -> None:
        self.loc_set = ALL_LOCATIONS
        self.names = {loc.display_name for loc in self.loc_set.all_locations}

    def test_mapped_names_exist(self) -> None:
        for entry in all_buffer_entries():
            name, description = S3KLocationIds.resolve(entry)
            with self.subTest(entry=str(entry)):
                self.assertIsNotNone(name, description)
                self.assertIn(name, self.names)

    def test_all_locations_mapped(self) -> None:
        expected = {loc.display_name for loc in self.loc_set.all_locations}
        mapped = {S3KLocationIds.resolve(entry)[0] for entry in all_buffer_entries()}
        self.assertEqual(set(), expected - mapped)

    def test_no_shared_respawn_indices(self) -> None:
        # An object can only be an item box or a big ring, never both
        for key, act_locs in S3KLocationIds.ACTS.items():
            with self.subTest(act=key):
                self.assertEqual(set(), act_locs.item_boxes.keys() & act_locs.big_rings.keys())

    def test_unmapped_entries(self) -> None:
        sky_sanctuary = Zone.SKY_SANCTUARY.value
        for entry in (
                # Knuckles doesn't fight the first two Mecha Sonics
                LocationBufferEntry(sky_sanctuary, 1, S3KMemory.LOC_SSZ_MECHA_SONIC_1),
                LocationBufferEntry(sky_sanctuary, 1, S3KMemory.LOC_SSZ_MECHA_SONIC_2),
                LocationBufferEntry(Zone.LAVA_REEF.value, 1, S3KMemory.LOC_BOSS),
                LocationBufferEntry(Zone.ANGEL_ISLAND.value, 0, 138),
                LocationBufferEntry(0x3F, 3, 0),
        ):
            with self.subTest(entry=str(entry)):
                self.assertIsNone(S3KLocationIds.resolve(entry)[0])


class TestLayouts(unittest.TestCase):
    @unittest.skipUnless(DISASM_LEVELS.is_dir(), 'the disassembly is not available')
    def test_layouts_match_disassembly(self) -> None:
        # The client writes to the respawn table entries of these objects, so
        # every index must really be an item box or big ring in the layout
        for key, objects in S3KLocationIds.LAYOUTS.items():
            data = (DISASM_LEVELS / LAYOUT_FILES[key]).read_bytes()
            for index, obj in objects.items():
                with self.subTest(layout=key, index=index, name=obj.location_name):
                    self.assertLess(index, S3KMemory.object_respawn_table.size)
                    obj_id = data[index * 6 + 4]
                    self.assertEqual(OBJ_ID_BIG_RING if obj.big_ring else OBJ_ID_MONITOR, obj_id)

    def test_all_item_boxes_and_big_rings(self) -> None:
        names = {
            obj.location_name for objects in S3KLocationIds.LAYOUTS.values()
            for obj in objects.values()
        }
        expected = {
            S3KLocationIds.resolve(LocationBufferEntry(zone, act, index))[0]
            for (zone, act), act_locs in S3KLocationIds.ACTS.items()
            for index in [*act_locs.item_boxes, *act_locs.big_rings]
        }
        self.assertEqual(expected, names)

    def test_angel_island_burnt_part(self) -> None:
        act_1 = S3KLocationIds.LAYOUTS[(Zone.ANGEL_ISLAND.value, 0)]
        act_2 = S3KLocationIds.LAYOUTS[(Zone.ANGEL_ISLAND.value, 1)]
        self.assertEqual('Angel Island Act 1 - Item Box 10', act_1[149].location_name)
        self.assertEqual('Angel Island Act 1 - Item Box 11', act_2[49].location_name)
        self.assertEqual('Angel Island Act 1 - Big Ring 2', act_2[19].location_name)
        self.assertTrue(act_2[19].big_ring)
        self.assertEqual('Angel Island Act 2 - Item Box 1', act_2[259].location_name)
        self.assertNotIn(49, act_1)

    def test_respawn_marks(self) -> None:
        zone = Zone.ICE_CAP.value
        location_ids = {
            'Ice Cap Act 1 - Item Box 1': 1,
            'Ice Cap Act 1 - Item Box 2': 2,
            'Ice Cap Act 1 - Big Ring 1': 3,
            'Ice Cap Act 1 - Big Ring 2': 4,
            # Item box 3, item box 4, and the other acts aren't in this slot
            'Ice Cap Act 2 - Item Box 1': 5,
        }
        marks = S3KLocationIds.respawn_marks(zone, 0, location_ids, {2, 3, 5})
        self.assertEqual({
            65: S3KMemory.RESPAWN_UNCHECKED_BIT,  # Item box 1
            # Item box 2 is checked, so it's left alone
            35: S3KMemory.RESPAWN_CHECKED_BIT,  # Big ring 1
            58: S3KMemory.RESPAWN_UNCHECKED_BIT,  # Big ring 2
        }, marks)
        self.assertEqual({}, S3KLocationIds.respawn_marks(zone, 0, {}, set()))
        self.assertEqual({}, S3KLocationIds.respawn_marks(0x3F, 0, location_ids, set()))

    def test_respawn_table_writes(self) -> None:
        unchecked = S3KMemory.RESPAWN_UNCHECKED_BIT
        checked = S3KMemory.RESPAWN_CHECKED_BIT
        # Respawn indices 10-14
        data = bytes([0x80, 0x00, 0x81 | unchecked, 0x00, checked])
        writes = S3KMemory.respawn_table_writes(data, 10, {
            10: unchecked,  # Loaded object, so bit 7 is kept
            12: unchecked,  # Already marked
            14: unchecked,  # Wrong mark
        })
        self.assertEqual({
            10: (0x80, 0x80 | unchecked),
            14: (checked, unchecked),
        }, writes)


class TestLocationBuffer(unittest.TestCase):
    @staticmethod
    def make_buffer(next_slot: int, slots: dict[int, bytes]) -> bytes:
        data = bytearray(S3KMemory.location_buffer.size)
        data[0:2] = S3KMemory.LOCATION_BUFFER_INTEGRITY_VALUE.to_bytes(2, 'big')
        slot_size = S3KMemory.LOCATION_BUFFER_SLOT_SIZE
        ptr = S3KMemory.location_buffer_slots_address + next_slot * slot_size
        data[2:4] = ptr.to_bytes(2, 'big')
        for idx, slot in slots.items():
            start = S3KMemory.LOCATION_BUFFER_HEADER_SIZE + idx * slot_size
            data[start:start + 3] = slot
        return bytes(data)

    def test_empty(self) -> None:
        buffer = S3KMemory.LocationBuffer.from_bytes(self.make_buffer(0, {}))
        self.assertTrue(buffer.is_valid)
        self.assertEqual([], buffer.entries)

    def test_uninitialized(self) -> None:
        buffer = S3KMemory.LocationBuffer.from_bytes(bytes(S3KMemory.location_buffer.size))
        self.assertFalse(buffer.is_valid)

    def test_parse_and_order(self) -> None:
        # Slot 14 was written first, then the buffer wrapped around to slots 0
        # and 1. The next write goes to slot 2.
        data = self.make_buffer(2, {
            14: bytes([0x41, 0x00, 0x2C]),  # Hydrocity act 2, respawn index 44
            0: bytes([0x01, 0x80, 0x00]),   # Hydrocity act 1, act complete
            1: bytes([0xC5, 0x82, 0x09]),   # Special stage 10 perfect, garbage zone/act
        })
        buffer = S3KMemory.LocationBuffer.from_bytes(data)
        self.assertTrue(buffer.is_valid)
        self.assertEqual(2, buffer.next_slot)
        self.assertEqual([
            LocationBufferEntry(Zone.HYDROCITY.value, 1, 44),
            LocationBufferEntry(Zone.HYDROCITY.value, 0, S3KMemory.LOC_ACT_COMPLETE),
            LocationBufferEntry(5, 3, S3KMemory.LOC_SS_PERFECT + 9),
        ], buffer.entries)
        self.assertEqual(
            ['Hydrocity Act 2 - Item Box 1',
             'Hydrocity Act 1 - Complete',
             'Special Stage 10 - Perfect'],
            [S3KLocationIds.resolve(entry)[0] for entry in buffer.entries])
        # The zone/act is ignored for special stages
        self.assertEqual((S3KMemory.LOC_SS_PERFECT + 9,), buffer.entries[2].key)
