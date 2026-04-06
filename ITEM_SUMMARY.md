# Chaos Emeralds

The Chaos Emeralds are added as items into the item pool when either the
`chaos_emeralds` or `super_emeralds` goal is specified in the game
configuration. Using a `chaos_emeralds` goal without a `super_emeralds`
goal adds the following item names to the item pool:

- White Chaos Emerald
- Red Chaos Emerald
- Cyan Chaos Emerald
- Purple Chaos Emerald
- Green Chaos Emerald
- Yellow Chaos Emerald
- Blue Chaos Emerald


With a `super_emeralds` goal, the chaos emeralds are added to the item pool
as progressive items with the following names:

- Progressive White Chaos Emerald
- Progressive Red Chaos Emerald
- Progressive Cyan Chaos Emerald
- Progressive Purple Chaos Emerald
- Progressive Green Chaos Emerald
- Progressive Yellow Chaos Emerald
- Progressive Blue Chaos Emerald

For example the first "Progressive White Chaos Emerald" will give the white
chaos emerald, while the second will give the white super emerald. This
ensures that the chaos emerald is always found before the super emerald,
and that the progression of finding each emerald is independent of the
others.

# Level and Character Items

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
