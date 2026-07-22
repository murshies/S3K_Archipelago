import logging
from typing import TYPE_CHECKING

import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient
import Utils

from . import consts, S3KMemory

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext


Utils.init_logging("S3KClient")
logger = logging.getLogger("S3KClient")

# These correspond to the names placed in each individual ROM
SK_GAME_NAME = "SONIC & KNUCKLES"
S3_GAME_NAME = "SONIC THE             HEDGEHOG 3"


class S3KClient(BizHawkClient):
    # BizHawkClient variables
    game = consts.GAME
    system = "GEN"
    patch_suffix = ".aps3k"

    # S3K-specific variables
    initialized: bool = False

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
        logger.info("Called S3KClient game_watcher")
        if not self.initialized:
            logger.info("Not initialized, attempting initialization")
            await self.handle_initialization(ctx)

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
            emeralds=0,
            lives=3,
            continues=0,
        )
        tails_save_file = S3KMemory.SaveFile(
            character=S3KMemory.SaveFileCharacter.TAILS,
            emeralds=0,
            lives=3,
            continues=0,
        )
        knuckles_save_file = S3KMemory.SaveFile(
            character=S3KMemory.SaveFileCharacter.KNUCKLES,
            emeralds=0,
            lives=3,
            continues=0,
        )

        # As a first test, assume all levels unlocked for all characters.
        payload = [
            (S3KMemory.sonic_lvl_bitmask.address,
             [0xFF, 0xFF, 0xFF, 0xFF],
             S3KMemory.sonic_lvl_bitmask.location),
            (S3KMemory.tails_lvl_bitmask.address,
             [0xFF, 0xFF, 0xFF, 0xFF],
             S3KMemory.tails_lvl_bitmask.location),
            (S3KMemory.knuckles_lvl_bitmask.address,
             [0xFF, 0xFF, 0xFF, 0xFF],
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
