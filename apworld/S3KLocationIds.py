# This file maps the entries the game writes to the location buffer (see
# S3KMemory.LocationBuffer) to Archipelago location names.
#
# Each entry has a zone/act (taken from Apparent_zone_and_act) and a location
# id. For item boxes and big rings, the location id is the object's index in
# the act's object layout (which is also its index in the object respawn
# table). These indices can be read from the object layout files in the
# disassembly, e.g. "Levels/HCZ/Object Pos/1.bin": each object is 6 bytes long,
# item boxes have an object id of 1, and big rings have an object id of 133.
#
# The item box and big ring numbers ("Item Box N", "Big Ring N") match the
# numbers on the maps in the location_maps directory.

from dataclasses import dataclass, field
import typing

from . import consts
from .locations import format_display_name
from .S3KMemory import (
    LOC_ACT_COMPLETE,
    LOC_BOSS,
    LOC_SS_EMERALD,
    LOC_SS_PERFECT,
    LOC_SSZ_MECHA_SONIC_1,
    LOC_SSZ_MECHA_SONIC_2,
    NUM_SPECIAL_STAGES,
    RESPAWN_CHECKED_BIT,
    RESPAWN_UNCHECKED_BIT,
    LocationBufferEntry,
    Zone,
)

LOC_NAME_COMPLETE: str = 'Complete'
LOC_NAME_BOSS: str = 'Boss'
LOC_NAME_MINIBOSS: str = 'Miniboss'
LOC_NAME_SS_EMERALD: str = 'Emerald'
LOC_NAME_SS_PERFECT: str = 'Perfect'
LOC_NAME_MECHA_SONIC_1: str = 'Mecha Sonic 1'
LOC_NAME_MECHA_SONIC_2: str = 'Mecha Sonic 2'
LOC_NAME_BIG_RING: str = 'Big Ring'
LOC_NAME_ITEM_BOX: str = 'Item Box'


@dataclass(frozen=True)
class ActLocations:
    # The zone and act, as they're named in the location yaml files
    zone: str
    act: typing.Optional[int]
    # The name of the location for defeating this act's boss, if there is one
    boss: typing.Optional[str]
    # Respawn table index -> item box number
    item_boxes: dict[int, int] = field(default_factory=dict)
    # Location ids specific to this act (other than the act complete and boss
    # ids) -> location name
    special_locations: dict[int, str] = field(default_factory=dict)
    # Respawn table index -> big ring number
    big_rings: dict[int, int] = field(default_factory=dict)
    # Respawn table indices from item_boxes and big_rings that are in the next
    # act's object layout, rather than this act's
    next_layout: frozenset[int] = frozenset()


