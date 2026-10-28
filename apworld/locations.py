# This file contains information for parsing and accessing location (places
# that players could potentially look for items) information.

from dataclasses import dataclass
import importlib.resources
import typing
import yaml

ZONE_ORDER = (
    'Angel Island',
    'Hydrocity',
    'Marble Garden',
    'Carnival Night',
    'Ice Cap',
    'Launch Base',
    'Mushroom Hill',
    'Flying Battery',
    'Sandopolis',
    'Lava Reef',
    'Hidden Palace',
    'Sky Sanctuary',
    'Knuckles Sky Sanctuary',
    'Death Egg',
    'Doomsday',
    'Special Stage 1',
    'Special Stage 2',
    'Special Stage 3',
    'Special Stage 4',
    'Special Stage 5',
    'Special Stage 6',
    'Special Stage 7',
    'Special Stage 8',
    'Special Stage 9',
    'Special Stage 10',
    'Special Stage 11',
    'Special Stage 12',
    'Special Stage 13',
    'Special Stage 14',
)

ZONE_ABBREVS = {
    'Angel Island': 'AIZ',
    'Hydrocity': 'HCZ',
    'Marble Garden': 'MGZ',
    'Carnival Night': 'CNZ',
    'Ice Cap': 'ICZ',
    'Launch Base': 'LBZ',
    'Mushroom Hill': 'MHZ',
    'Flying Battery': 'FBZ',
    'Sandopolis': 'SZ',
    'Lava Reef': 'LRZ',
    'Hidden Palace': 'HPZ',
    'Sky Sanctuary': 'SSZ',
    'Knuckles Sky Sanctuary': 'KSSZ',
    'Death Egg': 'DEZ',
    'Doomsday': 'DDZ',
    'Special Stage 1': 'SS1',
    'Special Stage 2': 'SS2',
    'Special Stage 3': 'SS3',
    'Special Stage 4': 'SS4',
    'Special Stage 5': 'SS5',
    'Special Stage 6': 'SS6',
    'Special Stage 7': 'SS7',
    'Special Stage 8': 'SS8',
    'Special Stage 9': 'SS9',
    'Special Stage 10': 'SS10',
    'Special Stage 11': 'SS11',
    'Special Stage 12': 'SS12',
    'Special Stage 13': 'SS13',
    'Special Stage 14': 'SS14',
}

ANGEL_ISLAND_1_APPARENT_ACT_2: set[int] = {49, 79, 121, 134, 133, 19}


class InvalidLocationType(Exception):
    type_name: str
    valid_types: set[str]

    def __init__(self, type_name: str, valid_types: set[str]) -> typing.Self:
        self.type_name = type_name
        self.valid_types = valid_types

    def __str__(self) -> str:
        return f'"{self.type_name}" is not valid. Valid types are: {self.valid_types}'


class DuplicateLocation(Exception):
    loc_name: str

    def __init__(self, loc_name: str) -> typing.Self:
        self.loc_name = loc_name

    def __str__(self) -> str:
        return f'Duplicate location "{self.loc_name}"'


class LocationTypeSet:
    _location_types: dict[str, list[str]]

    def __init__(self, location_types: dict[str, list[str]]) -> typing.Self:
        self._location_types = location_types

    @staticmethod
    def from_file(filename: str, validator: typing.Callable = None) -> typing.Self:
        with open(filename, 'r') as f:
            data = yaml.safe_load(f)
            if validator is not None:
                file_schema = {
                    '$schema': 'https://json-schema.org/draft/2020-12/schema',
                    '$id': 'https://github.com/murshies/S3K_Archipelago/apworld/types.schema.json',
                    'title': 'Schema for the location type definitions in apworld/locations/types.yaml',
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'is': {
                                'type': 'array',
                                'items': {
                                    'type': 'string'
                                }
                            }
                        },
                        'required': ['name', 'is'],
                        'additionalProperties': False
                    }
                }
                validator(data, file_schema)
        location_types = {}
        for entry in data:
            location_types[entry['name']] = entry['is']
        return LocationTypeSet(location_types)

    @property
    def all_type_names(self) -> set[str]:
        return set(self._location_types.keys())

    def types_for(self, type_name: str) -> set[str]:
        if type_name not in self._location_types:
            raise InvalidLocationType(type_name, self.all_type_names)
        types = {type_name}
        for subtype_name in self._location_types[type_name]:
            types.add(subtype_name)
            types |= self.types_for(subtype_name)
        return types


@dataclass
class LocationRequirement:
    character: str
    super_state: str
    difficulty: str

    @property
    def lua(self) -> str:
        """
        Export this LocationRequirement to a lua structure.

        This is used to build the PopTracker pack.
        """
        fields = []
        if self.character:
            fields.append(f'char = \"{self.character}\"')
        if self.super_state:
            fields.append(f'super_state = \"{self.super_state}\"')
        if self.difficulty and self.difficulty == 'hard':
            fields.append('hard = true')
        return '{' + ', '.join(fields) + '}'


@dataclass
class PopTrackerInfo:
    x: int
    y: int


