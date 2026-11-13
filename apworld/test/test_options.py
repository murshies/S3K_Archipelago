"""
Sanity checks for different options combinations
"""

from . import S3KTestBase
from .. import S3KConfigValidationError, S3KWorld


class TestAllEnabled(S3KTestBase):
    options = {
        'big_rings_goal': 'death_egg',
        'big_rings_to_check': 50,
        'chaos_emeralds_goal': 'knuckles_sky_sanctuary',
        'super_emeralds_goal': 'doomsday',
        'death_link': True,
        'logic_difficulty': 'standard',
        'zone_unlocks': 'zones_and_characters',
        'traps_enabled': True,
        'trap_weight_percentage': 10,
        'enable_boss_locations': True,
        'enable_big_ring_locations': True,
        'enable_special_stage_emerald_locations': True,
        'enable_special_stage_perfect_locations': True,
        'enable_lightning_shield_locations': True,
        'enable_flame_shield_locations': True,
        'enable_water_shield_locations': True,
        'enable_invincibility_locations': True,
        'enable_power_sneaker_locations': True,
        'enable_1_up_locations': True,
        'enable_super_ring_locations': True,
        'enable_robotnik_locations': True,
    }


class TestBigRingsOnly(S3KTestBase):
    options = {
        'big_rings_goal': 'death_egg',
        'big_rings_to_check': 50,
        'chaos_emeralds_goal': 'none',
        'super_emeralds_goal': 'none',
        'death_link': True,
        'logic_difficulty': 'standard',
        'zone_unlocks': 'all_unlocked',
        'traps_enabled': True,
        'trap_weight_percentage': 10,
        'enable_boss_locations': True,
        'enable_big_ring_locations': True,
        'enable_special_stage_emerald_locations': True,
        'enable_special_stage_perfect_locations': True,
        'enable_lightning_shield_locations': True,
        'enable_flame_shield_locations': True,
        'enable_water_shield_locations': True,
        'enable_invincibility_locations': True,
        'enable_power_sneaker_locations': True,
        'enable_1_up_locations': True,
        'enable_super_ring_locations': True,
        'enable_robotnik_locations': True,
    }


class TestChaosEmeraldHuntOnly(S3KTestBase):
    options = {
        'big_rings_goal': 'none',
        'big_rings_to_check': 50,
        'chaos_emeralds_goal': 'death_egg',
        'super_emeralds_goal': 'none',
        'death_link': True,
        'logic_difficulty': 'standard',
        'zone_unlocks': 'all_unlocked',
        'traps_enabled': True,
        'trap_weight_percentage': 10,
        'enable_boss_locations': True,
        'enable_big_ring_locations': True,
        'enable_special_stage_emerald_locations': True,
        'enable_special_stage_perfect_locations': True,
        'enable_lightning_shield_locations': True,
        'enable_flame_shield_locations': True,
        'enable_water_shield_locations': True,
        'enable_invincibility_locations': True,
        'enable_power_sneaker_locations': True,
        'enable_1_up_locations': True,
        'enable_super_ring_locations': True,
        'enable_robotnik_locations': True,
    }


class TestSuperEmeraldHuntOnly(S3KTestBase):
    options = {
        'big_rings_goal': 'none',
        'big_rings_to_check': 50,
        'chaos_emeralds_goal': 'none',
        'super_emeralds_goal': 'death_egg',
        'death_link': True,
        'logic_difficulty': 'standard',
        'zone_unlocks': 'all_unlocked',
        'traps_enabled': True,
        'trap_weight_percentage': 10,
        'enable_boss_locations': True,
        'enable_big_ring_locations': True,
        'enable_special_stage_emerald_locations': True,
        'enable_special_stage_perfect_locations': True,
        'enable_lightning_shield_locations': True,
        'enable_flame_shield_locations': True,
        'enable_water_shield_locations': True,
        'enable_invincibility_locations': True,
        'enable_power_sneaker_locations': True,
        'enable_1_up_locations': True,
        'enable_super_ring_locations': True,
        'enable_robotnik_locations': True,
    }


class TestNoBigRingHunt(S3KTestBase):
    options = {
        'big_rings_goal': 'none',
        'big_rings_to_check': 50,
        'chaos_emeralds_goal': 'knuckles_sky_sanctuary',
        'super_emeralds_goal': 'doomsday',
        'death_link': True,
        'logic_difficulty': 'standard',
        'zone_unlocks': 'all_unlocked',
        'traps_enabled': True,
        'trap_weight_percentage': 10,
        'enable_boss_locations': True,
        'enable_big_ring_locations': True,
        'enable_special_stage_emerald_locations': True,
        'enable_special_stage_perfect_locations': True,
        'enable_lightning_shield_locations': True,
        'enable_flame_shield_locations': True,
        'enable_water_shield_locations': True,
        'enable_invincibility_locations': True,
        'enable_power_sneaker_locations': True,
        'enable_1_up_locations': True,
        'enable_super_ring_locations': True,
        'enable_robotnik_locations': True,
    }


class TestZoneCompletionOnly(S3KTestBase):
    options = {
        'big_rings_goal': 'death_egg',
        'big_rings_to_check': 50,
        'chaos_emeralds_goal': 'knuckles_sky_sanctuary',
        'super_emeralds_goal': 'doomsday',
        'death_link': True,
        'logic_difficulty': 'standard',
        'zone_unlocks': 'all_unlocked',
        'traps_enabled': True,
        'trap_weight_percentage': 10,
        'enable_boss_locations': False,
        'enable_big_ring_locations': False,
        'enable_special_stage_emerald_locations': False,
        'enable_special_stage_perfect_locations': False,
        'enable_lightning_shield_locations': False,
        'enable_flame_shield_locations': False,
        'enable_water_shield_locations': False,
        'enable_invincibility_locations': False,
        'enable_power_sneaker_locations': False,
        'enable_1_up_locations': False,
        'enable_super_ring_locations': False,
        'enable_robotnik_locations': False,
    }