# Keyed by the (zone, act) values written to the location buffer. Note that act
# is zero based here (0 = act 1).
ACTS: dict[tuple[int, int], ActLocations] = {
    (Zone.ANGEL_ISLAND.value, 0): ActLocations(consts.ZONE_ANGEL_ISLAND, 1, LOC_NAME_MINIBOSS, {
        4: 1, 5: 2, 18: 3, 59: 4, 77: 5, 86: 6, 111: 7, 115: 8, 117: 9, 138: 10, 149: 11,
        # Item boxes 12-16 are in the burnt part of act 1. By then, the game
        # has already switched over to the act 2 object layout, but the
        # apparent act is still act 1, so these are act 2 respawn indices.
        49: 12, 79: 13, 121: 14, 134: 15, 133: 16,
    }, big_rings={
        # Big ring 2 is in the burnt part of act 1, so it's an act 2 respawn
        # index, like item boxes 12-16
        25: 1, 19: 2,
    }, next_layout=frozenset({49, 79, 121, 134, 133, 19})),
    (Zone.ANGEL_ISLAND.value, 1): ActLocations(consts.ZONE_ANGEL_ISLAND, 2, LOC_NAME_BOSS, {
        259: 1, 265: 2, 287: 3, 348: 4, 414: 5, 494: 6, 523: 7, 549: 8, 545: 9,
        589: 10, 576: 11, 578: 12, 582: 13, 676: 14, 185: 15, 228: 16, 292: 17,
    }, big_rings={226: 1, 673: 2}),
    (Zone.HYDROCITY.value, 0): ActLocations(consts.ZONE_HYDROCITY, 1, LOC_NAME_MINIBOSS, {
        0: 1, 7: 2, 84: 3, 85: 4, 133: 5, 30: 6, 31: 7, 90: 8, 109: 9, 143: 10,
        113: 11, 112: 12, 177: 13, 290: 14, 294: 15, 299: 16, 339: 17, 323: 18,
        324: 19, 376: 20, 305: 21, 341: 22,
    }, big_rings={141: 1, 328: 2}),
    (Zone.HYDROCITY.value, 1): ActLocations(consts.ZONE_HYDROCITY, 2, LOC_NAME_BOSS, {
        # 233 and 234 are two item boxes stacked on top of each other
        44: 1, 143: 2, 163: 3, 95: 4, 96: 5, 97: 6, 98: 7, 99: 8, 233: 9, 234: 9,
        190: 10, 196: 11, 222: 12, 297: 13, 292: 14, 374: 15, 338: 16, 357: 17,
        427: 18, 386: 19, 391: 20,
    }, big_rings={260: 1, 448: 2}),
    (Zone.MARBLE_GARDEN.value, 0): ActLocations(consts.ZONE_MARBLE_GARDEN, 1, LOC_NAME_MINIBOSS, {
        16: 1, 22: 2, 90: 3, 35: 4, 58: 5, 62: 6, 135: 7, 116: 8, 119: 9, 169: 10,
        170: 11, 175: 12, 109: 13, 224: 14, 315: 15, 289: 16, 345: 17, 341: 18,
        372: 19, 293: 20, 316: 21, 317: 22, 337: 23, 404: 24, 406: 25, 408: 26,
        437: 27, 444: 28, 210: 29, 247: 30,
    }, big_rings={105: 1, 12: 2, 85: 3, 111: 4, 251: 5, 202: 6, 281: 7, 380: 8}),
    (Zone.MARBLE_GARDEN.value, 1): ActLocations(consts.ZONE_MARBLE_GARDEN, 2, LOC_NAME_BOSS, {
        1: 1, 34: 2, 36: 3, 93: 4, 90: 5, 105: 6, 187: 7, 189: 8, 190: 9, 221: 10,
        195: 11, 167: 12, 232: 13, 233: 14, 235: 15, 248: 16, 308: 17, 260: 18,
        300: 19,
    }, big_rings={23: 1, 98: 2, 209: 3}),
    (Zone.CARNIVAL_NIGHT.value, 0): ActLocations(consts.ZONE_CARNIVAL_NIGHT, 1, LOC_NAME_MINIBOSS, {
        13: 1, 74: 2, 79: 3, 81: 4, 53: 5, 94: 6, 225: 7, 229: 8, 230: 9, 290: 10,
        103: 11, 152: 12, 238: 13, 242: 14, 308: 15, 296: 16, 380: 17, 361: 18,
        368: 19, 371: 20, 460: 21, 480: 22, 481: 23, 482: 24, 0: 25, 27: 26, 28: 27,
        30: 28, 54: 29, 56: 30, 59: 31, 63: 32, 61: 33, 64: 34, 68: 35, 87: 36,
        88: 37, 90: 38, 114: 39, 122: 40, 123: 41, 376: 42,
    }, big_rings={
        93: 1, 104: 2, 262: 3, 345: 4, 470: 5, 475: 6,
    }),
    (Zone.CARNIVAL_NIGHT.value, 1): ActLocations(consts.ZONE_CARNIVAL_NIGHT, 2, LOC_NAME_BOSS, {
        21: 1, 8: 2, 9: 3, 11: 4, 97: 5, 98: 6, 99: 7, 205: 8, 68: 9, 56: 10, 49: 11,
        46: 12, 16: 13, 47: 14, 192: 15, 186: 16, 217: 17, 166: 18, 169: 19, 170: 20,
        162: 21, 359: 22, 260: 23, 410: 24, 415: 25, 353: 26, 351: 27, 347: 28,
        366: 29, 469: 30, 467: 31, 549: 32, 550: 33, 615: 34, 617: 35, 618: 36,
        626: 37, 622: 38, 621: 39, 558: 40, 345: 41, 348: 42, 641: 43, 642: 44,
        643: 45,
    }, big_rings={50: 1, 158: 2, 110: 3, 582: 4, 686: 5}),
    (Zone.FLYING_BATTERY.value, 0): ActLocations(consts.ZONE_FLYING_BATTERY, 1, LOC_NAME_MINIBOSS, {
        44: 1, 45: 2, 22: 3, 20: 4, 35: 5, 171: 6, 173: 7, 232: 8, 233: 9, 311: 10, 316: 11,
    }, big_rings={277: 1, 362: 2}),
    (Zone.FLYING_BATTERY.value, 1): ActLocations(consts.ZONE_FLYING_BATTERY, 2, LOC_NAME_BOSS, {
        36: 1, 143: 2, 144: 3, 194: 4, 307: 5, 306: 6, 425: 7,
    }, big_rings={197: 1, 357: 2}),
    (Zone.ICE_CAP.value, 0): ActLocations(consts.ZONE_ICE_CAP, 1, LOC_NAME_MINIBOSS, {
        65: 1, 154: 2, 245: 3, 108: 4,
    }, big_rings={35: 1, 58: 2}),
    (Zone.ICE_CAP.value, 1): ActLocations(consts.ZONE_ICE_CAP, 2, LOC_NAME_BOSS, {
        27: 1, 112: 2, 138: 3, 279: 4, 272: 5, 275: 6, 261: 7, 263: 8, 307: 9,
    }, big_rings={256: 1, 330: 2, 60: 3}),
    (Zone.LAUNCH_BASE.value, 0): ActLocations(consts.ZONE_LAUNCH_BASE, 1, LOC_NAME_MINIBOSS, {
        2: 1, 33: 2, 64: 3, 71: 4, 75: 5, 77: 6, 112: 7, 126: 8, 196: 9, 199: 10,
        202: 11, 159: 12, 113: 13, 278: 14, 280: 15, 215: 16, 218: 17, 216: 18,
        287: 19, 286: 20, 284: 21, 337: 22,
    }, big_rings={0: 1, 18: 2, 195: 3}),
    (Zone.LAUNCH_BASE.value, 1): ActLocations(consts.ZONE_LAUNCH_BASE, 2, LOC_NAME_BOSS, {
        25: 1, 50: 2, 92: 3, 41: 4, 114: 5, 119: 6, 122: 7, 213: 8, 254: 9, 255: 10,
        214: 11, 187: 12, 189: 13, 278: 14, 437: 15, 436: 16, 435: 17, 395: 18,
        393: 19, 290: 20, 271: 21, 267: 22, 389: 23, 394: 24, 453: 25, 49: 26,
        91: 27, 266: 28,
    }, big_rings={12: 1, 24: 2, 397: 3, 391: 4, 207: 5}),
    (Zone.MUSHROOM_HILL.value, 0): ActLocations(consts.ZONE_MUSHROOM_HILL, 1, LOC_NAME_MINIBOSS, {
        48: 1, 49: 2, 58: 3, 97: 4, 145: 5, 177: 6, 180: 7, 183: 8, 312: 9, 376: 10,
        380: 11, 407: 12, 411: 13, 443: 14, 513: 15, 515: 16, 527: 17, 75: 18,
        132: 19, 134: 20,
    }, big_rings={5: 1, 329: 2, 409: 3, 528: 4, 31: 5}),
    (Zone.MUSHROOM_HILL.value, 1): ActLocations(consts.ZONE_MUSHROOM_HILL, 2, LOC_NAME_BOSS, {
        7: 1, 28: 2, 36: 3, 39: 4, 150: 5, 151: 6, 235: 7, 274: 8, 258: 9, 312: 10,
        336: 11, 324: 12, 484: 13, 486: 14, 488: 15, 489: 16, 523: 17, 524: 18,
        55: 19, 75: 20, 396: 21, 417: 22,
    }, big_rings={119: 1, 251: 2, 403: 3, 536: 4, 345: 5, 452: 6}),
    (Zone.SANDOPOLIS.value, 0): ActLocations(consts.ZONE_SANDOPOLIS, 1, LOC_NAME_MINIBOSS, {
        5: 1, 6: 2, 3: 3, 35: 4, 47: 5, 46: 6, 102: 7, 84: 8, 82: 9, 60: 10, 147: 11,
        148: 12, 104: 13, 154: 14, 163: 15, 160: 16, 287: 17, 244: 18, 242: 19,
        292: 20, 307: 21, 333: 22, 334: 23, 388: 24, 387: 25, 442: 26, 444: 27,
        449: 28, 451: 29, 480: 30, 483: 31, 484: 32, 545: 33, 585: 34,
    }, big_rings={48: 1, 197: 2, 228: 3, 339: 4, 380: 5, 528: 6, 574: 7}),
    (Zone.SANDOPOLIS.value, 1): ActLocations(consts.ZONE_SANDOPOLIS, 2, LOC_NAME_BOSS, {
        27: 1, 11: 2, 13: 3, 30: 4, 85: 5, 82: 6, 173: 7, 175: 8, 172: 9, 253: 10,
        254: 11, 257: 12, 272: 13, 273: 14, 311: 15, 372: 16, 411: 17,
    }, big_rings={47: 1, 118: 2, 391: 3, 486: 4}),
    (Zone.LAVA_REEF.value, 0): ActLocations(consts.ZONE_LAVA_REEF, 1, LOC_NAME_MINIBOSS, {
        93: 1, 155: 2, 212: 3, 214: 4, 130: 5, 131: 6, 190: 7, 161: 8, 288: 9,
        282: 10, 276: 11, 369: 12, 370: 13, 379: 14, 455: 15, 349: 16, 347: 17,
        345: 18, 237: 19, 491: 20, 492: 21, 499: 22, 71: 23, 74: 24, 22: 25,
        119: 26, 101: 27, 245: 28, 348: 29, 451: 30, 575: 31,
    }, big_rings={216: 1, 287: 2, 335: 3}),
    (Zone.LAVA_REEF.value, 1): ActLocations(consts.ZONE_LAVA_REEF, 2, None, {
        7: 1, 68: 2, 69: 3, 30: 4, 28: 5, 82: 6, 100: 7, 188: 8, 243: 9, 237: 10,
        305: 11, 304: 12, 438: 13, 439: 14, 441: 15, 34: 16, 190: 17,
    }, big_rings={152: 1, 225: 2, 287: 3, 318: 4, 125: 5}),
    # Lava Reef's boss act is internally act 1 of the Hidden Palace zone id
    (Zone.HIDDEN_PALACE.value, 0): ActLocations(consts.ZONE_LAVA_REEF, 3, LOC_NAME_BOSS, {
        34: 1, 26: 2,
    }),
    (Zone.HIDDEN_PALACE.value, 1): ActLocations(consts.ZONE_HIDDEN_PALACE, None, None, {
        7: 1, 6: 2, 3: 3, 2: 4, 1: 5, 0: 6, 22: 7, 23: 8, 24: 9, 28: 10,
    }),
    (Zone.SKY_SANCTUARY.value, 0): ActLocations(consts.ZONE_SKY_SANCTUARY, None, LOC_NAME_BOSS, {
        111: 1, 153: 2, 156: 3, 69: 4, 10: 5, 51: 6, 52: 7, 101: 8, 114: 9, 116: 10,
        118: 11, 166: 12, 79: 13, 78: 14, 62: 15, 130: 16,
    }, {
        # The first two Mecha Sonic fights. LOC_BOSS is used for the third.
        LOC_SSZ_MECHA_SONIC_1: LOC_NAME_MECHA_SONIC_1,
        LOC_SSZ_MECHA_SONIC_2: LOC_NAME_MECHA_SONIC_2,
    }),
    (Zone.SKY_SANCTUARY.value, 1): ActLocations(
        consts.ZONE_KNUCKLES_SKY_SANCTUARY, None, LOC_NAME_BOSS),
    (Zone.DEATH_EGG.value, 0): ActLocations(consts.ZONE_DEATH_EGG, 1, LOC_NAME_MINIBOSS, {
        8: 1, 43: 2, 62: 3, 115: 4, 89: 5, 214: 6, 215: 7, 217: 8, 218: 9, 219: 10,
        220: 11, 233: 12, 273: 13, 356: 14, 357: 15, 358: 16,
    }),
    (Zone.DEATH_EGG.value, 1): ActLocations(consts.ZONE_DEATH_EGG, 2, LOC_NAME_BOSS, {
        85: 1, 86: 2, 81: 3, 35: 4, 87: 5, 102: 6, 255: 7, 253: 8, 250: 9, 321: 10,
        322: 11, 182: 12, 197: 13, 199: 14, 203: 15, 155: 16, 156: 17, 271: 18,
        269: 19, 267: 20, 440: 21, 439: 22,
    }),
    # The final Death Egg boss has its own zone id, but counts as Death Egg act 2
    (Zone.DEATH_EGG_BOSS.value, 0): ActLocations(consts.ZONE_DEATH_EGG, 2, LOC_NAME_BOSS),
    (Zone.DOOMSDAY.value, 0): ActLocations(consts.ZONE_DOOMSDAY, None, LOC_NAME_BOSS),
}