@dataclass
class Location:
    name: str
    zone: str
    act: typing.Optional[int]
    location_type: str
    obj_id: int
    requirements: list[LocationRequirement]
    location_id: int
    poptracker_info: typing.Optional[PopTrackerInfo]

    @property
    def display_name(self) -> str:
        return format_display_name(self.zone, self.act, self.name)

    @property
    def lua(self) -> str:
        """
        Export this Location to a lua structure.

        This is used to build the PopTracker pack.
        """
        act_str = f'act = {self.act},' if self.act is not None else ''
        loc_number = ''
        try:
            loc_number = int(self.name.split(' ')[-1])
        except ValueError:
            # No number for this location - use a blank string
            pass
        loc_map = 'special' if 'Special Stage' in self.zone else ZONE_ABBREVS[self.zone]
        if self.act is not None:
            loc_map += str(self.act)
        x_coords = ''
        y_coords = ''
        if self.poptracker_info is not None:
            x_coords = f'x = {self.poptracker_info.x},'
            y_coords = f'y = {self.poptracker_info.y},'
        lua_reqs = ', '.join([req.lua for req in self.requirements])
        return f'''{{
            id = {self.location_id},
            name = "{self.display_name}",
            short_name = "{self.name}",
            zone = "{self.zone}",
            {act_str}
            type = "{self.location_type}",
            section = "@{self.display_name}/{self.location_type}",
            icon = "images/locations/{self.location_type}.png",
            number = \"{loc_number}\",
            map = \"{loc_map}\",
            {x_coords}
            {y_coords}
            requirements = {{ {lua_reqs} }}
        }}'''


def format_display_name(zone: str, act: typing.Optional[int], name: str) -> str:
    """
    Builds the name Archipelago uses for a location, e.g. "Hydrocity Act 1 -
    Item Box 3".
    """
    if not act:
        act_str = ''
    else:
        act_str = f' Act {act}'
    return f'{zone}{act_str} - {name}'


class LocationSet:
    _locations: list[Location]
    _types: LocationTypeSet
    _by_id: dict[int, Location]

    def __init__(self, locations: list[Location], types: LocationTypeSet) -> typing.Self:
        self._locations = locations
        self._types = types
        self._by_id = {}
        for loc in locations:
            self._by_id[loc.location_id] = loc

    def by_id(self, location_id: int) -> typing.Optional[Location]:
        if location_id not in self._by_id:
            return None
        return self._by_id[location_id]

    @staticmethod
    def from_files(
            filenames: list[str],
            types: LocationTypeSet,
            validator: typing.Callable = None,
    ) -> typing.Self:
        defs = []
        for filename in filenames:
            with open(filename, 'r') as f:
                defs += yaml.safe_load(f)
        return LocationSet.from_definitions(defs, types, validator)

    @staticmethod
    def from_definitions(
            defs: list[dict],
            types: LocationTypeSet,
            validator: typing.Callable = None,
    ) -> typing.Self:
        locations = []
        id_counter = 1
        loc_name_cache: set[str] = set()
        if validator is not None:
            schema = {
                '$schema': 'https://json-schema.org/draft/2020-12/schema',
                '$id': 'https://github.com/murshies/S3K_Archipelago/locations.schema.json',
                'title': 'Schema for the locations yaml file for a single act',
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'zone': {
                            'type': 'string',
                            'enum': list(ZONE_ORDER)
                        },
                        'act': {
                            'type': ['integer', 'null'],
                            'default': None
                        },
                        'type': {
                            'type': 'string',
                            'enum': list(types.all_type_names)
                        },
                        'obj_id': {
                            'type': 'integer',
                        },
                        'requirements': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'character': {
                                        'type': 'string',
                                        'enum': ['Sonic', 'Tails', 'Knuckles']
                                    },
                                    'super_state': {
                                        'type': ['string', 'null'],
                                        'enum': ['super', 'hyper'],
                                        'default': None,
                                    },
                                    'difficulty': {
                                        'type': 'string',
                                        'enum': ['normal', 'hard']
                                    }
                                },
                                'additionalProperties': False
                            }
                        },
                        'poptracker': {
                            'type': 'object',
                            'properties': {
                                'x': {'type': 'integer'},
                                'y': {'type': 'integer'},
                            },
                            'required': ['x', 'y'],
                            'additionalProperties': False
                        }
                    },
                    'required': ['name', 'zone', 'type', 'requirements'],
                    'additionalProperties': False
                }
            }
            validator(defs, schema)
        for entry in defs:
            loc = Location(
                name=entry['name'],
                zone=entry['zone'],
                act=entry.get('act'),
                location_type=entry['type'],
                obj_id=entry['obj_id'],
                requirements=[
                    LocationRequirement(
                        character=req.get('character'),
                        super_state=req.get('super_state'),
                        difficulty=req.get('difficulty', 'normal'),
                    )
                    for req in entry['requirements']
                ],
                location_id=id_counter,
                poptracker_info=None,
            )
            if 'poptracker' in entry:
                loc.poptracker_info = PopTrackerInfo(
                    entry['poptracker']['x'], entry['poptracker']['y'])
            display_name = loc.display_name
            if display_name in loc_name_cache:
                raise DuplicateLocation(display_name)
            loc_name_cache.add(display_name)
            locations.append(loc)
            id_counter += 1
        return LocationSet(locations, types)

    @property
    def all_locations(self) -> list[Location]:
        return self._locations

    @property
    def types(self) -> LocationTypeSet:
        return self._types

    def filter_locations(self, *filters: list[typing.Callable]) -> list[Location]:
        return [
            location
            for location in self._locations
            if all(filt(location, self._types) for filt in filters)
        ]


def load_location_set() -> LocationSet:
    """
    Loads every location definition. Location ids are assigned in the order the
    definitions are read, so the files are sorted to keep the ids the same no
    matter what order the filesystem lists them in.
    """
    locs_path = importlib.resources.files(__package__) / 'locations'

    loc_types_file = locs_path / 'types.yaml'
    with importlib.resources.as_file(loc_types_file) as types_file:
        loc_types = LocationTypeSet.from_file(types_file)

    loc_defs = []
    for f in sorted(locs_path.iterdir(), key=lambda f: f.name):
        if f.name.endswith('.yaml') and f.name != 'types.yaml':
            with f.open('r', encoding='utf-8') as loc_file:
                loc_defs += yaml.safe_load(loc_file)

    return LocationSet.from_definitions(loc_defs, loc_types)
