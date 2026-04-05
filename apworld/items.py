# This file contains information for parsing and accessing items (things that
# can be obtained during a game).

from dataclasses import dataclass
import jsonschema
import typing
import yaml

ITEM_GROUPS = (
    'chaos_emerald',
    'character',
    'goal',
    'item_box',
    'level',
)


@dataclass
class Item:
    name: str
    groups: list[str]
    progression: bool
    filler: bool
    trap: bool


class ItemSet:
    _items: list[Item]

    def __init__(self, items: list[Item]) -> typing.Self:
        self._items = items

    @staticmethod
    def from_file(filename: str) -> typing.Self:
        file_schema = {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': 'https://github.com/murshies/S3K_Archipelago/apworld/items.schema.json',
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'progressive_name': {'type': 'string'},
                    'groups': {
                        'type': 'array',
                        'items': {
                            'type': 'string',
                            'enum': list(ITEM_GROUPS)
                        }
                    },
                    'progression': {
                        'type': 'boolean',
                        'default': False
                    },
                    'filler': {
                        'type': 'boolean',
                        'default': False
                    },
                    'trap': {
                        'type': 'boolean',
                        'default': False
                    }
                },
                'required': ['name', 'groups'],
                'additionalProperties': False
            }
        }
        with open(filename, 'r') as f:
            data = yaml.safe_load(f)
            jsonschema.validate(data, file_schema)
        items = []
        for entry in data:
            items.append(Item(
                name=entry['name'],
                groups=entry['groups'],
                progression=entry.get('progression', False),
                filler=entry.get('filler', False),
                trap=entry.get('trap', False)
            ))
        return ItemSet(items)

    @property
    def all_items(self) -> list[Item]:
        return self._items

    def filter_items(self, *filters: list[typing.Callable]) -> list[Item]:
        return [
            item
            for item in self._items
            if all(filt(item) for filt in filters)
        ]