def special_stage_zone(stage: int) -> str:
    """stage is the zero based special stage number written by the game"""
    return f'Special Stage {stage + 1}'


def resolve(entry: LocationBufferEntry) -> tuple[typing.Optional[str], str]:
    """
    Translates a location buffer entry into an Archipelago location name. The
    return value is (location name, description). The location name is None if
    the entry doesn't correspond to any location; in that case, the
    description explains why.
    """
    loc_id = entry.location_id
    if LOC_SS_EMERALD <= loc_id < LOC_SS_EMERALD + NUM_SPECIAL_STAGES:
        zone = special_stage_zone(loc_id - LOC_SS_EMERALD)
        name = format_display_name(zone, None, LOC_NAME_SS_EMERALD)
        return name, name
    if LOC_SS_PERFECT <= loc_id < LOC_SS_PERFECT + NUM_SPECIAL_STAGES:
        zone = special_stage_zone(loc_id - LOC_SS_PERFECT)
        name = format_display_name(zone, None, LOC_NAME_SS_PERFECT)
        return name, name

    act = ACTS.get((entry.zone, entry.act))
    if act is None:
        return None, f'no locations in zone 0x{entry.zone:02X} act {entry.act}'
    act_name = format_display_name(act.zone, act.act, '').removesuffix(' - ')

    if loc_id == LOC_ACT_COMPLETE:
        loc_name = LOC_NAME_COMPLETE
    elif loc_id == LOC_BOSS:
        if act.boss is None:
            return None, f'{act_name} has no boss location'
        loc_name = act.boss
    elif loc_id in act.special_locations:
        loc_name = act.special_locations[loc_id]
    elif loc_id & 0x8000:
        return None, f'unknown special location id 0x{loc_id:04X}'
    elif loc_id in act.item_boxes:
        loc_name = f'{LOC_NAME_ITEM_BOX} {act.item_boxes[loc_id]}'
    elif loc_id in act.big_rings:
        loc_name = f'{LOC_NAME_BIG_RING} {act.big_rings[loc_id]}'
    else:
        return None, f'{act_name} respawn index {loc_id} is not mapped to an item box or big ring'

    name = format_display_name(act.zone, act.act, loc_name)
    return name, name


