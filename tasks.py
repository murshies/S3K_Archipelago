import bsdiff4
from invoke import task
from invoke.context import Context
import json
import jsonschema
import io
import itertools
import os
import pathlib
import shutil
import textwrap
import yaml
import zipfile

# Using imports directly from the apworld causes this script to need a lot of
# unnecessary libraries installed from the built-in worlds in
# Archipelago. Instead, copy the files needed to this directory and them import
# them.
required_apworld_files = (
    "items.py",
    "locations.py",
)
for req_file in required_apworld_files:
    shutil.copy(str(pathlib.Path(".") / "apworld" / req_file),
                req_file)

import items  # noqa: E402
import locations  # noqa: E402

INVOKE_ROOT = pathlib.Path(__file__).parent


@task
def all(c: Context):
    location_summary(c)
    item_summary(c)
    validate_player_config(c)
    test(c)
    apworld_release(c)  # Note that build_rom_base_diff is called as part of apworld_release


@task
def location_summary(c: Context):
    types = locations.LocationTypeSet.from_file(
        INVOKE_ROOT / 'apworld' / 'locations' / 'types.yaml',
        validator=jsonschema.validate)
    base_dir = INVOKE_ROOT / 'apworld' / 'locations'
    location_def_files = [
        base_dir / f for f in os.listdir(base_dir)
        if f.endswith('.yaml') and f != 'types.yaml'
    ]
    location_set = locations.LocationSet.from_files(
        location_def_files, types, validator=jsonschema.validate)
    zone_location_order = (
        ('complete', 'Act Complete'),
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
    item_set = items.ItemSet.from_file(
        item_yaml_filename, validator=jsonschema.validate)

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
              env={'PYTHONPATH': str(archipelago_root)})


@task
def build_rom_base_diff(c: Context):
    disasm_root = INVOKE_ROOT / "submodules" / "skdisasm"
    try:
        cwd = os.getcwd()
        os.chdir(str(disasm_root))
        # The skdisasm repo does contain a single script to build a Sonic 3 &
        # Knuckles ROM with a single command. However, this is not a byte
        # perfect build, which is needed here in order to create the base patch
        # file correctly. Instead, the commands for building the individual
        # ROMs do create byte perfect builds (other than the intended
        # modifications), and will generate a combined ROM that is the exact
        # same size as the unmodified base ROM.
        if os.name == "nt":
            c.run("buildS3.bat")
            c.run("buildSK.bat")
        else:
            c.run("./buildS3.lua")
            c.run("./buildSK.lua")
        with open("s3built.bin", "rb") as f:
            s3_rom = f.read()
        with open("skbuilt.bin", "rb") as f:
            sk_rom = f.read()
        # Combine the two ROMs in memory. Note that it is important that the
        # Sonic & Knuckles ROM comes before the Sonic 3 ROM.
        s3k_modded_rom = sk_rom + s3_rom
    finally:
        os.chdir(cwd)

    s3k_base_rom_file = INVOKE_ROOT / "S3K_base.md"
    with open(s3k_base_rom_file, "rb") as f:
        s3k_base_rom = f.read()

    if len(s3k_modded_rom) != len(s3k_base_rom):
        raise Exception(f"Found modded ROM length ({len(s3k_modded_rom)}) "
                        f"!= base ROM length ({len(s3k_base_rom)})")

    rom_patch = bsdiff4.diff(s3k_base_rom, s3k_modded_rom)
    patch_file = pathlib.Path(".") / "apworld" / "base_patch.bsdiff4"
    with open(str(patch_file), "wb") as f:
        f.write(rom_patch)


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
    build_rom_base_diff(c)
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
                         pathlib.Path('s3k') / os.path.relpath(full_file_path, apworld_root))