class TestMaxBigRings(S3KTestBase):
    options = {
        'big_rings_goal': 'death_egg',
        'big_rings_to_check': 77,
        'chaos_emeralds_goal': 'none',
        'super_emeralds_goal': 'none',
        'death_link': True,
        'logic_difficulty': 'standard',
        'zone_unlocks': 'all_unlocked',
        'traps_enabled': True,
        'trap_weight_percentage': 10,
        'enable_boss_locations': True,
        'enable_big_ring_locations': True,
        'enable_special_stage_emerald_locations': True,
        'enable_special_stage_perfect_locations': True,
        'enable_lightning_shield_locations': True,
        'enable_flame_shield_locations': True,
        'enable_water_shield_locations': True,
        'enable_invincibility_locations': True,
        'enable_power_sneaker_locations': True,
        'enable_1_up_locations': True,
        'enable_super_ring_locations': True,
        'enable_robotnik_locations': True,
    }


class TestOneBigRing(S3KTestBase):
    options = {
        'big_rings_goal': 'death_egg',
        'big_rings_to_check': 1,
        'chaos_emeralds_goal': 'none',
        'super_emeralds_goal': 'none',
        'death_link': True,
        'logic_difficulty': 'standard',
        'zone_unlocks': 'zones_and_characters',
        'traps_enabled': True,
        'trap_weight_percentage': 10,
        'enable_boss_locations': True,
        'enable_big_ring_locations': True,
        'enable_special_stage_emerald_locations': True,
        'enable_special_stage_perfect_locations': True,
        'enable_lightning_shield_locations': True,
        'enable_flame_shield_locations': True,
        'enable_water_shield_locations': True,
        'enable_invincibility_locations': True,
        'enable_power_sneaker_locations': True,
        'enable_1_up_locations': True,
        'enable_super_ring_locations': True,
        'enable_robotnik_locations': True,
    }


class TestBigRingLocsOffBigRingsGoalEnabled(S3KTestBase):
    options = {
        'big_rings_goal': 'death_egg',
        'big_rings_to_check': 10,
        'chaos_emeralds_goal': 'none',
        'super_emeralds_goal': 'none',
        'death_link': True,
        'logic_difficulty': 'standard',
        'zone_unlocks': 'zones_and_characters',
        'traps_enabled': True,
        'trap_weight_percentage': 10,
        'enable_boss_locations': True,
        'enable_big_ring_locations': False,
        'enable_special_stage_emerald_locations': True,
        'enable_special_stage_perfect_locations': True,
        'enable_lightning_shield_locations': True,
        'enable_flame_shield_locations': True,
        'enable_water_shield_locations': True,
        'enable_invincibility_locations': True,
        'enable_power_sneaker_locations': True,
        'enable_1_up_locations': True,
        'enable_super_ring_locations': True,
        'enable_robotnik_locations': True,
    }


class TestZeroBigRingsNoBigRingsGoal(S3KTestBase):
    options = {
        'big_rings_goal': 'none',
        'big_rings_to_check': 0,
        'chaos_emeralds_goal': 'death_egg',
        'super_emeralds_goal': 'none',
        'death_link': True,
        'logic_difficulty': 'standard',
        'zone_unlocks': 'zones_and_characters',
        'traps_enabled': True,
        'trap_weight_percentage': 10,
        'enable_boss_locations': True,
        'enable_big_ring_locations': False,
        'enable_special_stage_emerald_locations': True,
        'enable_special_stage_perfect_locations': True,
        'enable_lightning_shield_locations': True,
        'enable_flame_shield_locations': True,
        'enable_water_shield_locations': True,
        'enable_invincibility_locations': True,
        'enable_power_sneaker_locations': True,
        'enable_1_up_locations': True,
        'enable_super_ring_locations': True,
        'enable_robotnik_locations': True,
    }

class TestZeroBigRingsWithBigRingsGoal(S3KTestBase):
    options = {
        'big_rings_goal': 'doomsday',
        'big_rings_to_check': 0,
        'chaos_emeralds_goal': 'death_egg',
        'super_emeralds_goal': 'none',
        'death_link': True,
        'logic_difficulty': 'standard',
        'zone_unlocks': 'zones_and_characters',
        'traps_enabled': True,
        'trap_weight_percentage': 10,
        'enable_boss_locations': True,
        'enable_big_ring_locations': False,
        'enable_special_stage_emerald_locations': True,
        'enable_special_stage_perfect_locations': True,
        'enable_lightning_shield_locations': True,
        'enable_flame_shield_locations': True,
        'enable_water_shield_locations': True,
        'enable_invincibility_locations': True,
        'enable_power_sneaker_locations': True,
        'enable_1_up_locations': True,
        'enable_super_ring_locations': True,
        'enable_robotnik_locations': True,
    }

    auto_construct = False

    def test_all_state_can_reach_everything(self):
        with self.assertRaises(S3KConfigValidationError):
            self.world_setup()

    def test_empty_state_can_reach_something(self):
        with self.assertRaises(S3KConfigValidationError):
            self.world_setup()

    def test_fill(self):
        with self.assertRaises(S3KConfigValidationError):
            self.world_setup()
