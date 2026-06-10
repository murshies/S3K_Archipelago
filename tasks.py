from invoke import task
from invoke.context import Context
import json
import jsonschema
import io
import os
import pathlib
import textwrap
import yaml
import zipfile

import items
import locations

INVOKE_ROOT = pathlib.Path(__file__).parent


@task
def all(c: Context):
    location_summary(c)
    item_summary(c)
    validate_player_config(c)
    test(c)
    apworld_release(c)


@task
def location_summary(c: Context):
    types = locations.LocationTypeSet.from_file(
        INVOKE_ROOT / 'apworld' / 'locations' / 'types.yaml')
    base_dir = INVOKE_ROOT / 'apworld' / 'locations'
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

    with open(INVOKE_ROOT / 'LOCATION_SUMMARY.md', 'w') as f:
        doc.seek(0)
        f.write(doc.read())


@task
def item_summary(c: Context):
    item_yaml_filename = INVOKE_ROOT / 'apworld' / 'items.yaml'
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

    with open(INVOKE_ROOT / 'ITEM_SUMMARY.md', 'w') as f:
        doc.seek(0)
        f.write(doc.read())


@task
def validate_player_config(c: Context):
    with open(INVOKE_ROOT / 'apworld' / 'example.yaml') as f:
        cfg = yaml.safe_load(f)
    with open(INVOKE_ROOT / 'apworld' / 'player-config.schema.json', 'r') as f:
        schema = json.load(f)
    jsonschema.validate(cfg, schema)
    import pprint
    pprint.pprint(cfg)


@task
def test(c: Context):
    archipelago_root = INVOKE_ROOT / "submodules" / "Archipelago"
    with c.cd(INVOKE_ROOT / 'apworld'):
        test_root = INVOKE_ROOT / 'apworld' / 'test'
        c.run(f'pytest {test_root}',
              env={'PYTHONPATH': archipelago_root})


@task
def apworld_release(c: Context):
    build_dir = INVOKE_ROOT / 'build'
    os.makedirs(build_dir, exist_ok=True)
    out_file = build_dir / 's3k.apworld'
    if os.path.exists(out_file):
        os.remove(out_file)
    apworld_root = INVOKE_ROOT / 'apworld'
    apworld_ignore_files: set[str] = {
        '__pycache__',
        '.pytest_cache'
    }
    with zipfile.ZipFile(out_file, 'w') as zf:
        for root, dirs, files in os.walk(apworld_root):
            for f in files:
                full_file_path = pathlib.Path(root) / f
                should_ignore = any(
                    ignore in str(full_file_path)
                    for ignore in apworld_ignore_files)
                if should_ignore:
                    continue
                zf.write(full_file_path,
                         os.path.relpath(full_file_path, apworld_root))
