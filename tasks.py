from invoke import task
import json
import jsonschema
import io
import os
import pathlib
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
    doc.write('''
    The Chaos Emeralds are added as items into the item pool when either the
    `chaos_emeralds` or `super_emeralds` goal is specified in the game
    configuration. Using a `chaos_emeralds` goal without a `super_emeralds`
    goal adds the following item names to the item pool:
    ''')
    emerald_items = item_set.filter_items(
        lambda item: 'chaos_emerald' in item.groups
    )
    for item in emerald_items:
        doc.write(f'- {item.name}\n')
    doc.write('''
    With a `super_emeralds` goal, the chaos emeralds are added to the item pool
    as progressive items with the following names:
    ''')
    for item in emerald_items:
        doc.write(f'- {item.progressive_name}\n')
    doc.write('''
    For example the first "Progressive White Chaos Emerald" will give the white
    chaos emerald, while the second will give the white super emerald. This
    ensures that the chaos emerald is always found before the super emerald,
    and that the progression of finding each emerald is independent of the
    others.
    ''')
    doc.write('\n')

    with open('ITEM_SUMMARY.md', 'w') as f:
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
