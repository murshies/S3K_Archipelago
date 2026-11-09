# Sonic 3 & Knuckles Archipelago

This repo contains the code/assets for playing Sonic 3 & Knuckles in [Archipelago](https://archipelago.gg/). The [releases](https://github.com/murshies/S3K_Archipelago/releases) page has builds for the apworld, as well as releases for a [PopTracker](https://poptracker.github.io/) pack

# Requirements

In order to play this game in Archipelago, you must have:

1. The apworld installed from the releases page linked above
2. A legally obtained Sonic 3 & Knuckles ROM
3. The [BizHawk emulator](https://bizhawk.org/). This game was tested with version 2.10, but other versions will likely work since this game doesn't require any special emulator settings.

The Sonic 3 & Knuckles ROM is just the Sonic & Knuckles ROM with the Sonic 3 ROM appended to the end (the order **does** matter). If you have the individual ROMs, you can concatenate the files to get the ROM needed for this randomizer.

# How This Randomizer Works

There are three main goals that can be enabled:

1. Big Ring Hunt: Collect a number of big rings across each zone, configurable in the player YAML
2. Chaos Emerald Hunt: Find 7 chaos emeralds
3. Super Emerald Hunt: Find all 14 emeralds

To avoid issues with potentially finding a super emerald before the same color chaos emerald, all emeralds are generic "Chaos Emerald" items. This means that doing the Chaos Emerald Hunt goal will add 7 emerald items to the item pool, and the Super Emerald goal will add 14 emerald items to the item pool. If neither emerald hunt goal is enable, no emeralds are added to the item pool. Instead, all super emeralds are given at the start, allowing for the use of super/hyper forms immediately.

The game is not limited to one goal at a time - you can enable 1, 2, or 3 at a time and work towards multiple goals at once. Each goal unlocks a different stage, and beating that stage completes the goal:

1. Death Egg Zone
2. Knuckles Sky Sanctuary Zone
3. Doomsday Zone

The mapping between goals and zones are configurable as well, so you can pick how you want the game to end.

A sample player YAML file can be found in this repo, at [apworld/example.yaml](apworld/example.yaml). The options are:

- `big_rings_goal`: The goal zone for collecting a set number of big rings. This can be `none` (disabled), `death_egg`, `knuckles_sky_sanctuary`, or `doomsday`.
- `big_rings_to_check`: The number of big rings to check to unlock the `big_rings_goal` zone. There are 77 big rings in the game, so this must be between 1 and 77, inclusive.
- `chaos_emeralds_goal`: The goal zone for collecting 7 chaos emeralds. This can be `none` (disabled), `death_egg`, `knuckles_sky_sanctuary`, or `doomsday`.
- `super_emeralds_goal`: The goal zone for collecting all 14 emeralds. This can be `none` (disabled), `death_egg`, `knuckles_sky_sanctuary`, or `doomsday`.
- `death_link`: Turns death link on or off (one player dying with death link enabled kills all other players with death link enabled)
- `logic_difficulty`: The logic difficult (see the Logic Difficulty section below for more info). This can be `standard` or `hard`
- `zone_unlocks`: This determines how zones/characters can be unlocked (see the Zone Unlocks section below). This can be `all_unlocked`, `zones_and_characters`, `zones_only`, or `characters_only`.
- `traps_enabled`: Whether or not trap items are added to the item pool (see the Traps section below for more info).
- `trap_weight_percentage`: The percentage of junk items (shields, invincibility, etc.) that will be traps.
- `enable_boss_locations`: Toggles whether or not beating a miniboss or boss grants an item.
- `enable_big_ring_locations`: Toggles whether or not collecting a big ring grants an item.
- `enable_special_stage_emerald_locations`: Toggles whether or not beating a special stage grants an item.
- `enable_special_stage_perfect_locations`: Toggles whether or not collecting all rings in a special stage grants an item.
- `enable_lightning_shield_locations`: Toggles whether or not breaking a lightning shield monitor grants an item.
- `enable_flame_shield_locations`: Toggles whether or not breaking a flame shield monitor grants an item.
- `enable_water_shield_locations`: Toggles whether or not breaking a water shield monitor grants an item.
- `enable_invincibility_locations`: Toggles whether or not breakng an invincibility monitor grants an item.
- `enable_power_sneaker_locations` Toggles whether or not breaking a power sneakers (speed shoes) monitor grants an item.
- `enable_1_up_locations`: Toggles whether or not breaking a 1 up (extra life) monitor grants an item.
- `enable_super_ring_locations`: Toggles whether or not breaking a super ring (10 ring) monitor grants an item.
- `enable_robotnik_locations`: Toggles whether or not breaking a Robotnik monitor grants an item.

## Special Stages

Since special stages are unlocked like zones, they can no longer be accessed through big rings in the stage. Instead, they are accessible through the save select menu.

## Zone Unlocks

There are a few options for how zones and special stages are unlocked:

1. All Unlocked: The game starts with all zones and special stages unlocked
2. Characters Only: The game starts with all zones and special stages unlocked for a single character, and items are added to the item pool to unlock the other characters
3. Zones Only: The game starts with a single zone unlocked for all characters, and one item per zone is added to the item pool to unlock those
4. Zones and Characters: The game starts with a single zone for a single character, and items per zone, per character are added to the item pool. For example, you can find an "Angel Island - Sonic" item to unlock Angel Island Zone for just Sonic.

## Locations

There are a few types of locations to check in the game:

1. Act Completion
2. Bosses/Minibosses
3. Item Boxes
4. Big Rings
5. Special Stage Perfects
6. Beating a Special Stage

Act completion checks cannot be disabled, but everything else is toggleable. Item boxes can also be enabled or disabled by their individual types as well - for example, you can have just 1 up boxes be a check, while leaving the others disabled. Since the Big Ring Hunt goal involves checking the big rings, they are forced to be enabled when that goal is enabled.

## Logic Difficulty

There are two options for this:

1. Normal: Checks that follow normal gameplay paths are in logic.
2. Hard: Some tricky movement, or backtracking into areas not intended for a character is expected.

There is not currently a difficulty which expects the player to know any glitches.

## Quality of Life Improvements

There are a few things that have been changed in the game:

- Collecting a super emerald after collecting all 7 chaos emeralds no long disables super transformations.
- Super/hyper transformations only trigger when specifically pressing C while jumping, so instashield/flying/gliding can still be used after collecting 50 rings without transforming.
- Pressing C while jumping and in super/hyper form will untransform.
- Pressing A while paused will bring the player back to the save select menu.
- Pressing B while paused will bring the player back to the beginning of the current zone.
- Item boxes that are enabled as checks that have not been collected yet show up as a static monitor, and do not give the regular item on breaking it. If the level is reloaded after breaking it, it reverts back to its normal item.
- When big ring checks are enabled, big rings will not respawn after collecting them, to help show that the location has already been checked. They also do not grant the player 50 rings.

## Traps

There are current two traps implemented:

1. Robotnik Trap: Forces the player to take damage, as if they broke a robotnik item box.
2. Poison Trap: This drains the player of 20 rings one by one, at a rate of one ring every half second.

## Death Link

Death link is implemented for this game.

# Questions?

This game has a thread on the main Archipelago Discord server. It can be found [here](https://discord.com/channels/731205301247803413/1079542502555668601).
