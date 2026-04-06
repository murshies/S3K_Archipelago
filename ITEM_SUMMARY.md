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
    
