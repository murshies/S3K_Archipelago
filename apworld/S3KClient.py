from dataclasses import dataclass
import logging
import time
from typing import TYPE_CHECKING

import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient

from . import consts, S3KLocationIds, S3KMemory, S3KReceivedItems

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext


logger = logging.getLogger("Client")

# These correspond to the names placed in each individual ROM
SK_GAME_NAME = "SONIC & KNUCKLES"
S3_GAME_NAME = "SONIC THE             HEDGEHOG 3"

# When enabled, the entire parsed location buffer is logged every time it is
# read. Useful for figuring out which location ids the game writes.
LOG_LOCATION_BUFFER = False


@dataclass(frozen=True)
class SaveState:
    """The save data that the received items should result in."""
    emeralds: int
    level_bitmasks: tuple[int, ...]

    @property
    def level_unlock_bytes(self) -> bytes:
        return b"".join(mask.to_bytes(4, "big") for mask in self.level_bitmasks)


class S3KClient(BizHawkClient):
    # BizHawkClient variables
    game = consts.GAME
    system = "GEN"
    patch_suffix = ".aps3k"

    # S3K-specific variables
    # Keys (see S3KMemory.LocationBufferEntry.key) of location buffer entries
    # that have already been handled. The game keeps old entries in the buffer
    # until they're overwritten, so the same entries are read many times.
    processed_location_keys: set[tuple]
    # The seed that processed_location_keys applies to
    processed_location_seed: str | None
    # Data storage keys that have already been requested from the server
    requested_storage_keys: set[str]

    def __init__(self) -> None:
        super().__init__()
        self.processed_location_keys = set()
        self.processed_location_seed = None
        self.requested_storage_keys = set()

    async def validate_rom(self, ctx: "BizHawkClientContext") -> bool:
        game_names = await bizhawk.read(ctx.bizhawk_ctx, [S3KMemory.sk_game_name,
                                                          S3KMemory.s3_game_name])
        sk_game_name = game_names[0].decode("ascii")
        s3_game_name = game_names[1].decode("ascii")
        logger.info(f"Found sk_game_name = '{sk_game_name}' and s3_game_name = '{s3_game_name}'")
        if sk_game_name != SK_GAME_NAME or s3_game_name != S3_GAME_NAME:
            return False

        ctx.game = self.game
        # Receive every item, including this player's own items and starting
        # inventory, since the game can't give out any items by itself
        ctx.items_handling = 0b111
        ctx.want_slot_data = True

        return True

    async def game_watcher(self, ctx: "BizHawkClientContext") -> None:
        try:
            await self.tick(ctx)
        except Exception as e:
            logger.error(f"Exception while processing game state: {e}")

    async def tick(self, ctx: "BizHawkClientContext") -> None:
        await self.handle_locations(ctx)

        # Applying items needs the slot data, which is only available once
        # connected to a slot
        if ctx.slot is not None and ctx.slot_data is not None:
            item_names = [ctx.item_names.lookup_in_game(item.item) for item in ctx.items_received]
            save_state = self.save_state(ctx, item_names)
            if await self.handle_initialization(ctx, save_state):
                await self.sync_save_data(ctx, save_state)
                await self.deliver_junk_items(ctx, item_names)

        game_state_read_payload = [
            S3KMemory.game_mode,
            S3KMemory.current_zone,
            S3KMemory.act_number,
        ]
        game_state = await bizhawk.read(ctx.bizhawk_ctx, game_state_read_payload)
        try:
            game_mode = S3KMemory.GameMode(game_state[0][0])
        except ValueError:
            # logger.info(f"Unknown game mode {game_state[0][0]} received")
            game_mode = S3KMemory.GameMode.UNKNOWN
        curr_zone = S3KMemory.Zone(game_state[1][0])
        act_number = game_state[2][0]
        # if game_mode == S3KMemory.GameMode.SAVE_SELECT:
        #     logger.info("On save select")
        # elif game_mode == S3KMemory.GameMode.LEVEL_LOADED:
        #     logger.info(f"In {curr_zone} act {act_number}")

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

    async def handle_initialization(
            self, ctx: "BizHawkClientContext", save_state: SaveState) -> bool:
        """
        Sets up the save files and level unlocks the first time the game runs.
        Returns whether the save data is ready to be updated.
        """
        # To determine whether or not Archipelago has initialized the save
        # files, check the slot state of the first save slot. For the purposes
        # of the randomizer, all three save slots will be marked as "game
        # complete" (0x100 for complete with no emerald set, 0x200 for complete
        # with all chaos emeralds, or 0x300 for complete with all super
        # emeralds). Therefore, reading a zero here means that the game has not
        # yet initialized the same data in RAM, and reading 0x8000 (new game)
        # means that this client has not yet initialized the save files. This
        # is checked every time, since a reset with no save data in SRAM makes
        # the save files new again.
        init_flag = (await bizhawk.read(ctx.bizhawk_ctx, [S3KMemory.arch_initialized]))[0]
        if init_flag == b"\x00\x00":
            # Wait for the game to read the save data from SRAM before
            # attempting to manipulate the save data in RAM.
            return False
        elif init_flag != b"\x80\x00":
            # Already initialized
            return True

        # Otherwise, do Archipelago initialization. Set up the save files and
        # the level bit fields, and have the game write them to SRAM.
        save_files = [
            S3KMemory.SaveFile(
                character=character,
                emeralds=save_state.emeralds,
                lives=3,
                continues=0,
            )
            for character in (
                S3KMemory.SaveFileCharacter.SONIC,
                S3KMemory.SaveFileCharacter.TAILS,
                S3KMemory.SaveFileCharacter.KNUCKLES,
            )
        ]
        payload = [
            (S3KMemory.level_unlocks.address,
             list(save_state.level_unlock_bytes),
             S3KMemory.level_unlocks.location),
            (S3KMemory.save_files.address,
             [byte for save_file in save_files for byte in save_file.data],
             S3KMemory.save_files.location),
            (S3KMemory.save_flag.address, [1, 0], S3KMemory.save_flag.location),
        ]
        logger.info("Initializing save files")
        # Only write if the save files haven't changed since they were read
        return await bizhawk.guarded_write(
            ctx.bizhawk_ctx,
            payload,
            [(S3KMemory.arch_initialized.address,
              list(init_flag),
              S3KMemory.arch_initialized.location)],
        )

    @staticmethod
    def save_state(ctx: "BizHawkClientContext", item_names: list[str]) -> SaveState:
        """Works out the emeralds and level unlocks from the items received."""
        settings = S3KReceivedItems.SlotSettings.from_slot_data(ctx.slot_data)
        checked_names = [
            ctx.location_names.lookup_in_game(loc_id)
            for loc_id in ctx.checked_locations | ctx.locations_checked
        ]
        emeralds = S3KReceivedItems.emerald_count(item_names)
        zones = S3KReceivedItems.unlocked_zones(
            item_names,
            settings,
            emeralds,
            S3KReceivedItems.big_rings_checked(checked_names),
        )
        return SaveState(
            emeralds=emeralds,
            level_bitmasks=S3KReceivedItems.level_bitmasks(zones),
        )

    async def sync_save_data(self, ctx: "BizHawkClientContext", save_state: SaveState) -> None:
        """
        Makes the level unlocks and the emeralds in every save file match the
        items received, and has the game write them to SRAM if anything
        changed. This also undoes changes the game makes itself, e.g. when it
        saves the emeralds from a special stage.
        """
        level_data, save_data = await bizhawk.read(
            ctx.bizhawk_ctx, [S3KMemory.level_unlocks, S3KMemory.save_files])

        writes = []
        if level_data != save_state.level_unlock_bytes:
            logger.info("Updating level unlocks")
            writes.append((S3KMemory.level_unlocks.address,
                           list(save_state.level_unlock_bytes),
                           S3KMemory.level_unlocks.location))

        game_state = S3KMemory.save_game_state(save_state.emeralds)
        emerald_bytes = S3KMemory.save_emerald_bitmask(save_state.emeralds).to_bytes(2, "big")
        for idx in range(len(S3KReceivedItems.CHARACTERS)):
            base = idx * S3KMemory.SAVE_FILE_SIZE
            state_offset = base + S3KMemory.SAVE_FILE_GAME_STATE_OFFSET
            emerald_offset = base + S3KMemory.SAVE_FILE_EMERALDS_OFFSET
            if (save_data[state_offset] != game_state or
                    save_data[emerald_offset:emerald_offset + 2] != emerald_bytes):
                writes.append((S3KMemory.save_files.address + state_offset,
                               [game_state],
                               S3KMemory.save_files.location))
                writes.append((S3KMemory.save_files.address + emerald_offset,
                               list(emerald_bytes),
                               S3KMemory.save_files.location))
        if not writes:
            return

        if any(write[0] != S3KMemory.level_unlocks.address for write in writes):
            logger.info(f"Updating save files to {save_state.emeralds} emeralds")
        writes.append((S3KMemory.save_flag.address, [1, 0], S3KMemory.save_flag.location))
        # Only write if nothing changed since the data was read
        await bizhawk.guarded_write(ctx.bizhawk_ctx, writes, [
            (S3KMemory.level_unlocks.address, list(level_data), S3KMemory.level_unlocks.location),
            (S3KMemory.save_files.address, list(save_data), S3KMemory.save_files.location),
        ])

    async def deliver_junk_items(self, ctx: "BizHawkClientContext", item_names: list[str]) -> None:
        """
        Gives the player junk items (shields, traps, etc.) one at a time
        through the item mailbox. See S3KMemory.item_mailbox.

        How many junk items have been delivered is kept in the server's data
        storage, so items aren't given twice when the client restarts. The id
        of the request that's waiting for the game is stored there too, so the
        client can tell whether the game processed it while the client wasn't
        running.
        """
        key = f"S3K_item_delivery_{ctx.team}_{ctx.slot}"
        if key not in ctx.stored_data:
            if key not in self.requested_storage_keys:
                ctx.set_notify(key)
                self.requested_storage_keys.add(key)
            return
        state = ctx.stored_data[key] or {}
        index: int = state.get("index", 0)
        pending_id: int = state.get("pending_id", 0)

        data = (await bizhawk.read(ctx.bizhawk_ctx, [S3KMemory.item_mailbox]))[0]
        integrity = int.from_bytes(data[0:2], "big")
        last_processed_id = int.from_bytes(data[2:6], "big")
        request_id = int.from_bytes(data[6:10], "big")
        if integrity != S3KMemory.ITEM_MAILBOX_INTEGRITY_VALUE:
            return

        junk = S3KReceivedItems.junk_items(item_names)
        if pending_id:
            if last_processed_id == pending_id:
                # The game applied the item
                if index < len(junk):
                    logger.info(f"Gave {junk[index][0]}")
                await self.save_delivery_state(ctx, key, index + 1, 0)
                return
            if request_id == pending_id:
                # Still waiting for the game to apply it
                return
            # The game was reset before it applied the item, so the request
            # was lost. Fall through and send it again.
        elif request_id != last_processed_id:
            # The game is still working on a request this client doesn't know
            # about, so wait for it to finish
            return

        if index >= len(junk):
            return
        name, item_type = junk[index]
        new_id = self.next_request_id(last_processed_id, request_id)
        # Save the request before sending it, so a client restart can tell
        # whether the game applied it
        await self.save_delivery_state(ctx, key, index, new_id)
        sent = await bizhawk.guarded_write(
            ctx.bizhawk_ctx,
            [
                (S3KMemory.item_request_type.address,
                 list(item_type.to_bytes(2, "big")),
                 S3KMemory.item_request_type.location),
                (S3KMemory.item_request_id.address,
                 list(new_id.to_bytes(4, "big")),
                 S3KMemory.item_request_id.location),
            ],
            [(S3KMemory.item_mailbox.address, list(data), S3KMemory.item_mailbox.location)],
        )
        if sent:
            logger.info(f"Sending {name} to the game")

    @staticmethod
    def next_request_id(last_processed_id: int, request_id: int) -> int:
        """
        A new mailbox request id: the current unix timestamp, bumped if needed
        so it's always newer than the ids already in the mailbox.
        """
        new_id = int(time.time()) & 0xFFFFFFFF
        newest = max(last_processed_id, request_id)
        if new_id <= newest:
            new_id = (newest + 1) & 0xFFFFFFFF
        return new_id or 1

    @staticmethod
    async def save_delivery_state(
            ctx: "BizHawkClientContext", key: str, index: int, pending_id: int) -> None:
        value = {"index": index, "pending_id": pending_id}
        ctx.stored_data[key] = value
        await ctx.send_msgs([{
            "cmd": "Set",
            "key": key,
            "default": None,
            "want_reply": False,
            "operations": [{"operation": "replace", "value": value}],
        }])
