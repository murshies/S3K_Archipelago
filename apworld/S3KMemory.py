# This file contains an abstraction of Sonic 3 & Knuckles RAM/ROM layout

MEM_RAM: str = "RAM"
MEM_ROM: str = "ROM"


class MemObject(tuple):
    @property
    def address(self) -> int:
        return self[0]

    @property
    def size(self) -> int:
        """Size in bytes"""
        return self[1]

    @property
    def location(self) -> str:
        return self[2]


# ROM addresses
sk_game_name = MemObject(0x120, 16, MEM_ROM)
s3_game_name = MemObject(0x200120, 32, MEM_ROM)

# RAM addresses
arch_initialized = MemObject(0xE69F, 1, MEM_RAM)
sonic_lvl_bitmask = MemObject(0xE6A0, 4, MEM_RAM)
tails_lvl_bitmask = MemObject(0xE6A4, 4, MEM_RAM)
knuckles_lvl_bitmask = MemObject(0xE6A8, 4, MEM_RAM)