@task
def poptracker_release(c: Context):
    # There are a few files which are essentially apworld information
    # translated into JSON/Lua bindings. Generate those first before building
    # the pack zip file.
    types = locations.LocationTypeSet.from_file(
        INVOKE_ROOT / 'apworld' / 'locations' / 'types.yaml',
        validator=jsonschema.validate)
    base_dir = INVOKE_ROOT / 'apworld' / 'locations'
    location_def_files = [
        base_dir / f for f in sorted(os.listdir(base_dir))
        if f.endswith('.yaml') and f != 'types.yaml'
    ]
    location_set = locations.LocationSet.from_files(
        location_def_files, types, validator=jsonschema.validate)
    locs_path = INVOKE_ROOT / 'poptracker' / 'locations'
    shutil.rmtree(locs_path)
    os.makedirs(locs_path)
    with open(INVOKE_ROOT / 'poptracker' / 'tracker_base.json') as tracker_base:
        tracker = json.load(tracker_base)
    lua_defs = []
    for zone, abbrev in locations.ZONE_ABBREVS.items():
        print(f'Iterating on {zone} {abbrev}')
        # Lava Reef boss is technically act 3, so look for act 3 locations
        # too. Some zones like Sky Sanctuary do not have an act at all.
        for act in [None, 1, 2, 3]:
            # Things like act complete and bosses
            act_locs = location_set.filter_locations(
                lambda p, ts: (
                    zone == p.zone and
                    act == p.act and
                    ('boss' in ts.types_for(p.location_type) or
                     'complete' in ts.types_for(p.location_type) or
                     'emerald' in ts.types_for(p.location_type))
                )
            )
            item_box_locs = location_set.filter_locations(
                lambda p, ts: (
                    zone == p.zone and
                    act == p.act and
                    'item_box' in ts.types_for(p.location_type)
                )
            )
            big_ring_locs = location_set.filter_locations(
                lambda p, ts: (
                    zone == p.zone and
                    act == p.act and
                    'big_ring' in ts.types_for(p.location_type)
                )
            )
            if len(act_locs) == 0:
                # No completes or bosses or emeralds, skip it.
                continue
            # Generate the groupings per item type for the tracker layout.

            def gen_group_layout(locs, header, max_per_row=5):
                return {
                    'type': 'group',
                    'header': header,
                    'content': {
                        'type': 'itemgrid',
                        'item_margin': '2,2',
                        'item_size': 32,
                        'h_alignment': 'left',
                        'rows': [
                            [f'loc_{loc.location_id}' for loc in batch]
                            for batch in itertools.batched(locs, max_per_row)
                        ]
                    }
                }
            act_locs_layout = gen_group_layout(act_locs, 'Act')
            big_rings_locs_layout = gen_group_layout(big_ring_locs, 'Big Rings')
            item_box_locs_layout = gen_group_layout(item_box_locs, 'Item Boxes')
            act_abbrev = abbrev
            if act is not None:
                act_abbrev = f'{abbrev}{act}'
            if 'Special Stage' not in zone:
                content = []
                if len(act_locs) > 0:
                    content.append(act_locs_layout)
                if len(big_ring_locs) > 0:
                    content.append(big_rings_locs_layout)
                if len(item_box_locs) > 0:
                    content.append(item_box_locs_layout)
                content += [
                    {
                        'type': 'text',
                        'text': 'Left click: highlight on map'
                    },
                    {
                        'type': 'text',
                        'text': 'Right click: mark as checked'
                    },
                    {
                        'type': 'text',
                        'text': 'Middle click: reset highlighting'
                    }
                ]
                act_tracker_data = {
                    'title': f'{abbrev}{act}' if act is not None else abbrev,
                    'content': {
                        'type': 'dock',
                        'content': [
                            {
                                'type': 'array',
                                'dock': 'left',
                                'orientation': 'vertical',
                                'margin': '2,2',
                                'max_width': 240,
                                'v_alignment': 'top',
                                'content': content
                            },
                            {
                                'type': 'group',
                                'header': f'{zone} Act {act}' if act is not None else zone,
                                'content': {
                                    'type': 'map',
                                    'maps': [
                                        'special' if 'Special Stage' in zone else act_abbrev
                                    ]
                                }
                            }
                        ]
                    }
                }
                tracker['tracker_default']['content'][1]['tabs'].append(act_tracker_data)

            full_act_locs = location_set.filter_locations(
                lambda p, ts: zone == p.zone and act == p.act
            )
            act_loc_data = []
            for loc in full_act_locs:
                entry = {
                    'name': loc.display_name,
                    'access_rules': [
                        f'^$s3k_access|{loc.location_id}'
                    ],
                    'visibility_rules': [
                        f'$s3k_in_seed|{loc.location_id}'
                    ],
                    'chest_unopened_img': f'images/locations/{loc.location_type}.png',
                    'chest_opened_img': f'images/locations/{loc.location_type}.png',
                    'sections': [
                        {
                            'name': loc.location_type,
                            'item_count': 1
                        }
                    ]
                }
                if loc.poptracker_info is not None:
                    entry['map_locations'] = [
                        {
                            'map': 'special' if 'Special Stage' in zone else act_abbrev,
                            'x': loc.poptracker_info.x,
                            'y': loc.poptracker_info.y,
                            # 'size': 127,
                        }
                    ]
                act_loc_data.append(entry)
                lua_defs.append(loc.lua)

            act_loc_file = INVOKE_ROOT / 'poptracker' / 'locations' / f'{act_abbrev.lower()}.json'
            print(f'Writing {act_loc_file}')
            with open(act_loc_file, 'a') as f:
                json.dump(act_loc_data, f, indent=2)

            lua_struct_file = INVOKE_ROOT / 'poptracker' / 'scripts' / 'structure.lua'
    with open(lua_struct_file, 'w') as f:
        f.write('LOCATIONS = {\n')
        f.write(','.join(lua_defs))
        f.write('\n}')

    with open(INVOKE_ROOT / 'poptracker' / 'tracker.json', 'w') as tracker_out:
        json.dump(tracker, tracker_out, indent=2)

    # Finally, build the pack by zipping the poptracker directory

    poptracker_root = INVOKE_ROOT / 'poptracker'
    out_file = INVOKE_ROOT / 'build' / 's3k_poptracker.zip'
    if os.path.exists(out_file):
        os.remove(out_file)
    with zipfile.ZipFile(out_file, 'w') as zf:
        for root, dirs, files, in os.walk(poptracker_root):
            for f in files:
                full_file_path = pathlib.Path(root) / f
                zf.write(full_file_path,
                         os.path.relpath(full_file_path, poptracker_root))
