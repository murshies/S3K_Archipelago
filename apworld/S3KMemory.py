# This file contains an abstraction of Sonic 3 & Knuckles RAM/ROM layout
from dataclasses import dataclass
from enum import Enum

from . import consts

MEM_RAM: str = "68K RAM"
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

    def __new__(cls, *T):
        assert len(T) == 3
        return super(MemObject, cls).__new__(cls, T)


# ROM addresses
sk_game_name = MemObject(0x120, 16, MEM_ROM)
s3_game_name = MemObject(0x200120, 32, MEM_ROM)

# RAM addresses
arch_initialized = MemObject(0xE6AC, 2, MEM_RAM)  # The slot state of the first save slot
sonic_lvl_bitmask = MemObject(0xE6A0, 4, MEM_RAM)
tails_lvl_bitmask = MemObject(0xE6A4, 4, MEM_RAM)
knuckles_lvl_bitmask = MemObject(0xE6A8, 4, MEM_RAM)
sonic_save_file = MemObject(0xE6AC, 10, MEM_RAM)
tails_save_file = MemObject(0xE6B6, 10, MEM_RAM)
knuckles_save_file = MemObject(0xE6C0, 10, MEM_RAM)
game_mode = MemObject(0xF600, 1, MEM_RAM)
current_zone = MemObject(0xFE10, 1, MEM_RAM)
act_number = MemObject(0xFE11, 1, MEM_RAM)


class GameMode(Enum):
    """
    Represents the current game mode, as specified at the address in
    game_mode. There are other valid values but these are the ones relevant to
    Archipelago.
    """
    UNKNOWN = 0xFF  # Placeholder to use for all other values
    LEVEL_LOADED = 0x0C
    SAVE_SELECT = 0x4C


class Zone(Enum):
    """
    Represents the id values used internall in the game at the current_zone RAM
    address.
    """
    ANGEL_ISLAND = 0
    HYDROCITY = 1
    MARBLE_GARDEN = 2
    CARNIVAL_NIGHT = 3
    ICE_CAP = 5  # Not a typo - Flying Battery really is 4
    LAUNCH_BASE = 6
    MUSHROOM_HILL = 7
    FLYING_BATTERY = 4
    SANDOPOLIS = 8
    LAVA_REEF = 9
    HIDDEN_PALACE = 22
    SKY_SANCTUARY = 10
    DEATH_EGG = 11
    DOOMSDAY = 12


class SaveFileCharacter(Enum):
    """
    These values correspond to the values used in the save slot in the game's
    SRAM
    """
    SONIC_AND_TAILS = 0x0
    SONIC = 0x10
    TAILS = 0x20
    KNUCKLES = 0x30


class EmeraldState(Enum):
    NOT_FOUND = 1
    CHAOS = 2
    SUPER = 3


@dataclass
class SaveFile:
    character: SaveFileCharacter
    emeralds: int
    lives: int
    continues: int

    @property
    def data(self) -> list[int]:
        """
        Transform this instance into the byte format stored in Sonic 3 &
        Knuckles' SRAM. See
        https://info.sonicretro.org/SCHG:Sonic_the_Hedgehog_3_%26_Knuckles/RAM_Editing,
        "Variables for each save slot", for an explanation of the layout. Each
        save slot is 10 bytes total. The return value is a list of bytes.
        """
        # In order to allow selection of any unlocked zone, each save slot will
        # at least be considered complete (0x100). Start with this and
        # determine if it should be changed based on the unlocked
        # emeralds. Note that these values are the upper byte of the 16 bit
        # word for this value, the lower bit is always zero and will be filled
        # in below in the return value.
        game_state = 0x1
        if self.emeralds >= consts.EMERALDS_FOR_SUPER_HUNT:
            game_state = 0x3  # Game Complete with all Super Emeralds
        elif self.emeralds >= consts.EMERALDS_FOR_CHAOS_HUNT:
            game_state = 0x2  # Game Complete with all Chaos Emeralds

        # Archipelago is going to read which levels are unlocked for each save
        # slot from a different location in SRAM, so the current level byte
        # isn't really needed. Set it to the "last level" value for each
        # character as the base game expects it. This may need to be changed
        # later since the 14 special stages will be selectable by each
        # character.
        curr_level = 0xE  # Last level for Sonic will at least one emerald set
        if self.character == SaveFileCharacter.TAILS:
            curr_level = 0xD
        elif self.character == SaveFileCharacter.KNUCKLES:
            curr_level = 0xC

        # In this Archipelago, instead of finding specific chaos or super
        # emeralds (e.g. "blue super emerald"), there are generic chaos emerald
        # pickups. So, instead of filling in state specific to each emerald
        # slot, we keep track of how many total emeralds have been
        # collected. For the purpose of the save slot data, go through and fill
        # in the emerald state in order:
        # 0 = not collected
        # 1 = chaos emerald collected
        # 3 = super emerald collected
        # 2, which is "chaos emerald traded for an (inactive) super emerald",
        # is skipped. This is because the Archipelago works differently from
        # the base game, in that each character will have access to the super
        # transformation of the highest completed emerald set.
        emerald_state = [0, 0, 0, 0, 0, 0, 0]
        idx = 0
        for emerald in range(self.emeralds):
            if emerald_state[idx] == 0:
                emerald_state[idx] = 1
            else:
                emerald_state[idx] = 3
            idx = (idx + 1) % 7
        # The emerald state is represented as a bitmask in the save data, with
        # each emerald using 2 bits
        emerald_bitmask = 0
        for idx, emerald_state in enumerate(emerald_state):
            emerald_bitmask |= emerald_state << (14 - idx * 2)

        # Construct the final payload
        return [
            game_state, 0x0,
            self.character.value,
            curr_level,
            0x0, 0x0,  # Special stage rings entered in current zone, always keep clear
            emerald_bitmask >> 8, emerald_bitmask & 0xFF,  # Split into upper and lower bytes
            self.lives,
            self.continues,
        ]
