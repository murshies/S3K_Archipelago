from dataclasses import dataclass
import logging
import time
from typing import TYPE_CHECKING

from NetUtils import ClientStatus
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
    # Keys of location buffer entries that were found while not connected to
    # a slot, and are waiting to be sent. Only used for logging.
    waiting_location_keys: set[tuple]
    # Data storage keys that have already been requested from the server
    requested_storage_keys: set[str]
    # Location name -> id, for the locations in this slot
    location_ids: dict[str, int]
    # The (seed, slot) that location_ids applies to
    location_ids_slot: tuple | None
    # Death link state
    # A death link was received and still needs to be sent to the game
    death_link_pending: bool
    # The id of the death link request in the item mailbox, or 0 if there
    # isn't one
    death_link_request_id: int
    # The game killed the player because of a death link, so the next death
    # shouldn't be sent out
    killed_by_death_link: bool
    # Whether the player was dead the last time the game was checked
    player_dead: bool
    # The time of the last death link this client sent, so it can be ignored
    # when the server sends it back
    last_sent_death_time: float | None

    def __init__(self) -> None:
        super().__init__()
        self.processed_location_keys = set()
        self.processed_location_seed = None
        self.waiting_location_keys = set()
        self.requested_storage_keys = set()
        self.location_ids = {}
        self.location_ids_slot = None
        self.death_link_pending = False
        self.death_link_request_id = 0
        self.killed_by_death_link = False
        self.player_dead = False
        self.last_sent_death_time = None

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

    def on_package(self, ctx: "BizHawkClientContext", cmd: str, args: dict) -> None:
        if cmd != "Bounced" or "DeathLink" not in args.get("tags", []):
            return
        if args["data"]["time"] == self.last_sent_death_time:
            # This client's own death link, sent back by the server
            return
        self.death_link_pending = True

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
            if ctx.slot_data.get("death_link") and "DeathLink" not in ctx.tags:
                await ctx.update_death_link(True)
            await self.handle_death(ctx)
            item_names = [ctx.item_names.lookup_in_game(item.item) for item in ctx.items_received]
            await self.handle_goal(ctx, item_names)
            await self.handle_ending_zones(ctx)
            await self.handle_respawn_marks(ctx)
            save_state = self.save_state(ctx, item_names)
            if await self.handle_initialization(ctx, save_state):
                await self.sync_save_data(ctx, save_state)
                await self.handle_mailbox(ctx, item_names)

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
        try:
            curr_zone = S3KMemory.Zone(game_state[1][0])
        except ValueError:
            # The zone isn't meaningful outside of levels (e.g. in special
            # stages or on the save select screen)
            curr_zone = None
        act_number = game_state[2][0]
        # if game_mode == S3KMemory.GameMode.SAVE_SELECT:
        #     logger.info("On save select")
        # elif game_mode == S3KMemory.GameMode.LEVEL_LOADED:
        #     logger.info(f"In {curr_zone} act {act_number}")

    @staticmethod
    async def handle_goal(ctx: "BizHawkClientContext", item_names: list[str]) -> None:
        """Tells the server once all of the goals have been completed."""
        if ctx.finished_game:
            return
        settings = S3KReceivedItems.SlotSettings.from_slot_data(ctx.slot_data)
        if S3KReceivedItems.goal_complete(item_names, settings):
            await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
            ctx.finished_game = True
            logger.info("All goals complete!")

    @staticmethod
    async def handle_ending_zones(ctx: "BizHawkClientContext") -> None:
        """
        Tells the game which goal zones should play the ending when completed
        (see S3KMemory.ending_zones). This only changes as goal locations are
        checked, but the game clears it on reset, so it's checked every tick.
        """
        settings = S3KReceivedItems.SlotSettings.from_slot_data(ctx.slot_data)
        checked_names = [
            ctx.location_names.lookup_in_game(loc_id)
            for loc_id in ctx.checked_locations | ctx.locations_checked
        ]
        bits = S3KReceivedItems.ending_zones(settings, checked_names)
        current = (await bizhawk.read(ctx.bizhawk_ctx, [S3KMemory.ending_zones]))[0]
        if current[0] != bits:
            await bizhawk.write(ctx.bizhawk_ctx, [
                (S3KMemory.ending_zones.address, [bits], S3KMemory.ending_zones.location),
            ])

    async def handle_death(self, ctx: "BizHawkClientContext") -> None:
        """Sends a death link when the player dies in a level."""
        game_mode, routine = await bizhawk.read(
            ctx.bizhawk_ctx, [S3KMemory.game_mode, S3KMemory.player_1_routine])
        dead = (game_mode[0] == S3KMemory.GameMode.LEVEL_LOADED.value and
                routine[0] in (S3KMemory.PLAYER_ROUTINE_DEATH, S3KMemory.PLAYER_ROUTINE_DROWNED))
        if dead and not self.player_dead:
            # The game kills the player in the same frame that it acknowledges a
            # death link, so a death while a death link is waiting in the
            # mailbox is treated as caused by it too
            if self.killed_by_death_link or self.death_link_request_id:
                self.killed_by_death_link = False
            elif "DeathLink" in ctx.tags:
                await ctx.send_death(f"{ctx.player_names[ctx.slot]} died")
                self.last_sent_death_time = ctx.last_death_link
        if dead:
            # The player is already dead, so a death link received now
            # doesn't need to kill them again on their next life
            self.death_link_pending = False
        self.player_dead = dead

    async def handle_locations(self, ctx: "BizHawkClientContext") -> None:
        """
        Reads the location buffer from the game's RAM and sends any new
        location checks to the server.
        """
        data = (await bizhawk.read(ctx.bizhawk_ctx, [S3KMemory.location_buffer]))[0]
        buffer = S3KMemory.LocationBuffer.from_bytes(data)
        if LOG_LOCATION_BUFFER:
            logger.info(self.describe_location_buffer(buffer))
        current_keys = {entry.key for entry in buffer.entries} if buffer.is_valid else set()
        lost_keys = self.waiting_location_keys - current_keys
        if lost_keys:
            logger.warning(
                f"{len(lost_keys)} location check(s) disappeared from the game before they could "
                "be sent to the server. This happens if the game is reset, or if more than "
                f"{S3KMemory.LOCATION_BUFFER_SLOTS} checks are made while disconnected.")
            self.waiting_location_keys -= lost_keys
        if not buffer.is_valid:
            return

        # Location names can only be translated into ids once connected to a
        # slot. Until then, leave the entries unprocessed so they're picked up
        # once the connection is made.
        if ctx.slot is None or not ctx.server_locations:
            new_keys = current_keys - self.processed_location_keys - self.waiting_location_keys
            if new_keys:
                logger.info(
                    f"Found {len(new_keys)} location check(s) in the game that this client hasn't "
                    "sent yet. They will be sent once connected to the server.")
                self.waiting_location_keys |= new_keys
            return
        # Everything in the buffer is handled below
        self.waiting_location_keys.clear()
        if self.processed_location_seed != ctx.seed_name:
            self.processed_location_keys.clear()
            self.processed_location_seed = ctx.seed_name

        new_entries = [
            entry for entry in buffer.entries
            if entry.key not in self.processed_location_keys
        ]
        if not new_entries:
            return

        name_to_id = self.slot_location_ids(ctx)
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

    def slot_location_ids(self, ctx: "BizHawkClientContext") -> dict[str, int]:
        """
        Maps location names to ids. Only the locations enabled by the player's
        settings are in server_locations, so this leaves out locations which
        don't apply to this slot.
        """
        if self.location_ids_slot != (ctx.seed_name, ctx.slot) or not self.location_ids:
            self.location_ids = {
                ctx.location_names.lookup_in_game(loc_id): loc_id
                for loc_id in ctx.server_locations
            }
            self.location_ids_slot = (ctx.seed_name, ctx.slot)
        return self.location_ids

    async def handle_respawn_marks(self, ctx: "BizHawkClientContext") -> None:
        """
        Marks the item boxes and big rings in the current act in the object
        respawn table (see S3KMemory.RESPAWN_UNCHECKED_BIT), so that the game
        can show which ones still have to be checked. The game clears the
        respawn table every time a level is loaded, so the marks have to be
        written again each time. Every tick, only the respawn byte of a single
        marked object is read to see if that's happened; the whole act is
        written at once when it has.
        """
        if not ctx.server_locations:
            return
        game_mode, zone, act = await bizhawk.read(
            ctx.bizhawk_ctx,
            [S3KMemory.game_mode, S3KMemory.current_zone, S3KMemory.act_number])
        if game_mode[0] != S3KMemory.GameMode.LEVEL_LOADED.value:
            return
        marks = S3KLocationIds.respawn_marks(
            zone[0], act[0], self.slot_location_ids(ctx),
            ctx.checked_locations | ctx.locations_checked)
        if not marks:
            # Nothing in this act needs to look different from the vanilla game
            return

        table = S3KMemory.object_respawn_table
        sentinel_index, sentinel_bits = next(iter(marks.items()))
        sentinel = (await bizhawk.read(
            ctx.bizhawk_ctx, [(table.address + sentinel_index, 1, table.location)]))[0]
        if sentinel[0] & S3KMemory.RESPAWN_ARCHIPELAGO_MASK == sentinel_bits:
            # Already marked since the act was loaded
            return

        start = min(marks)
        data = (await bizhawk.read(
            ctx.bizhawk_ctx,
            [(table.address + start, max(marks) - start + 1, table.location)]))[0]
        writes = S3KMemory.respawn_table_writes(data, start, marks)
        if not writes:
            return
        # Only write if the same act is still loaded, and the game hasn't
        # changed any of the bytes since they were read, e.g. by loading or
        # unloading one of the objects
        guards = [
            (S3KMemory.game_mode.address, list(game_mode), S3KMemory.game_mode.location),
            (S3KMemory.current_zone.address, list(zone), S3KMemory.current_zone.location),
            (S3KMemory.act_number.address, list(act), S3KMemory.act_number.location),
        ] + [
            (table.address + index, [current], table.location)
            for index, (current, _) in writes.items()
        ]
        if await bizhawk.guarded_write(
                ctx.bizhawk_ctx,
                [(table.address + index, [new], table.location)
                 for index, (_, new) in writes.items()],
                guards):
            logger.debug(f"Marked {len(writes)} item box(es) and big ring(s) in zone "
                         f"0x{zone[0]:02X} act {act[0]}")

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
        # data, check the level unlock bitmasks. If the integrity bytes is set,
        # meaning that the game has initialized that memory location, but the
        # bitmasks are completely clear, that means that this client has not
        # set any save data. If that's the case, initialize.
        integrity, sonic_bitmask, tails_bitmask, knuckles_bitmask = await bizhawk.read(
            ctx.bizhawk_ctx,
            [S3KMemory.lvl_bitmask_integrity,
             S3KMemory.sonic_lvl_bitmask,
             S3KMemory.tails_lvl_bitmask,
             S3KMemory.knuckles_lvl_bitmask])

        if integrity != b"\x41\x50":
            # If the game somehow hasn't set the integrity value by this point,
            # defer initialization.
            logger.info(f"Level bitmask integrity word not set yet (found {integrity})")
            return False

        # If any bitmasks have been written with values, we are initialized.
        if sonic_bitmask != b"\x00\x00\x00\x00":
            return True
        if tails_bitmask != b"\x00\x00\x00\x00":
            return True
        if knuckles_bitmask != b"\x00\x00\x00\x00":
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
        await bizhawk.write(ctx.bizhawk_ctx, payload)
        return True

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

    async def handle_mailbox(self, ctx: "BizHawkClientContext", item_names: list[str]) -> None:
        """
        Sends requests to the game through the item mailbox, one at a time
        (see S3KMemory.item_mailbox). These are junk items (shields, traps,
        etc.) and received death links. A death link goes ahead of the next
        junk item.

        How many junk items have been delivered is kept in the server's data
        storage, so items aren't given twice when the client restarts. The id
        of the junk item request that's waiting for the game is stored there
        too, so the client can tell whether the game processed it while the
        client wasn't running. Death links aren't stored, since a death only
        matters at the time it happens.
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

        if self.death_link_request_id:
            if last_processed_id == self.death_link_request_id:
                # The game killed the player. Don't send that death back out,
                # unless handle_death already saw and skipped it.
                logger.info("DeathLink: Killed the player")
                self.death_link_request_id = 0
                self.killed_by_death_link = not self.player_dead
                return
            if request_id == self.death_link_request_id:
                # Still waiting for the game to kill the player
                return
            # The game was reset before it processed the death link, so
            # there's no one to kill anymore
            self.death_link_request_id = 0

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

        new_id = self.next_request_id(last_processed_id, request_id)
        if self.death_link_pending and not pending_id:
            self.death_link_pending = False
            if await self.write_mailbox_request(
                    ctx, data, S3KMemory.ITEM_TYPE_DEATH_LINK, new_id):
                self.death_link_request_id = new_id
            return

        if index >= len(junk):
            return
        name, item_type = junk[index]
        # Save the request before sending it, so a client restart can tell
        # whether the game applied it
        await self.save_delivery_state(ctx, key, index, new_id)
        if await self.write_mailbox_request(ctx, data, item_type, new_id):
            logger.info(f"Sending {name} to the game")

    @staticmethod
    async def write_mailbox_request(
            ctx: "BizHawkClientContext", mailbox: bytes, item_type: int, request_id: int) -> bool:
        """
        Writes a request to the item mailbox. The request is only written if
        the mailbox still matches what was read, and the return value says
        whether it was.
        """
        return await bizhawk.guarded_write(
            ctx.bizhawk_ctx,
            [
                (S3KMemory.item_request_type.address,
                 list(item_type.to_bytes(2, "big")),
                 S3KMemory.item_request_type.location),
                (S3KMemory.item_request_id.address,
                 list(request_id.to_bytes(4, "big")),
                 S3KMemory.item_request_id.location),
            ],
            [(S3KMemory.item_mailbox.address, list(mailbox), S3KMemory.item_mailbox.location)],
        )

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
