from . import S3KTestBase


class TestS3KWorld(S3KTestBase):
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
        'enable_super_ring_locations': False,
        'enable_robotnik_locations': False,
    }
