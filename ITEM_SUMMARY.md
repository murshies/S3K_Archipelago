# Chaos Emeralds

The Chaos Emeralds are added as items into the item pool when either the
`chaos_emeralds` or `super_emeralds` goal is specified in the game
configuration. There are not individual chaos emerald/super emerald items
per color. Instead, a number of generic "Chaos Emerald" items are added to
the item pool, depending on player's settings. Finding the required number
of emeralds per goal will unlock

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

# Junk/Filler Items

There are also several junk/filler items which will be dispersed throughout
each game in the generated world:

- Lightning Shield
- Flame Shield
- Water Shield
- Invincibility
- Power Sneakers

# Traps

There are a currently couple of traps defined in this apworld. There will
likely be more added after a playable version of the game is complete:

| Name | Description |
|-|-|
| Robotnik Trap | Causes the player to lose all of their rings
| Poison Trap | Causes the player to lose rings over a period of time
