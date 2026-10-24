AP_ITEM_CODES = {
    [1] = "chaos_emerald",
    [2] = "master_emerald",
    [3] = "master_emerald_shard",
    [4] = "char_sonic",
    [5] = "char_tails",
    [6] = "char_knuckles",
    [7] = "zone_angel_island",
    [8] = "zone_hydrocity",
    [9] = "zone_marble_garden",
    [10] = "zone_carnival_night",
    [11] = "zone_ice_cap",
    [12] = "zone_launch_base",
    [13] = "zone_mushroom_hill",
    [14] = "zone_flying_battery",
    [15] = "zone_sandopolis",
    [16] = "zone_lava_reef",
    [17] = "zone_hidden_palace",
    [18] = "zone_sky_sanctuary",
    [19] = "zone_death_egg",
    [20] = "zone_doomsday",
    [21] = "zone_special_stage_1",
    [22] = "zone_special_stage_2",
    [23] = "zone_special_stage_3",
    [24] = "zone_special_stage_4",
    [25] = "zone_special_stage_5",
    [26] = "zone_special_stage_6",
    [27] = "zone_special_stage_7",
    [28] = "zone_special_stage_8",
    [29] = "zone_special_stage_9",
    [30] = "zone_special_stage_10",
    [31] = "zone_special_stage_11",
    [32] = "zone_special_stage_12",
    [33] = "zone_special_stage_13",
    [34] = "zone_special_stage_14",
    [35] = "zone_angel_island_sonic",
    [36] = "zone_hydrocity_sonic",
    [37] = "zone_marble_garden_sonic",
    [38] = "zone_carnival_night_sonic",
    [39] = "zone_ice_cap_sonic",
    [40] = "zone_launch_base_sonic",
    [41] = "zone_mushroom_hill_sonic",
    [42] = "zone_flying_battery_sonic",
    [43] = "zone_sandopolis_sonic",
    [44] = "zone_lava_reef_sonic",
    [45] = "zone_hidden_palace_sonic",
    [46] = "zone_sky_sanctuary_sonic",
    [47] = "zone_death_egg_sonic",
    [48] = "zone_doomsday_sonic",
    [49] = "zone_special_stage_1_sonic",
    [50] = "zone_special_stage_2_sonic",
    [51] = "zone_special_stage_3_sonic",
    [52] = "zone_special_stage_4_sonic",
    [53] = "zone_special_stage_5_sonic",
    [54] = "zone_special_stage_6_sonic",
    [55] = "zone_special_stage_7_sonic",
    [56] = "zone_special_stage_8_sonic",
    [57] = "zone_special_stage_9_sonic",
    [58] = "zone_special_stage_10_sonic",
    [59] = "zone_special_stage_11_sonic",
    [60] = "zone_special_stage_12_sonic",
    [61] = "zone_special_stage_13_sonic",
    [62] = "zone_special_stage_14_sonic",
    [63] = "zone_angel_island_tails",
    [64] = "zone_hydrocity_tails",
    [65] = "zone_marble_garden_tails",
    [66] = "zone_carnival_night_tails",
    [67] = "zone_ice_cap_tails",
    [68] = "zone_launch_base_tails",
    [69] = "zone_mushroom_hill_tails",
    [70] = "zone_flying_battery_tails",
    [71] = "zone_sandopolis_tails",
    [72] = "zone_lava_reef_tails",
    [73] = "zone_hidden_palace_tails",
    [74] = "zone_sky_sanctuary_tails",
    [75] = "zone_death_egg_tails",
    [76] = "zone_special_stage_1_tails",
    [77] = "zone_special_stage_2_tails",
    [78] = "zone_special_stage_3_tails",
    [79] = "zone_special_stage_4_tails",
    [80] = "zone_special_stage_5_tails",
    [81] = "zone_special_stage_6_tails",
    [82] = "zone_special_stage_7_tails",
    [83] = "zone_special_stage_8_tails",
    [84] = "zone_special_stage_9_tails",
    [85] = "zone_special_stage_10_tails",
    [86] = "zone_special_stage_11_tails",
    [87] = "zone_special_stage_12_tails",
    [88] = "zone_special_stage_13_tails",
    [89] = "zone_special_stage_14_tails",
    [90] = "zone_angel_island_knuckles",
    [91] = "zone_hydrocity_knuckles",
    [92] = "zone_marble_garden_knuckles",
    [93] = "zone_carnival_night_knuckles",
    [94] = "zone_ice_cap_knuckles",
    [95] = "zone_launch_base_knuckles",
    [96] = "zone_mushroom_hill_knuckles",
    [97] = "zone_flying_battery_knuckles",
    [98] = "zone_sandopolis_knuckles",
    [99] = "zone_lava_reef_knuckles",
    [100] = "zone_hidden_palace_knuckles",
    [101] = "zone_knuckles_sky_sanctuary_knuckles",
    [102] = "zone_special_stage_1_knuckles",
    [103] = "zone_special_stage_2_knuckles",
    [104] = "zone_special_stage_3_knuckles",
    [105] = "zone_special_stage_4_knuckles",
    [106] = "zone_special_stage_5_knuckles",
    [107] = "zone_special_stage_6_knuckles",
    [108] = "zone_special_stage_7_knuckles",
    [109] = "zone_special_stage_8_knuckles",
    [110] = "zone_special_stage_9_knuckles",
    [111] = "zone_special_stage_10_knuckles",
    [112] = "zone_special_stage_11_knuckles",
    [113] = "zone_special_stage_12_knuckles",
    [114] = "zone_special_stage_13_knuckles",
    [115] = "zone_special_stage_14_knuckles",
}

