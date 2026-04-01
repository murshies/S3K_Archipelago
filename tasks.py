from dataclasses import dataclass
from invoke import task
import json
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


@task
def location_summary(c):
    types = LocationTypeSet.from_file(os.path.join('apworld', 'locations', 'types.yaml'))
    base_dir = os.path.join('apworld', 'locations')
    location_def_files = [
        os.path.join(base_dir, f) for f in os.listdir(base_dir)
        if f.endswith('.yaml') and f != 'types.yaml'
    ]
    location_set = LocationSet.from_files(location_def_files, types)
    zone_location_order = (
        ('big_ring', 'Big Ring'),
        ('boss', 'Boss'),
        ('1_up', '1 UP'),
        ('super_ring', 'Super Ring (10 rings)'),
        ('lightning_shield', 'Lightning Shield'),
        ('flame_shield', 'Flame Shield'),
        ('water_shield', 'Water Shield'),
        ('shield', 'All Shields'),
        ('invincibility', 'Invincibility'),
        ('robotnik', 'Robotnik Item Box'),
        ('power_sneakers', 'Power Sneakers'),
        ('item_box', 'Total Item Boxes'),
        ('emerald', 'Special Stage Emerald'),
        ('special_stage_perfect', 'Special Stage Perfect')
    )
    doc = io.StringIO()

    doc.write('# Total Item Counts\n')
    doc.write('| Location Type | Count |\n')
    doc.write('|-|-|\n')
    for location_type, location_display in zone_location_order:
        matching = location_set.filter_items(
            lambda p, ts: location_type in ts.types_for(p.location_type)
        )
        doc.write(f'|{location_display}|{len(matching)}|\n')
    doc.write(f'|Total|{len(location_set.all_locations)}|\n')

    doc.write('# Items Per Zone\n')
    doc.write('| Zone | Location Type | Count |\n')
    doc.write('|-|-|-|\n')
    for zone in ZONE_ORDER:
        for location_type, location_display in zone_location_order:
            matching = location_set.filter_items(
                lambda p, ts: location_type in ts.types_for(p.location_type),
                lambda p, ts: zone == p.zone
            )
            if len(matching) > 0:
                doc.write(f'|{zone}|{location_display}|{len(matching)}|\n')
        # Then get the total number of locations for the zone
        zone_matching = location_set.filter_items(
            lambda p, ts: zone == p.zone
        )
        doc.write(f'|{zone}|Total|{len(zone_matching)}|\n')

    with open('LOCATION_SUMMARY.md', 'w') as f:
        doc.seek(0)
        f.write(doc.read())


@task
def validate_user_config(c):
    with open('apworld/example.yaml', 'r') as f:
        cfg = yaml.safe_load(f)
    with open('apworld/user-config.schema.json', 'r') as f:
        schema = json.load(f)
    jsonschema.validate(cfg, schema)
    import pprint
    pprint.pprint(cfg)
