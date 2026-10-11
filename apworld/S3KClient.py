import logging
from typing import TYPE_CHECKING

import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient

from . import consts, S3KLocationIds, S3KMemory

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext


logger = logging.getLogger("Client")

# These correspond to the names placed in each individual ROM
SK_GAME_NAME = "SONIC & KNUCKLES"
S3_GAME_NAME = "SONIC THE             HEDGEHOG 3"

# When enabled, the entire parsed location buffer is logged every time it is
# read. Useful for figuring out which location ids the game writes.
LOG_LOCATION_BUFFER = False


class S3KClient(BizHawkClient):
    # BizHawkClient variables
    game = consts.GAME
    system = "GEN"
    patch_suffix = ".aps3k"

    # S3K-specific variables
    initialized: bool = False
    # Keys (see S3KMemory.LocationBufferEntry.key) of location buffer entries
    # that have already been handled. The game keeps old entries in the buffer
    # until they're overwritten, so the same entries are read many times.
    processed_location_keys: set[tuple]
    # The seed that processed_location_keys applies to
    processed_location_seed: str | None

    def __init__(self) -> None:
        super().__init__()
        self.processed_location_keys = set()
        self.processed_location_seed = None

    async def validate_rom(self, ctx: "BizHawkClientContext") -> bool:
        game_names = await bizhawk.read(ctx.bizhawk_ctx, [S3KMemory.sk_game_name,
                                                          S3KMemory.s3_game_name])
        sk_game_name = game_names[0].decode("ascii")
        s3_game_name = game_names[1].decode("ascii")
        logger.info(f"Found sk_game_name = '{sk_game_name}' and s3_game_name = '{s3_game_name}'")
        if sk_game_name != SK_GAME_NAME or s3_game_name != S3_GAME_NAME:
            return False

        ctx.game = self.game
        ctx.items_handling = 0b001
        ctx.want_slot_data = True

        return True

    async def game_watcher(self, ctx: "BizHawkClientContext") -> None:
        try:
            await self.tick(ctx)
        except Exception as e:
            logger.error(f"Exception while processing game state: {e}")

    async def tick(self, ctx: "BizHawkClientContext") -> None:
        if not self.initialized:
            logger.info("Not initialized, attempting initialization")
            await self.handle_initialization(ctx)

        await self.handle_locations(ctx)

        game_state_read_payload = [
            S3KMemory.game_mode,
            S3KMemory.current_zone,
            S3KMemory.act_number,
        ]
        game_state = await bizhawk.read(ctx.bizhawk_ctx, game_state_read_payload)
        try:
            game_mode = S3KMemory.GameMode(game_state[0][0])
        except ValueError:
            game_mode = S3KMemory.GameMode.UNKNOWN
        curr_zone = S3KMemory.Zone(game_state[1][0])
        act_number = game_state[2][0]
        if game_mode == S3KMemory.GameMode.SAVE_SELECT:
            logger.info("On save select")
        elif game_mode == S3KMemory.GameMode.LEVEL_LOADED:
            logger.info(f"In {curr_zone} act {act_number}")

    async def handle_locations(self, ctx: "BizHawkClientContext") -> None:
        """
        Reads the location buffer from the game's RAM and sends any new
        location checks to the server.
        """
        data = (await bizhawk.read(ctx.bizhawk_ctx, [S3KMemory.location_buffer]))[0]
        buffer = S3KMemory.LocationBuffer.from_bytes(data)
        if LOG_LOCATION_BUFFER:
            logger.info(self.describe_location_buffer(buffer))
        if not buffer.is_valid:
            return

        # Location names can only be translated into ids once connected to a
        # slot. Until then, leave the entries unprocessed so they're picked up
        # once the connection is made.
        if ctx.slot is None or not ctx.server_locations:
            return
        if self.processed_location_seed != ctx.seed_name:
            self.processed_location_keys.clear()
            self.processed_location_seed = ctx.seed_name

        new_entries = [
            entry for entry in buffer.entries
            if entry.key not in self.processed_location_keys
        ]
        if not new_entries:
            return

        # Only the locations enabled by the player's settings are in
        # server_locations, so this also filters out checks which don't apply
        # to this slot.
        name_to_id = {
            ctx.location_names.lookup_in_game(loc_id): loc_id
            for loc_id in ctx.server_locations
        }
        new_location_ids: set[int] = set()
        for entry in new_entries:
            self.processed_location_keys.add(entry.key)
            name, description = S3KLocationIds.resolve(entry)
            if name is None:
                logger.info(f"Ignoring location buffer entry {entry}: {description}")
            elif name not in name_to_id:
                logger.info(f"Ignoring {name}: not a location in this slot")
            else:
                logger.info(f"Checked {name}")
                new_location_ids.add(name_to_id[name])

        if new_location_ids:
            # locations_checked is resent by CommonContext on reconnect
            ctx.locations_checked |= new_location_ids
            await ctx.check_locations(new_location_ids)

    @staticmethod
    def describe_location_buffer(buffer: S3KMemory.LocationBuffer) -> str:
        lines = [
            f"Location buffer: integrity=0x{buffer.integrity:04X} "
            f"({'valid' if buffer.is_valid else 'INVALID'}), next slot={buffer.next_slot}, "
            "slots oldest to newest:"
        ]
        for slot_idx, entry in buffer.slots_oldest_first():
            if entry is None:
                lines.append(f"  [{slot_idx:2}] empty")
            else:
                _, description = S3KLocationIds.resolve(entry)
                lines.append(f"  [{slot_idx:2}] {entry} -> {description}")
        return "\n".join(lines)

    async def handle_initialization(self, ctx: "BizHawkClientContext") -> None:
        # To determine whether or not Archipelago has initialized the save
        # files, check the slot state of the first save slot. For the purposes
        # of the randomizer, all three save slots will be marked as "game
        # complete" (0x100 for complete with no emerald set, 0x200 for complete
        # with all chaos emeralds, or 0x300 for complete with all super
        # emeralds). Therefore, reading a zero here means that the game has not
        # yet initialized the same data in RAM, and reading 0x8000 (new game)
        # means that this client has not yet initialized the save files.
        init_flag = (await bizhawk.read(ctx.bizhawk_ctx, [S3KMemory.arch_initialized]))[0]
        logger.info(f"Got init flag value {init_flag}")
        if init_flag == b"\x00\x00":
            # Wait for the game to read the save data from SRAM before
            # attempting to manipulate the save data in RAM.
            logger.info("Game not yet initialized, deferring")
            return
        elif init_flag != b"\x80\x00":
            # Already initialized, set the clients flag to indicate this and do
            # nothing further.
            logger.info("Game already initialized")
            self.initialized = True
            return

        # Otherwise, do Archipelago initialization. Set up the save files, the
        # level bit fields, and set the initialized flag in the game's memory
        # if all setup is successful.
        sonic_save_file = S3KMemory.SaveFile(
            character=S3KMemory.SaveFileCharacter.SONIC,
            emeralds=10,
            lives=3,
            continues=0,
        )
        tails_save_file = S3KMemory.SaveFile(
            character=S3KMemory.SaveFileCharacter.TAILS,
            emeralds=10,
            lives=3,
            continues=0,
        )
        knuckles_save_file = S3KMemory.SaveFile(
            character=S3KMemory.SaveFileCharacter.KNUCKLES,
            emeralds=10,
            lives=3,
            continues=0,
        )

        # As a first test, assume all levels unlocked for all characters.
        payload = [
            (S3KMemory.sonic_lvl_bitmask.address,
             [0xFF, 0xFF, 0xF1, 0xFF],
             S3KMemory.sonic_lvl_bitmask.location),
            (S3KMemory.tails_lvl_bitmask.address,
             [0xFF, 0xFF, 0xDF, 0xFF],
             S3KMemory.tails_lvl_bitmask.location),
            (S3KMemory.knuckles_lvl_bitmask.address,
             [0xFF, 0xFF, 0xD7, 0xFF],
             S3KMemory.knuckles_lvl_bitmask.location),
            (S3KMemory.arch_initialized.address,
             [0xFF],
             S3KMemory.arch_initialized.location),
            (S3KMemory.sonic_save_file.address,
             sonic_save_file.data,
             S3KMemory.sonic_save_file.location),
            (S3KMemory.tails_save_file.address,
             tails_save_file.data,
             S3KMemory.tails_save_file.location),
            (S3KMemory.knuckles_save_file.address,
             knuckles_save_file.data,
             S3KMemory.knuckles_save_file.location),
        ]
        logger.info(f"Writing addresses: {payload}")
        await bizhawk.write(ctx.bizhawk_ctx, payload)

        self.initialized = True
