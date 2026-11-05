local LOCATE_VIEW_WIDTH = 1800
local LOCATE_VIEW_HEIGHT = 1100
local REFRESH_INTERVAL = 0.25

local STATE_STYLES = {
    available = {mods = "", background = "#00a000", color = "#ffffff"},
    sequence_break = {mods = "", background = "#e0b000", color = "#000000"},
    unavailable = {mods = "", background = "#c00000", color = "#ffffff"},
    inspect = {mods = "", background = "#2060ff", color = "#ffffff"},
    checked = {mods = "@disabled", background = "#505050", color = "#c0c0c0"},
    not_in_seed = {mods = "brightness|0.35", background = "", color = "#808080"},
}
local HIGHLIGHT_COLOR = "#ffd700"
local NO_NUMBER_BADGE = "\u{25CF}"

LOCATION_ITEMS = {}

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

function locate(loc)
    if loc.map == nil then
        return
    end
    if highlighted == loc.id then
        set_highlight(nil)
        return
    end
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
