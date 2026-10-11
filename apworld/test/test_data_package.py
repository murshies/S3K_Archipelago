"""
Checks that the data package is complete as soon as the world is imported.
Archipelago computes the data package checksum at import time, and clients
trust their local copy when the checksums match, so an incomplete data package
leaves clients unable to look up location and item names.
"""

import unittest

from .. import ALL_ITEMS, ALL_LOCATIONS, load_location_set, S3KWorld
from . import S3KTestBase

# Taken when this module is imported, which is before any test generates a
# world
IMPORT_TIME_CHECKSUM: str = S3KWorld.get_data_package_data()['checksum']


class TestDataPackage(unittest.TestCase):
    def test_all_locations_and_items_present(self) -> None:
        self.assertEqual(
            {loc.display_name: loc.location_id for loc in ALL_LOCATIONS.all_locations},
            S3KWorld.location_name_to_id)
        self.assertEqual(
            {item.name: item.code for item in ALL_ITEMS.all_items},
            S3KWorld.item_name_to_id)

    def test_ids_unique(self) -> None:
        self.assertEqual(len(S3KWorld.location_name_to_id),
                         len(set(S3KWorld.location_name_to_id.values())))
        self.assertEqual(len(S3KWorld.item_name_to_id),
                         len(set(S3KWorld.item_name_to_id.values())))

    def test_ids_stable(self) -> None:
        reloaded = {loc.display_name: loc.location_id for loc in load_location_set().all_locations}
        self.assertEqual(S3KWorld.location_name_to_id, reloaded)


class TestDataPackageAfterGeneration(S3KTestBase):
    options = {
        'big_rings_to_check': 50,
        'enable_robotnik_locations': False,
        'enable_super_ring_locations': False,
    }

    def test_generation_does_not_change_data_package(self) -> None:
        self.assertEqual(IMPORT_TIME_CHECKSUM, S3KWorld.get_data_package_data()['checksum'])