-- Index of the last received item that was applied. Archipelago resends every
-- item on reconnect, starting from index 0.
local current_index = -1

-- Every tracker item code that Archipelago items map to
local AP_CODES = {}
for _, code in pairs(AP_ITEM_CODES) do
    AP_CODES[code] = true
end

local function reset_item(code)
    local item = Tracker:FindObjectForCode(code)
    if item == nil then
        return
    end
    if item.Type == "toggle" then
        item.Active = false
    elseif item.Type == "consumable" then
        item.AcquiredCount = 0
    end
end

local function set_stage(code, value)
    local item = Tracker:FindObjectForCode(code)
    if item ~= nil and type(value) == "number" then
        item.CurrentStage = value
    end
end

local function apply_slot_data(slot_data)
    set_stage("setting_zone_unlocks_all", slot_data.zone_unlocks)
    set_stage("setting_big_rings_goal_none", slot_data.big_rings_goal)
    set_stage("setting_chaos_emeralds_goal_none", slot_data.chaos_emeralds_goal)
    set_stage("setting_super_emeralds_goal_none", slot_data.super_emeralds_goal)
    if type(slot_data.big_rings_to_check) == "number" then
        Tracker:FindObjectForCode("setting_big_rings_to_check").AcquiredCount = slot_data.big_rings_to_check
    end
    -- Not sent by the apworld yet; set "Hard Logic" by hand until it is
    if type(slot_data.logic_difficulty) == "number" then
        Tracker:FindObjectForCode("setting_hard_logic").Active = slot_data.logic_difficulty == 1
    end
end

local function set_checked(location_id)
    local loc = LOCATIONS_BY_ID[location_id]
    if loc == nil then
        return
    end
    local section = Tracker:FindObjectForCode(loc.section)
    if section ~= nil then
        section.AvailableChestCount = 0
    end
end

local function on_clear(slot_data)
    current_index = -1
    Tracker.BulkUpdate = true
    local ok, err = pcall(function()
        for code in pairs(AP_CODES) do
            reset_item(code)
        end
        for _, loc in ipairs(LOCATIONS) do
            local section = Tracker:FindObjectForCode(loc.section)
            if section ~= nil then
                section.AvailableChestCount = section.ChestCount
                section.Highlight = Highlight.None
            end
        end
        apply_slot_data(slot_data or {})

        -- Only the locations the server knows about are part of this seed
        LOCATIONS_IN_SEED = {}
        for _, id in ipairs(Archipelago.MissingLocations or {}) do
            LOCATIONS_IN_SEED[id] = true
        end
        for _, id in ipairs(Archipelago.CheckedLocations or {}) do
            LOCATIONS_IN_SEED[id] = true
            set_checked(id)
        end
    end)
    Tracker.BulkUpdate = false
    if not ok then
        print("S3K: error while resetting tracker: " .. tostring(err))
    end
    mark_location_list_dirty()
end

local function on_item(index, item_id, item_name, player_number)
    if index <= current_index then
        return
    end
    current_index = index
    local code = AP_ITEM_CODES[item_id]
    if code == nil then
        return
    end
    local item = Tracker:FindObjectForCode(code)
    if item == nil then
        return
    end
    if item.Type == "toggle" then
        item.Active = true
    elseif item.Type == "consumable" then
        item.AcquiredCount = item.AcquiredCount + item.Increment
    end
end

local function on_location(location_id, location_name)
    set_checked(location_id)
    mark_location_list_dirty()
end

Archipelago:AddClearHandler("s3k_clear", on_clear)
Archipelago:AddItemHandler("s3k_item", on_item)
Archipelago:AddLocationHandler("s3k_location", on_location)
