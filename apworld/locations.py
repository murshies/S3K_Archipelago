# This file contains information for parsing and accessing location (places
# that players could potentially look for items) information.

from dataclasses import dataclass
import jsonschema
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
    'Special Stage'
)


class InvalidLocationType(Exception):
    type_name: str
    valid_types: set[str]

    def __init__(self, type_name: str, valid_types: set[str]) -> typing.Self:
        self.type_name = type_name
        self.valid_types = valid_types

    def __str__(self) -> str:
        return f'"{self.type_name}" is not valid. Valid types are: {self.valid_types}'


class LocationTypeSet:
    _location_types: dict[str, list[str]]

    def __init__(self, location_types: dict[str, list[str]]) -> typing.Self:
        self._location_types = location_types

    @staticmethod
    def from_file(filename: str) -> typing.Self:
        file_schema = {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': 'https://github.com/murshies/S3K_Archipelago/types.schema.json',
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
        with open(filename) as f:
            data = yaml.safe_load(f)
            jsonschema.validate(data, file_schema)
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

    @property
    def display_name(self) -> str:
        if not self.act:
            act_str = ''
        elif self.zone == 'Special Stage':
            act_str = f' {self.act}'
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
    def from_files(filenames: list[str], types: LocationTypeSet) -> typing.Self:
        file_schema = {
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
                                    'type': 'string',
                                    'enum': ['super', 'hyper']
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
        locations = []
        for filename in filenames:
            with open(filename) as f:
                data = yaml.safe_load(f)
                jsonschema.validate(data, file_schema)
            for entry in data:
                locations.append(Location(
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
                    ]
                ))
        return LocationSet(locations, types)

    @property
    def all_locations(self) -> list[Location]:
        return self._locations

    def filter_items(self, *filters: list[typing.Callable]) -> list[Location]:
        return [
            location
            for location in self._locations
            if all(filt(location, self._types) for filt in filters)
        ]
