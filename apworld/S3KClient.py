from dataclasses import dataclass
import logging
import time
import typing

from NetUtils import ClientStatus
import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient

from . import consts, items, locations, S3KMemory

if typing.TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext


logger = logging.getLogger("Client")

# These correspond to the names placed in each individual ROM
SK_GAME_NAME = "SONIC & KNUCKLES"
S3_GAME_NAME = "SONIC THE             HEDGEHOG 3"

GOAL_LOCATIONS: dict[int, str] = {
    consts.GOAL_DEATH_EGG: locations.format_display_name(
        consts.ZONE_DEATH_EGG, 2, 'Complete'),
    consts.GOAL_DOOMSDAY: locations.format_display_name(
        consts.ZONE_DOOMSDAY, None, 'Complete'),
    consts.GOAL_KNUCKLES_SKY_SANCTUARY: locations.format_display_name(
        consts.ZONE_KNUCKLES_SKY_SANCTUARY, None, 'Complete'),
}


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
    # The set of locations for the game, for various queries
    _location_set: locations.LocationSet | None
    # The set of items for this game, for various queries
    _item_set: items.ItemSet | None
    # A mapping of code -> item, so we don't need to compute this over and over again
    _items_by_code: dict[int, items.Item] | None
    # The base mapping of zones to characters that can play that zone. Note
    # that this is keyed on the item group name for the character.
    _base_chars_to_zones: dict[str, set[str]] | None
    # A cache of the in-game zone/act combinations to their enabled locations
    location_cache: dict[tuple[int, int], list[locations.Location]]
    # The seed and slot for which the location cache is valid
    curr_seed_slot: tuple | None

    def __init__(self) -> None:
        super().__init__()
        self.processed_location_keys = set()
        self.processed_location_seed = None
        self.waiting_location_keys = set()
        self.requested_storage_keys = set()
        self.death_link_pending = False
        self.death_link_request_id = 0
        self.killed_by_death_link = False
        self.player_dead = False
        self.last_sent_death_time = None
        self._location_set = None
        self._item_set = None
        self._items_by_code = None
        self._base_chars_to_zones = None
        self.location_cache = {}
        self.curr_seed_slot = None

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

    def from_arch_rxd_items(self, ctx: "BizHawkClientContext") -> list[items.Item]:
        """
        Given the items received according to Archipelago, get the S3K-specific
        items.
        """
        items_by_code = self.items_by_code()
        return [items_by_code[item.item] for item in ctx.items_received]

    async def tick(self, ctx: "BizHawkClientContext") -> None:
        await self.handle_locations(ctx)

        # Applying items needs the slot data, which is only available once
        # connected to a slot
        if ctx.slot is not None and ctx.slot_data is not None:
            if ctx.slot_data.get("death_link") and "DeathLink" not in ctx.tags:
                await ctx.update_death_link(True)
            await self.handle_death(ctx)
            rxd_items = self.from_arch_rxd_items(ctx)
            await self.handle_goal(ctx, rxd_items)
            await self.handle_ending_zones(ctx)
            await self.handle_respawn_marks(ctx)
            save_state = self.save_state(ctx, rxd_items)
            if await self.handle_initialization(ctx, save_state):
                await self.sync_save_data(ctx, save_state)
                await self.handle_mailbox(ctx, rxd_items)

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
    async def handle_goal(ctx: "BizHawkClientContext", rxd_items: typing.Iterable[items.Item]) -> None:
        """Tells the server once all of the goals have been completed."""
        if ctx.finished_game:
            return

        goals_completed = [
            item for item in rxd_items
            if items.ITEM_GROUP_GOAL in item.groups
        ]
        goals = (
            ctx.slot_data['big_rings_goal'],
            ctx.slot_data['chaos_emeralds_goal'],
            ctx.slot_data['super_emeralds_goal']
        )
        num_goals = 0
        for goal in goals:
            if goal != consts.GOAL_NONE:
                num_goals += 1
        if len(goals_completed) >= num_goals:
            await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
            ctx.finished_game = True
            logger.info("All goals complete!")

    async def handle_ending_zones(self, ctx: "BizHawkClientContext") -> None:
        """
        Tells the game which goal zones should play the ending when completed
        (see S3KMemory.ending_zones). This only changes as goal locations are
        checked, but the game clears it on reset, so it's checked every tick.
        """
        checked = set([
            ctx.location_names.lookup_in_game(loc_id)
            for loc_id in ctx.checked_locations | ctx.locations_checked
        ])
        goals = {
            goal
            for goal in (
                    ctx.slot_data["big_rings_goal"],
                    ctx.slot_data["chaos_emeralds_goal"],
                    ctx.slot_data["super_emeralds_goal"],
            )
            if goal != consts.GOAL_NONE
        }
        bits = 0
        for goal in goals:
            if all(GOAL_LOCATIONS[other] in checked for other in goals - {goal}):
                bits |= 1 << S3KMemory.ENDING_ZONE_BITS[goal]
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

        new_location_ids: set[int] = set()
        for entry in new_entries:
            self.processed_location_keys.add(entry.key)
            loc = entry.to_location(self.location_set(ctx))
            if loc is None:
                logger.info(f"Ignoring location buffer entry {entry}")
            else:
                logger.info(f"Checked {loc.display_name}")
                new_location_ids.add(loc.location_id)

        if new_location_ids:
            # locations_checked is resent by CommonContext on reconnect
            ctx.locations_checked |= new_location_ids
            await ctx.check_locations(new_location_ids)

    def location_set(self, ctx: "BizHawkClientContext") -> locations.LocationSet:
        """
        Gets the set of locations relevant to this game, initializing it if
        needed.
        """
        next_seed_slot = (ctx.seed_name, ctx.slot)
        if self.curr_seed_slot != next_seed_slot:
            self.curr_seed_slot = next_seed_slot
            self._location_set = None
            self.location_cache = {}
        if self._location_set is not None:
            return self._location_set
        loc_set = locations.load_location_set()  # start with everything
        filtered = loc_set.filter_locations(
            lambda p, ts: p.location_id in ctx.server_locations
        )
        self._location_set = locations.LocationSet(filtered, loc_set.types)
        return self._location_set

    def _init_item_set(self):
        if self._item_set is not None and self._items_by_code is not None:
            return
        self._item_set = items.load_item_set()
        self._items_by_code = {item.code: item for item in self._item_set.all_items}

    def item_set(self) -> items.ItemSet:
        """
        Gets the set of items for S3K, initializing it if needed.

        Unlike location_set, this is just the full list of items, not just ones
        that are relevant to the game.
        """
        self._init_item_set()
        return self._item_set

    def items_by_code(self) -> dict[int, items.Item]:
        """
        Get the set of items, keyed by code.
        """
        self._init_item_set()
        return self._items_by_code

    def respawn_marks(
            self,
            zone: int,
            act: int,
            ctx: "BizHawkClientContext",
    ) -> dict[int, int]:
        """
        Get the respawn table bits for all item boxes and big rings in the item
        layout. This is usually the current act, but there is the one exception
        of Angel Island act 1 post-burn cutscene items internally belonging to
        act 2. Remember that zone and act are the values as reported by the
        game.
        """
        marks = {}
        checked = ctx.checked_locations | ctx.locations_checked

        try:
            game_zone = S3KMemory.Zone(zone)
        except ValueError:
            return marks

        def _loc_filter(loc: locations.Location, ts: locations.LocationTypeSet) -> bool:
            """
            Given the zone and act from the game, what locations are applicable?
            """
            def type_filter():
                return (
                    consts.LOCTYPE_ITEM_BOX in ts.types_for(loc.location_type) or
                    loc.location_type == consts.LOCTYPE_BIG_RING
                )

            if game_zone == S3KMemory.Zone.HIDDEN_PALACE and act == 0:
                return (
                    loc.zone == consts.ZONE_LAVA_REEF and
                    loc.act == 3 and
                    type_filter()
                )
            elif game_zone == S3KMemory.Zone.HIDDEN_PALACE and act == 1:
                return loc.zone == consts.ZONE_HIDDEN_PALACE and type_filter()
            elif game_zone == S3KMemory.Zone.SKY_SANCTUARY and act == 0:
                return loc.zone == consts.ZONE_SKY_SANCTUARY and type_filter()
            elif game_zone == S3KMemory.Zone.ANGEL_ISLAND:
                if act == 0:
                    # Filter out the burnt section ones
                    return (
                        loc.zone == consts.ZONE_ANGEL_ISLAND and
                        loc.act == 1 and
                        loc.obj_id not in locations.ANGEL_ISLAND_1_APPARENT_ACT_2 and
                        type_filter()
                    )
                else:  # act 2
                    return (
                        loc.zone == consts.ZONE_ANGEL_ISLAND and
                        (
                            loc.act == 2 or
                            loc.obj_id in locations.ANGEL_ISLAND_1_APPARENT_ACT_2
                        ) and
                        type_filter()
                    )
            else:
                return (
                    loc.zone == S3KMemory.ZONE_TO_NAME.get(game_zone) and
                    loc.act == act + 1 and
                    type_filter()
                )

        loc_set = self.location_set(ctx)
        cache_key = (zone, act)
        if cache_key in self.location_cache:
            locs = self.location_cache[cache_key]
        else:
            locs = loc_set.filter_locations(_loc_filter)
            self.location_cache[cache_key] = locs

        for loc in locs:
            if loc.location_id not in checked:
                marks[loc.obj_id] = S3KMemory.RESPAWN_UNCHECKED_BIT
            elif loc.location_type == consts.LOCTYPE_BIG_RING:
                marks[loc.obj_id] = S3KMemory.RESPAWN_CHECKED_BIT

        return marks

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
        marks = self.respawn_marks(zone[0], act[0], ctx)
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

    def goal_zone_availability(
            self,
            ctx: "BizHawkClientContext",
            rxd_items: list[items.Item],
            big_rings_checked: int,
            emeralds_rxd: int,
    ) -> dict[int, bool]:
        """
        Calculate a mapping of goals zones, to whether or not they are
        available to the player.
        """
        mapping = {}

        if ctx.slot_data["big_rings_goal"] != consts.GOAL_NONE:
            goal_met = big_rings_checked >= ctx.slot_data["big_rings_to_check"]
            mapping[ctx.slot_data["big_rings_goal"]] = goal_met

        if ctx.slot_data["chaos_emeralds_goal"] != consts.GOAL_NONE:
            goal_met = emeralds_rxd >= consts.EMERALDS_FOR_CHAOS_HUNT
            mapping[ctx.slot_data["chaos_emeralds_goal"]] = goal_met

        if ctx.slot_data["super_emeralds_goal"] != consts.GOAL_NONE:
            goal_met = emeralds_rxd >= consts.EMERALDS_FOR_SUPER_HUNT
            mapping[ctx.slot_data["super_emeralds_goal"]] = goal_met

        return mapping

    def zones_to_chars(
            self,
            ctx: "BizHawkClientContext",
            rxd_items: list[items.Item],
            big_rings_checked: int,
            emeralds_rxd: int,
    ) -> dict[str, set[str]]:
        if self._base_chars_to_zones is None:
            self._base_chars_to_zones = {}
            item_set = self.item_set()
            for char in consts.CHARACTERS:
                zones = item_set.filter_items(
                    lambda item: (
                        char in item.groups and
                        items.ITEM_GROUP_CHARACTER not in item.groups and
                        items.ITEM_GROUP_LEVEL in item.groups
                    ))
                self._base_chars_to_zones[char] = set([
                    item.name for item in zones
                ])

        zones_to_chars = {}
        chars_unlocked = set()
        zones_unlocked = set()
        if ctx.slot_data["zone_unlocks"] == consts.ZONE_UNLOCKS_CHARACTERS_ONLY:
            for item in rxd_items:
                if items.ITEM_GROUP_CHARACTER in item.groups:
                    chars_unlocked.add(item.name)
        elif ctx.slot_data["zone_unlocks"] == consts.ZONE_UNLOCKS_ZONES_ONLY:
            for item in rxd_items:
                if items.ITEM_GROUP_LEVEL in item.groups:
                    zones_unlocked.add(item.name)

        for char in consts.CHARACTERS:
            if char not in zones_to_chars:
                zones_to_chars[char] = set()
            if ctx.slot_data["zone_unlocks"] == consts.ZONE_UNLOCKS_ALL_UNLOCKED:
                zones_to_chars[char] = set(self._base_chars_to_zones[char])
            elif ctx.slot_data["zone_unlocks"] == consts.ZONE_UNLOCKS_CHARACTERS_ONLY:
                if char in chars_unlocked:
                    zones_to_chars[char] = set(self._base_chars_to_zones[char])
            elif ctx.slot_data["zone_unlocks"] == consts.ZONE_UNLOCKS_ZONES_ONLY:
                for zone in zones_unlocked:
                    if zone in self._base_chars_to_zones[char]:
                        zones_to_chars[char].add(zone)
            elif ctx.slot_data["zone_unlocks"] == consts.ZONE_UNLOCKS_ZONES_AND_CHARACTERS:
                for item in rxd_items:
                    if char in item.groups:
                        zone = item.name.split('-')[0].strip()
                        zones_to_chars[char].add(zone)

        # Handle adding/removing goal zones
        goal_zones_availability = self.goal_zone_availability(
            ctx, rxd_items, big_rings_checked, emeralds_rxd)
        if goal_zones_availability.get(consts.GOAL_DEATH_EGG):
            zones_to_chars[items.ITEM_GROUP_SONIC].add(consts.ZONE_DEATH_EGG)
            zones_to_chars[items.ITEM_GROUP_TAILS].add(consts.ZONE_DEATH_EGG)
        elif goal_zones_availability.get(consts.GOAL_DEATH_EGG) is False:
            zones_to_chars[items.ITEM_GROUP_SONIC].discard(consts.ZONE_DEATH_EGG)
            zones_to_chars[items.ITEM_GROUP_TAILS].discard(consts.ZONE_DEATH_EGG)

        if goal_zones_availability.get(consts.GOAL_KNUCKLES_SKY_SANCTUARY):
            zones_to_chars[items.ITEM_GROUP_KNUCKLES].add(consts.ZONE_SKY_SANCTUARY)
        elif goal_zones_availability.get(consts.GOAL_KNUCKLES_SKY_SANCTUARY) is False:
            zones_to_chars[items.ITEM_GROUP_KNUCKLES].discard(consts.ZONE_SKY_SANCTUARY)

        if goal_zones_availability.get(consts.GOAL_DOOMSDAY):
            zones_to_chars[items.ITEM_GROUP_SONIC].add(consts.ZONE_DOOMSDAY)
        elif goal_zones_availability.get(consts.GOAL_DOOMSDAY) is False:
            zones_to_chars[items.ITEM_GROUP_SONIC].discard(consts.ZONE_DOOMSDAY)

        return zones_to_chars

    def save_state(self, ctx: "BizHawkClientContext", rxd_items: list[items.Item]) -> SaveState:
        """Works out the emeralds and level unlocks from the items received."""
        checked = ctx.checked_locations | ctx.locations_checked
        emeralds_rxd = len([
            item for item in rxd_items
            if items.ITEM_GROUP_CHAOS_EMERALD in item.groups
        ])
        if emeralds_rxd > consts.EMERALDS_FOR_SUPER_HUNT:
            emeralds_rxd = consts.EMERALDS_FOR_SUPER_HUNT
        loc_set = self.location_set(ctx)
        big_rings_checked = len(loc_set.filter_locations(
            lambda p, ts: (
                p.location_type == consts.LOCTYPE_BIG_RING and
                p.location_id in checked
            )
        ))
        zones_to_chars = self.zones_to_chars(ctx, rxd_items, big_rings_checked, emeralds_rxd)
        return SaveState(
            emeralds=emeralds_rxd,
            level_bitmasks=S3KMemory.level_bitmasks(zones_to_chars),
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
        for idx in range(len(consts.CHARACTERS)):
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

    async def handle_mailbox(
            self,
            ctx: "BizHawkClientContext",
            rxd_items: list[items.Item],
    ) -> None:
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

        junk = []
        for item in rxd_items:
            if item.name in S3KMemory.JUNK_ITEM_TYPES:
                junk.append((item.name, S3KMemory.JUNK_ITEM_TYPES[item.name]))
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
