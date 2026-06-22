from BaseClasses import CollectionState, MultiWorld
from worlds.AutoWorld import World
from worlds.generic.Rules import add_rule, CollectionRule

from . import consts, locations


def loc_requirement_to_rule(
        world: World,
        player: int,
        loc_set: locations.LocationSet,
        loc: locations.Location,
        req: locations.LocationRequirement,
) -> CollectionRule:
    """
    Translate a single LocatonRequirement into a rules function.

    The properties of a single LocationRequirement are given an "and"
    relationship, i.e. a player must meet all of the requirements of a
    LocationRequirement in order to check the associated Location.
    """
    if world.options.logic_difficulty.value == consts.LOGIC_NORMAL and \
       req.difficulty == consts.LOGIC_HARD:
        # If the requirement is too hard for the player's settings, consider it
        # unachievable without considering any of its other attributes.
        return lambda state: False

    reqs: list[CollectionRule] = []

    # Handle the character of the location requirement. Note that having all
    # zones/characters unlocked from the start
    # (i.e. consts.ZONE_UNLOCKS_ALL_UNLOCKED) means there is no character-based
    # rule that needs to be followed, so no function is added here.
    if world.options.zone_unlocks.value == consts.ZONE_UNLOCKS_CHARACTERS_ONLY:
        reqs.append(lambda state: state.has(req.character, player))
    elif world.options.zone_unlocks.value == consts.ZONE_UNLOCKS_ZONES_AND_CHARACTERS:
        zone_item_name = f"{loc.zone} - {req.character}"
        reqs.append(lambda state: state.has(zone_item_name, player))
    elif world.options.zone_unlocks.value == consts.ZONE_UNLOCKS_ZONES_ONLY:
        reqs.append(lambda state: state.has(loc.zone, player))

    if req.super_state is not None:
        if (
                world.options.chaos_emeralds_goal.value == consts.GOAL_NONE and
                world.options.super_emeralds_goal.value == consts.GOAL_NONE
        ):
            # This means that the chaos/super emeralds are obtained through
            # completing special stages, like in the base game. Instead of
            # checking for chaos emeralds rewarded, check if the player is able
            # to reach each of the special stages.
            reqs.append(lambda state: can_reach_all_special_stages(
                world, state, player, loc_set))
        else:
            if req.super_state == consts.SUPER_STATE_SUPER:
                emerald_count = consts.EMERALDS_FOR_CHAOS_HUNT
                if req.character == consts.CHARACTER_TAILS:
                    # Unlock Sonic and Knuckles, who get their super forms after
                    # collection the chaos emeralds, Tails only gets his super form
                    # after collecting the super emeralds.
                    emerald_count = consts.EMERALDS_FOR_SUPER_HUNT
            else:  # hyper state
                # Hyper Tails does not exist, so there *should* not be a
                # requirement with this definition, but if there is, treat it like
                # Hyper Sonic/Knuckles & Super Tails.
                emerald_count = consts.EMERALDS_FOR_SUPER_HUNT
            if emerald_count == consts.EMERALDS_FOR_SUPER_HUNT and not world.hyper_state_available():
                # Super emeralds are required for this rule, but do not exist given
                # the player's settings.
                return lambda state: False
            else:
                reqs.append(lambda state: state.has('Chaos Emerald', player, emerald_count))

    return lambda state: all(req(state) for req in reqs)


def loc_requirements_to_rule(
        world: World,
        player: int,
        loc_set: locations.LocationSet,
        loc: locations.Location,
) -> CollectionRule:
    """
    Translate the Location's requirements into a rules function.

    Each Location has a list of requirements associated with it. These are
    given an "or" relationship, i.e. the player must meet one of the
    requirements in order to check the location. This function translates that
    list of requirements into a function which can be passed to Archipelago's
    `add_rule` function.
    """
    if len(loc.requirements) == 0:
        return lambda state: True
    elif is_enabled_goal_zone(world, loc.zone):
        # Do not do any of the requirement translation if this location is in a
        # goal zone. The region logic will take care of making sure that the
        # locations are only reachable when the target goal has been achieved.
        return lambda state: True
    else:
        return lambda state: any(
            loc_requirement_to_rule(world, player, loc_set, loc, req)(state)
            for req in loc.requirements
        )


def set_rules(
        multiworld: MultiWorld,
        world: World,
        player: int,
        loc_set: locations.LocationSet,
) -> None:
    """
    Add all of the rules for this game to the multiworld.

    At this point, location_set will already be filtered to only include
    locations that are enabled by the player's settings, so there is not need
    to do those sorts of checks here.
    """
    for loc in loc_set.all_locations:
        add_rule(multiworld.get_location(loc.display_name, player),
                 loc_requirements_to_rule(world, player, loc_set, loc))


def is_enabled_goal_zone(world: World, zone: str) -> bool:
    option_to_str: dict[int, str] = {
        consts.GOAL_DEATH_EGG: consts.ZONE_DEATH_EGG,
        consts.GOAL_DOOMSDAY: consts.ZONE_DOOMSDAY,
        consts.GOAL_KNUCKLES_SKY_SANCTUARY: consts.ZONE_KNUCKLES_SKY_SANCTUARY,
        consts.GOAL_NONE: 'none',
    }
    return (
        option_to_str[world.options.big_rings_goal.value] == zone or
        option_to_str[world.options.chaos_emeralds_goal.value] == zone or
        option_to_str[world.options.super_emeralds_goal.value] == zone
    )


def can_reach_all_special_stages(
        world: World,
        state: CollectionState,
        player: int,
        loc_set: locations.LocationSet,
) -> bool:
    """
    Determine whether or not the player can reach all special stages.
    """
    if world.options.zone_unlocks.value == consts.ZONE_UNLOCKS_ALL_UNLOCKED:
        return True
    elif world.options.zone_unlocks.value == consts.ZONE_UNLOCKS_CHARACTERS_ONLY:
        # Items to unlock all zones for a single character are in the item
        # pool. This means that one character is unlocked from the start, and
        # therefore all of the special stages are available to that character
        # from the start.
        return True
    elif world.options.zone_unlocks.value == consts.ZONE_UNLOCKS_ZONES_ONLY:
        # Items to unlock a single zone for all characters are in the item
        # pool. Check to see if the player has all of them.
        for stage_num in range(1, 15):
            stage_item = f"Special Stage {stage_num}"
            if not state.has(stage_item, player):
                return False
        return True
    else:
        # Zones are unlocked per character. The player only needs one character
        # to have access to the special stage to consider it reachable by the
        # player.
        for stage_num in range(1, 15):
            has_special_stage = False
            for char in (
                    consts.CHARACTER_SONIC,
                    consts.CHARACTER_TAILS,
                    consts.CHARACTER_KNUCKLES):
                special_stage_item = f"Special Stage {stage_num} - {char}"
                if state.has(special_stage_item, player):
                    has_special_stage = True
                    break
            if not has_special_stage:
                return False
        return True
