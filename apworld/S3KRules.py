from BaseClasses import MultiWorld
from worlds.AutoWorld import World
from worlds.generic.Rules import add_rule, CollectionRule

from . import consts, locations


def loc_requirement_to_rule(
        world: World,
        player: int,
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
        zone_item_name = f'{loc.zone} Zone - {req.character}'
        reqs.append(lambda state: state.has(zone_item_name, player))
    elif world.options.zone_unlocks.value == consts.ZONE_UNLOCKS_ZONES_ONLY:
        zone_item_name = f'{loc.zone} Zone'
        reqs.append(lambda state: state.has(zone_item_name, player))

    if req.super_state is not None:
        if req.super_state == consts.SUPER_STATE_SUPER:
            emerald_count = 7
            if req.character == consts.CHARACTER_TAILS:
                # Unlock Sonic and Knuckles, who get their super forms after
                # collection the chaos emeralds, Tails only gets his super form
                # after collecting the super emeralds.
                emerald_count = 14
            reqs.append(lambda state: state.has('Chaos Emerald', player, emerald_count))
        else:  # hyper state
            # Hyper Tails does not exist, so there *should* not be a
            # requirement with this definition, but if there is, treat it like
            # Hyper Sonic/Knuckles & Super Tails.
            reqs.append(lambda state: state.has('Chaos Emerald', player, 14))

    return lambda state: all(req(state) for req in reqs)


def loc_requirements_to_rule(
        world: World,
        player: int,
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
    return lambda state: any(
        loc_requirement_to_rule(world, player, loc, req)(state)
        for req in loc.requirements
    )


def set_rules(
        multiworld: MultiWorld,
        world: World,
        player: int,
        location_set: locations.LocationSet,
) -> None:
    """
    Add all of the rules for this game to the multiworld.

    At this point, location_set will already be filtered to only include
    locations that are enabled by the player's settings, so there is not need
    to do those sorts of checks here.
    """
    for loc in location_set.all_locations:
        add_rule(multiworld.get_location(loc.display_name, player),
                 loc_requirements_to_rule(world, player, loc))
