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
sonic_lvl_bitmask = MemObject(0xE69C, 4, MEM_RAM)
tails_lvl_bitmask = MemObject(0xE6A0, 4, MEM_RAM)
knuckles_lvl_bitmask = MemObject(0xE6A4, 4, MEM_RAM)
sonic_save_file = MemObject(0xE6AC, 10, MEM_RAM)
tails_save_file = MemObject(0xE6B6, 10, MEM_RAM)
knuckles_save_file = MemObject(0xE6C0, 10, MEM_RAM)
game_mode = MemObject(0xF600, 1, MEM_RAM)
current_zone = MemObject(0xFE10, 1, MEM_RAM)
act_number = MemObject(0xFE11, 1, MEM_RAM)

# Location check buffer. See Archipelago_Location_Buffer in the disassembly's
# sonic3k.constants.asm for the full description. The layout is:
# - 2 bytes: integrity value, set once the game has initialized the buffer
# - 2 bytes: pointer (low word of the RAM address) to the slot the game will
#   write the next location check to
# - LOCATION_BUFFER_SLOTS slots of LOCATION_BUFFER_SLOT_SIZE bytes each
LOCATION_BUFFER_INTEGRITY_VALUE: int = 0x4150  # 'AP'
LOCATION_BUFFER_SLOTS: int = 15
LOCATION_BUFFER_SLOT_SIZE: int = 3
LOCATION_BUFFER_HEADER_SIZE: int = 4
location_buffer = MemObject(
    0xE668,
    LOCATION_BUFFER_HEADER_SIZE + LOCATION_BUFFER_SLOTS * LOCATION_BUFFER_SLOT_SIZE,
    MEM_RAM,
)
location_buffer_slots_address: int = location_buffer.address + LOCATION_BUFFER_HEADER_SIZE

# Location ids written to the location buffer for things that aren't item
# boxes. These match the Archipelago_Loc_* constants in the disassembly. Item
# boxes use their index in the object respawn table, which never has the
# highest bit set.
LOC_ACT_COMPLETE: int = 0x8000
LOC_BOSS: int = 0x8001
LOC_SSZ_MECHA_SONIC_1: int = 0x8002
LOC_SSZ_MECHA_SONIC_2: int = 0x8003
LOC_SS_EMERALD: int = 0x8100  # + special stage number (0-13)
LOC_SS_PERFECT: int = 0x8200  # + special stage number (0-13)
NUM_SPECIAL_STAGES: int = 14


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
    # Act 1 is the Lava Reef boss (Lava Reef act 3), act 2 is Hidden Palace
    HIDDEN_PALACE = 22
    # Act 1 is the final Death Egg boss, act 2 is the Hidden Palace special stage area
    DEATH_EGG_BOSS = 23
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
        curr_level = 28

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


@dataclass(frozen=True)
class LocationBufferEntry:
    """
    A single filled slot from the location buffer. zone and act are the raw
    values from Apparent_zone_and_act (so act is 0 for act 1, 1 for act 2).
    """
    zone: int
    act: int
    location_id: int

    @property
    def is_special_stage(self) -> bool:
        return (LOC_SS_EMERALD <= self.location_id < LOC_SS_EMERALD + NUM_SPECIAL_STAGES or
                LOC_SS_PERFECT <= self.location_id < LOC_SS_PERFECT + NUM_SPECIAL_STAGES)

    @property
    def key(self) -> tuple:
        """
        A key which uniquely identifies the checked location. The zone and act
        have no meaning for special stage locations, so they are left out.
        """
        if self.is_special_stage:
            return (self.location_id,)
        return (self.zone, self.act, self.location_id)

    def __str__(self) -> str:
        if self.is_special_stage:
            return f"special stage id=0x{self.location_id:04X}"
        return (f"zone=0x{self.zone:02X} act={self.act} "
                f"id=0x{self.location_id:04X} ({self.location_id})")


@dataclass
class LocationBuffer:
    integrity: int
    next_slot: int
    # One entry per slot, in slot order. None means the slot is empty.
    slots: list[LocationBufferEntry | None]

    @property
    def is_valid(self) -> bool:
        return (self.integrity == LOCATION_BUFFER_INTEGRITY_VALUE and
                0 <= self.next_slot < LOCATION_BUFFER_SLOTS)

    @property
    def entries(self) -> list[LocationBufferEntry]:
        """All filled slots, from oldest to newest."""
        return [entry for _, entry in self.slots_oldest_first() if entry is not None]

    def slots_oldest_first(self) -> list[tuple[int, LocationBufferEntry | None]]:
        """
        (slot index, entry) pairs in the order they were written. The slot the
        game will write to next holds the oldest entry, since the buffer wraps
        around.
        """
        start = self.next_slot if 0 <= self.next_slot < LOCATION_BUFFER_SLOTS else 0
        return [
            ((start + i) % LOCATION_BUFFER_SLOTS, self.slots[(start + i) % LOCATION_BUFFER_SLOTS])
            for i in range(LOCATION_BUFFER_SLOTS)
        ]

    @staticmethod
    def from_bytes(data: bytes) -> "LocationBuffer":
        integrity = int.from_bytes(data[0:2], "big")
        next_slot_ptr = int.from_bytes(data[2:4], "big")
        slot_offset = next_slot_ptr - location_buffer_slots_address
        if slot_offset % LOCATION_BUFFER_SLOT_SIZE == 0:
            next_slot = slot_offset // LOCATION_BUFFER_SLOT_SIZE
        else:
            next_slot = -1
        slots = []
        for idx in range(LOCATION_BUFFER_SLOTS):
            start = LOCATION_BUFFER_HEADER_SIZE + idx * LOCATION_BUFFER_SLOT_SIZE
            zone_act, id_high, id_low = data[start:start + LOCATION_BUFFER_SLOT_SIZE]
            # The game zeroes the buffer on startup. An all-zero slot would
            # otherwise mean "Angel Island act 1, respawn index 0", which is
            # not an item box, so it's safe to treat as empty.
            if zone_act == 0 and id_high == 0 and id_low == 0:
                slots.append(None)
                continue
            slots.append(LocationBufferEntry(
                zone=zone_act & 0x3F,
                act=zone_act >> 6,
                location_id=(id_high << 8) | id_low,
            ))
        return LocationBuffer(integrity=integrity, next_slot=next_slot, slots=slots)
