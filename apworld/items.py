# This file contains information for parsing and accessing items (things that
# can be obtained during a game).

from dataclasses import dataclass
import jsonschema
import typing
import yaml

ITEM_GROUP_CHAOS_EMERALD = 'chaos_emerald'
ITEM_GROUP_CHARACTER = 'character'
ITEM_GROUP_GOAL = 'goal'
ITEM_GROUP_ITEM_BOX = 'item_box'
ITEM_GROUP_LEVEL = 'level'
ITEM_GROUP_MULTIGOAL = 'multigoal'

ITEM_GROUPS = (
    ITEM_GROUP_CHAOS_EMERALD,
    ITEM_GROUP_CHARACTER,
    ITEM_GROUP_GOAL,
    ITEM_GROUP_ITEM_BOX,
    ITEM_GROUP_LEVEL,
    ITEM_GROUP_MULTIGOAL,
)


@dataclass
class Item:
    name: str
    code: int
    description: typing.Optional[str]
    groups: list[str]
    progression: bool
    filler: bool
    trap: bool


class ItemSet:
    _items: dict[str, Item]

    def __init__(self, items: dict[str, Item]) -> typing.Self:
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
                    'description': {
                        'type': ['string', 'null'],
                        'default': None,
                    },
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
        items = {}
        code = 1
        for entry in data:
            items[entry['name']] = Item(
                name=entry['name'],
                code=code,
                description=entry.get('description'),
                groups=entry['groups'],
                progression=entry.get('progression', False),
                filler=entry.get('filler', False),
                trap=entry.get('trap', False)
            )
            code += 1
        return ItemSet(items)

    @property
    def all_items(self) -> list[Item]:
        return list(self._items.values())

    def filter_items(self, *filters: list[typing.Callable]) -> list[Item]:
        return [
            item
            for item in self._items.values()
            if all(filt(item) for filt in filters)
        ]

    def item_with_name(self, item_name: str) -> Item:
        return self._items[item_name]