@dataclass(frozen=True)
class LayoutObject:
    """An item box or big ring in an act's object layout."""
    location_name: str
    big_ring: bool


def _build_layouts() -> dict[tuple[int, int], dict[int, LayoutObject]]:
    layouts: dict[tuple[int, int], dict[int, LayoutObject]] = {}
    for (zone, act), act_locs in ACTS.items():
        objects = [
            (index, f'{LOC_NAME_ITEM_BOX} {number}', False)
            for index, number in act_locs.item_boxes.items()
        ] + [
            (index, f'{LOC_NAME_BIG_RING} {number}', True)
            for index, number in act_locs.big_rings.items()
        ]
        for index, loc_name, big_ring in objects:
            layout_act = act + 1 if index in act_locs.next_layout else act
            name = format_display_name(act_locs.zone, act_locs.act, loc_name)
            layouts.setdefault((zone, layout_act), {})[index] = LayoutObject(name, big_ring)
    return layouts


# Keyed by Current_zone_and_act, which says which object layout is loaded.
# This is the same as the ACTS key, except for the burnt part of Angel Island
# act 1. Each value maps the respawn table index to the object.
LAYOUTS: dict[tuple[int, int], dict[int, LayoutObject]] = _build_layouts()


def respawn_marks(zone: int, act: int, location_ids: dict[str, int],
                  checked: typing.Collection[int]) -> dict[int, int]:
    """
    The Archipelago respawn table bits (see S3KMemory.RESPAWN_UNCHECKED_BIT)
    for the item boxes and big rings in the given object layout. zone and act
    are the values from Current_zone_and_act. location_ids maps the names of
    the locations in this slot to their ids, so objects that aren't locations
    in this slot are left out; checked holds the ids of the checked locations.
    The return value maps the respawn index to its bits, and leaves out
    objects that should behave like they do in the vanilla game.
    """
    marks = {}
    for index, obj in LAYOUTS.get((zone, act), {}).items():
        loc_id = location_ids.get(obj.location_name)
        if loc_id is None:
            continue
        if loc_id not in checked:
            marks[index] = RESPAWN_UNCHECKED_BIT
        elif obj.big_ring:
            marks[index] = RESPAWN_CHECKED_BIT
    return marks
