"""
Checks the mapping from location buffer entries to location names against the
location definitions, and the parsing of the location buffer itself.
"""

import pathlib
import unittest

from .. import consts, locations, S3KLocationIds, S3KMemory
from ..S3KMemory import LocationBufferEntry, Zone

LOCATIONS_DIR = pathlib.Path(__file__).parent.parent / 'locations'


def load_location_set() -> locations.LocationSet:
    types = locations.LocationTypeSet.from_file(LOCATIONS_DIR / 'types.yaml')
    files = sorted(f for f in LOCATIONS_DIR.glob('*.yaml') if f.name != 'types.yaml')
    return locations.LocationSet.from_files(files, types)


def all_buffer_entries() -> list[S3KMemory.LocationBufferEntry]:
    """Every location buffer entry that the mapping knows about."""
    entries = []
    for (zone, act), act_locs in S3KLocationIds.ACTS.items():
        entries.append(LocationBufferEntry(zone, act, S3KMemory.LOC_ACT_COMPLETE))
        if act_locs.boss is not None:
            entries.append(LocationBufferEntry(zone, act, S3KMemory.LOC_BOSS))
        for special_id in act_locs.special_locations:
            entries.append(LocationBufferEntry(zone, act, special_id))
        for respawn_idx in act_locs.item_boxes:
            entries.append(LocationBufferEntry(zone, act, respawn_idx))
    for stage in range(S3KMemory.NUM_SPECIAL_STAGES):
        entries.append(LocationBufferEntry(0, 0, S3KMemory.LOC_SS_EMERALD + stage))
        entries.append(LocationBufferEntry(0, 0, S3KMemory.LOC_SS_PERFECT + stage))
    return entries


class TestLocationIds(unittest.TestCase):
    def setUp(self) -> None:
        self.loc_set = load_location_set()
        self.names = {loc.display_name for loc in self.loc_set.all_locations}

    def test_mapped_names_exist(self) -> None:
        for entry in all_buffer_entries():
            name, description = S3KLocationIds.resolve(entry)
            with self.subTest(entry=str(entry)):
                self.assertIsNotNone(name, description)
                self.assertIn(name, self.names)

    def test_all_locations_mapped(self) -> None:
        # Big rings aren't reported through the location buffer
        expected = {
            loc.display_name
            for loc in self.loc_set.all_locations
            if loc.location_type != consts.LOCTYPE_BIG_RING
        }
        mapped = {S3KLocationIds.resolve(entry)[0] for entry in all_buffer_entries()}
        self.assertEqual(set(), expected - mapped)

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
