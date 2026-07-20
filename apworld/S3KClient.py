from typing import TYPE_CHECKING

import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient

from . import consts, S3KMemory

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext


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
        if sk_game_name != SK_GAME_NAME or s3_game_name != S3_GAME_NAME:
            return False

        ctx.game = self.game
        ctx.items_handling = 0b001
        ctx.want_slot_data = True

        return True

    async def game_watcher(self, ctx: "BizHawkClientContext") -> None:
        try:
            if not self.initialized:
                await self.handle_initialization(ctx)

        except bizhawk.RequestFailedError:
            pass

    async def handle_initialization(self, ctx: "BizHawkClientContext") -> None:
        init_flag = bool(await bizhawk.read(ctx.bizhawk_ctx, [S3KMemory.arch_initialized])[0])
        if init_flag:
            # The game has already been initialized (e.g. on a previous
            # connection), update our state to match
            self.initialized = True
            return

        # Otherwise, do Archipelago initialization. Set up the save files, the
        # level bit fields, and set the initialized flag in the game's memory
        # if all setup is successful.

        # As a first test, assume all levels unlocked for all characters.
        bizhawk.write(
            ctx.bizhawk_ctx,
            [
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
                 S3KMemory.arch_initialized.location)
            ]
        )

        self.initialized = True
