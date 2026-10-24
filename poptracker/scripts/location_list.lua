local LOCATE_VIEW_WIDTH = 1800
local LOCATE_VIEW_HEIGHT = 1100
local REFRESH_INTERVAL = 0.25

-- How each state is shown: the icon's image filters, and the badge's
-- background and text colors ("" is PopTracker's default)
local STATE_STYLES = {
    available = {mods = "", background = "#00a000", color = "#ffffff"},
    sequence_break = {mods = "", background = "#e0b000", color = "#000000"},
    unavailable = {mods = "", background = "#c00000", color = "#ffffff"},
    inspect = {mods = "", background = "#2060ff", color = "#ffffff"},
    checked = {mods = "@disabled", background = "#505050", color = "#c0c0c0"},
    not_in_seed = {mods = "brightness|0.35", background = "", color = "#808080"},
}
local HIGHLIGHT_COLOR = "#ffd700"
-- Badge text for checks without a number, so there is something to color
local NO_NUMBER_BADGE = "\u{25CF}"

LOCATION_ITEMS = {}

-- MAP_TABS = {
--     ["HCZ2_1"] = "HCZ2 left half",
--     ["hcz2_2"] = "HCZ2 right half",
--     ["cnz2_1"] = "CNZ2 left half",
--     ["cnz2_2"] = "CNZ2 right half",
--     ["icz1_1"] = "ICZ1 left half",
--     ["icz1_2"] = "ICZ1 right half",
--     ["icz2_1"] = "ICZ2 left half",
--     ["icz2_2"] = "ICZ2 right half",
--     ["lbz2_1"] = "LBZ2 left half",
--     ["lbz2_2"] = "LBZ2 right half",
--     ["mhz1_1"] = "MHZ1 left half",
--     ["mhz1_2"] = "MHZ1 right half",
--     ["mhz2_1"] = "MHZ2 left half",
--     ["mhz2_2"] = "MHZ2 right half",
--     ["sz1_1"] = "SZ1 left half",
--     ["sz1_2"] = "SZ1 right half",
--     ["sz2_1"] = "SZ2 left half",
--     ["sz2_2"] = "SZ2 right half",
-- }

local highlighted = nil
local dirty = true
local since_refresh = 0

function mark_location_list_dirty()
    dirty = true
end

local function section_for(loc)
    return Tracker:FindObjectForCode(loc.section)
end

local function state_for(loc)
    if not s3k_in_seed(loc.id) then
        return "not_in_seed"
    end
    local section = section_for(loc)
    if section == nil then
        return "unavailable"
    end
    if section.AvailableChestCount == 0 then
        return "checked"
    end
    local level = section.AccessibilityLevel
    if level == AccessibilityLevel.Normal or level == AccessibilityLevel.Cleared then
        return "available"
    elseif level == AccessibilityLevel.SequenceBreak then
        return "sequence_break"
    elseif level == AccessibilityLevel.Inspect then
        return "inspect"
    end
    return "unavailable"
end

local function refresh_entry(entry)
    local state = state_for(entry.loc)
    local is_highlighted = highlighted == entry.loc.id
    local key = state .. (is_highlighted and "+highlight" or "")
    if key == entry.style then
        return
    end
    entry.style = key
    local style = STATE_STYLES[state]
    entry.item.IconMods = style.mods
    entry.item:SetOverlayBackground(style.background)
    entry.item:SetOverlayColor(is_highlighted and HIGHLIGHT_COLOR or style.color)
end

function refresh_location_list()
    for _, entry in pairs(LOCATION_ITEMS) do
        refresh_entry(entry)
    end
end

local function set_highlight(loc)
    if highlighted ~= nil then
        local previous = LOCATIONS_BY_ID[highlighted]
        local section = section_for(previous)
        if section ~= nil then
            section.Highlight = Highlight.None
        end
    end
    highlighted = loc and loc.id or nil
    if loc ~= nil then
        local section = section_for(loc)
        if section ~= nil then
            section.Highlight = Highlight.Priority
        end
    end
    dirty = true
end

-- Zooms all of an act's map images back out
-- local function reset_view(act_map)
--     for _, map in ipairs(ACT_MAPS[act_map]) do
--         local size = MAP_SIZES[map]
--         Tracker:UiHint("Zoom " .. map, "1")
--         Tracker:UiHint("Pan " .. map, string.format("%d,%d", size.width // 2, size.height // 2))
--     end
-- end

function locate(loc)
    if loc.map == nil then
        -- This will happen for bosses and act completions
        return
    end
    if highlighted == loc.id then
        -- Clicking the same check again zooms back out
        set_highlight(nil)
        -- reset_view(loc.map)
        return
    end
    -- if MAP_TABS[loc.map] ~= nil then
    --     -- The check is on one half of a split map
    --     Tracker:UiHint("ActivateTab", MAP_TABS[loc.map])
    -- end
    -- local size = MAP_SIZES[loc.map]
    -- local zoom = math.max(1, size.width / LOCATE_VIEW_WIDTH, size.height / LOCATE_VIEW_HEIGHT)
    -- Tracker:UiHint("Zoom " .. loc.map, string.format("%.3f", zoom))
    -- Tracker:UiHint("Pan " .. loc.map, string.format("%d,%d", loc.x, loc.y))
    set_highlight(loc)
end

local function toggle_checked(loc)
    local section = section_for(loc)
    if section == nil then
        return
    end
    if section.AvailableChestCount == 0 then
        section.AvailableChestCount = section.ChestCount
    else
        section.AvailableChestCount = 0
    end
    dirty = true
end

local function create_item(loc)
    local code = "loc_" .. loc.id
    local item = ScriptHost:CreateLuaItem()
    item.Name = loc.short_name
    item.Icon = ImageReference:FromPackRelativePath(loc.icon)
    item.CanProvideCodeFunc = function(self, c)
        return c == code
    end
    item.ProvidesCodeFunc = function(self, c)
        return 0
    end
    item.OnLeftClickFunc = function(self)
        locate(loc)
    end
    item.OnRightClickFunc = function(self)
        toggle_checked(loc)
    end
    item.OnMiddleClickFunc = function(self)
        set_highlight(nil)
        -- reset_view(loc.map)
    end
    item:SetOverlay(loc.number ~= "" and loc.number or NO_NUMBER_BADGE)
    item:SetOverlayFontSize(12)
    LOCATION_ITEMS[loc.id] = {item = item, loc = loc, style = nil}
end

for _, loc in ipairs(LOCATIONS) do
    if loc.map ~= nil then
        create_item(loc)
    end
end

ScriptHost:AddWatchForCode("s3k_location_list", "*", function(code)
    dirty = true
end)
ScriptHost:AddOnLocationSectionChangedHandler("s3k_location_list", function(section)
    dirty = true
end)
ScriptHost:AddOnFrameHandler("s3k_location_list", function(elapsed)
    since_refresh = since_refresh + elapsed
    if dirty and since_refresh >= REFRESH_INTERVAL then
        dirty = false
        since_refresh = 0
        refresh_location_list()
    end
end)
