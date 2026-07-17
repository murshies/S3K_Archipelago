from typing import TYPE_CHECKING

import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient

from . import consts

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext


# These correspond to the names placed in each individual ROM
SK_GAME_NAME = "SONIC & KNUCKLES"
S3_GAME_NAME = "SONIC THE             HEDGEHOG 3"


class S3KClient(BizHawkClient):
    game = consts.GAME
    system = "GEN"
    patch_suffix = ".aps3k"

    async def validate_rom(self, ctx: "BizHawkClientContext") -> bool:
        game_names = await bizhawk.read(ctx.bizhawk_ctx, [(0x120, 16, "ROM"),
                                                          (0x200120, 32, "ROM")])
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
            pass
        except bizhawk.RequestFailedError:
            pass
