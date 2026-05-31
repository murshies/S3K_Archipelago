from invoke import task
import json
import jsonschema
import io
import os
import pathlib
import textwrap
import yaml

import items
import locations


@task
def location_summary(c):
    types = locations.LocationTypeSet.from_file(
        pathlib.Path('.') / 'apworld' / 'locations' / 'types.yaml')
    base_dir = pathlib.Path('.') / 'apworld' / 'locations'
    location_def_files = [
        base_dir / f for f in os.listdir(base_dir)
        if f.endswith('.yaml') and f != 'types.yaml'
    ]
    location_set = locations.LocationSet.from_files(location_def_files, types)
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
        matching = location_set.filter_locations(
            lambda p, ts: location_type in ts.types_for(p.location_type)
        )
        doc.write(f'|{location_display}|{len(matching)}|\n')
    doc.write(f'|Total|{len(location_set.all_locations)}|\n')

    doc.write('# Items Per Zone\n')
    doc.write('| Zone | Location Type | Count |\n')
    doc.write('|-|-|-|\n')
    for zone in locations.ZONE_ORDER:
        for location_type, location_display in zone_location_order:
            matching = location_set.filter_locations(
                lambda p, ts: location_type in ts.types_for(p.location_type),
                lambda p, ts: zone == p.zone
            )
            if len(matching) > 0:
                doc.write(f'|{zone}|{location_display}|{len(matching)}|\n')
        # Then get the total number of locations for the zone
        zone_matching = location_set.filter_locations(
            lambda p, ts: zone == p.zone
        )
        doc.write(f'|{zone}|Total|{len(zone_matching)}|\n')

    with open('LOCATION_SUMMARY.md', 'w') as f:
        doc.seek(0)
        f.write(doc.read())


@task
def item_summary(c):
    item_yaml_filename = pathlib.Path('.') / 'apworld' / 'items.yaml'
    item_set = items.ItemSet.from_file(item_yaml_filename)

    doc = io.StringIO()

    doc.write('# Chaos Emeralds\n')
    doc.write(textwrap.dedent('''
    The Chaos Emeralds are added as items into the item pool when either the
    `chaos_emeralds` or `super_emeralds` goal is specified in the game
    configuration. There are not individual chaos emerald/super emerald items
    per color. Instead, a number of generic "Chaos Emerald" items are added to
    the item pool, depending on player's settings. Finding the required number
    of emeralds per goal will unlock
    '''))
    doc.write('\n')

    doc.write('# Level and Character Items\n')
    doc.write(textwrap.dedent('''
    Depending on the value of the `zone_unlocks` game configuration, characters
    and levels can be added to the item pool. There are four options:

    1. `all_unlocked` adds no zone or character items to the pool. All stages
       and characters are unlocked from the start.
    2. `zones_and_characters` adds an zone unlock *per character*. For example,
       there will be three separate items in the pool for unlocking Angel
       Island Zone: one for Sonic, one for Tails, and one for Knuckles.
    3. `zones_only` adds one unlock per zone. Once that zone is unlocked, it is
       available to all characters.
    4. `characters_only` adds one unlock per character. Once a character is
       unlocked, all zones are available to that character.
    '''))
    doc.write('\n')

    doc.write('# Junk/Filler Items\n')
    doc.write(textwrap.dedent('''
    There are also several junk/filler items which will be dispersed throughout
    each game in the generated world:
    '''))
    doc.write('\n')
    junk_items = item_set.filter_items(
        lambda item: item.filler
    )
    for item in junk_items:
        doc.write(f'- {item.name}\n')
    doc.write('\n')

    doc.write('# Traps\n')
    doc.write(textwrap.dedent('''
    There are a currently couple of traps defined in this apworld. There will
    likely be more added after a playable version of the game is complete:
    '''))
    doc.write('\n')
    trap_items = item_set.filter_items(
        lambda item: item.trap
    )
    doc.write('| Name | Description |\n')
    doc.write('|-|-|\n')
    for item in trap_items:
        doc.write(f'| {item.name} | {item.description if item.description else ""}\n')

    with open('ITEM_SUMMARY.md', 'w') as f:
        doc.seek(0)
        f.write(doc.read())


@task
def validate_user_config(c):
    with open('apworld/example.yaml', 'r') as f:
        cfg = yaml.safe_load(f)
    with open('apworld/player-config.schema.json', 'r') as f:
        schema = json.load(f)
    jsonschema.validate(cfg, schema)
    import pprint
    pprint.pprint(cfg)
