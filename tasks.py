from dataclasses import dataclass
from invoke import task
import jsonschema
import io
import os
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


class InvalidPickupType(Exception):
    type_name: str
    valid_types: set[str]

    def __init__(self, type_name: str, valid_types: set[str]) -> typing.Self:
        self.type_name = type_name
        self.valid_types = valid_types

    def __str__(self) -> str:
        return f'"{self.type_name}" is not valid. Valid types are: {self.valid_types}'


class PickupTypeSet:
    _pickup_types: dict[str, list[str]]

    def __init__(self, pickup_types: dict[str, list[str]]) -> typing.Self:
        self._pickup_types = pickup_types

    @staticmethod
    def from_file(filename: str) -> typing.Self:
        file_schema = {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': 'https://github.com/murshies/S3K_Archipelago/types.schema.json',
            'title': 'Schema for the pickups type definitions in pickups/types.yaml',
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
        pickup_types = {}
        for entry in data:
            pickup_types[entry['name']] = entry['is']

        return PickupTypeSet(pickup_types)

    @property
    def all_type_names(self) -> set[str]:
        return set(self._pickup_types.keys())

    def types_for(self, type_name: str) -> set[str]:
        if type_name not in self._pickup_types:
            raise InvalidPickupType(type_name, self.all_type_names)
        types = {type_name}
        for subtype_name in self._pickup_types[type_name]:
            types.add(subtype_name)
            types |= self.types_for(subtype_name)
        return types


@dataclass
class PickupRequirement:
    character: str
    super_state: str
    difficulty: str


@dataclass
class Pickup:
    name: str
    zone: str
    act: typing.Optional[int]
    pickup_type: str
    requirements: list[PickupRequirement]

    @property
    def display_name(self) -> str:
        if not self.act:
            act_str = ''
        elif self.zone == 'Special Stage':
            act_str = f' {self.act}'
        else:
            act_str = f' Act {self.act}'
        return f'{self.zone}{act_str} - {self.name}'


class PickupSet:
    _pickups: list[Pickup]
    _types: PickupTypeSet

    def __init__(self, pickups: list[Pickup], types: PickupTypeSet) -> typing.Self:
        self._pickups = pickups
        self._types = types

    @staticmethod
    def from_files(filenames: list[str], types: PickupTypeSet) -> typing.Self:
        file_schema = {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': 'https://github.com/murshies/S3K_Archipelago/pickups.schema.json',
            'title': 'Schema for the pickups yaml file for a single act',
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
        pickups = []
        for filename in filenames:
            with open(filename) as f:
                data = yaml.safe_load(f)
                jsonschema.validate(data, file_schema)
            for entry in data:
                pickups.append(Pickup(
                    name=entry['name'],
                    zone=entry['zone'],
                    act=entry.get('act'),
                    pickup_type=entry['type'],
                    requirements=[
                        PickupRequirement(
                            character=req.get('character'),
                            super_state=req.get('super_state'),
                            difficulty=req.get('difficulty', 'normal'),
                        )
                        for req in entry['requirements']
                    ]
                ))
        return PickupSet(pickups, types)

    def all_with_type(self, type_name: str) -> list[Pickup]:
        return [
            pickup
            for pickup in self._pickups
            if type_name in self._types.types_for(pickup.pickup_type)
        ]


@task
def item_summary(c):
    types = PickupTypeSet.from_file(os.path.join('pickups', 'types.yaml'))
    pickup_def_files = [
        os.path.join('pickups', f) for f in os.listdir('pickups')
        if f.endswith('.yaml') and f != 'types.yaml'
    ]
    import pprint
    pprint.pprint(pickup_def_files)
    pickup_set = PickupSet.from_files(pickup_def_files, types)
    for pickup in pickup_set._pickups:
        print(pickup.display_name)
    print(len(pickup_set._pickups))
    doc = io.StringIO()
    doc.write('# Items Per Zone')
