# This file contains information for parsing and accessing location (places
# that players could potentially look for items) information.

from dataclasses import dataclass
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


@dataclass
class Location:
    name: str
    zone: str
    act: typing.Optional[int]
    location_type: str
    requirements: list[LocationRequirement]
    location_id: int

    @property
    def display_name(self) -> str:
        if not self.act:
            act_str = ''
        else:
            act_str = f' Act {self.act}'
        return f'{self.zone}{act_str} - {self.name}'


class LocationSet:
    _locations: list[Location]
    _types: LocationTypeSet

    def __init__(self, locations: list[Location], types: LocationTypeSet) -> typing.Self:
        self._locations = locations
        self._types = types

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
                requirements=[
                    LocationRequirement(
                        character=req.get('character'),
                        super_state=req.get('super_state'),
                        difficulty=req.get('difficulty', 'normal'),
                    )
                    for req in entry['requirements']
                ],
                location_id=id_counter
            )
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
