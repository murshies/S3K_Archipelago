-- Logic for whether or not a location is in logic
-- Unfortunately this is a bit of duplication of the logic in the apworld
-- itself, but for now it is the most straightforward way to do this.
-- TODO: Pull some of these constants from the apworld and generate some of
-- this file.

ZONE_UNLOCKS_ALL_UNLOCKED = 0
ZONE_UNLOCKS_ZONES_AND_CHARACTERS = 1
ZONE_UNLOCKS_ZONES_ONLY = 2
ZONE_UNLOCKS_CHARACTERS_ONLY = 3

GOAL_NONE = 0
GOAL_DOOMSDAY = 1
GOAL_KNUCKLES_SKY_SANCTUARY = 2
GOAL_DEATH_EGG = 3

EMERALDS_FOR_CHAOS_HUNT = 7
EMERALDS_FOR_SUPER_HUNT = 14

GOAL_ZONES = {
   [GOAL_DOOMSDAY] = "Doomsday",
   [GOAL_KNUCKLES_SKY_SANCTUARY] = "Knuckles Sky Sanctuary",
   [GOAL_DEATH_EGG] = "Death Egg",
}

LOCATIONS_BY_ID = {}
for _, loc in ipairs(LOCATIONS) do
   LOCATIONS_BY_ID[loc.id] = loc
end

LOCATIONS_IN_SEED = nil

function slugify(text)
   return (text:lower():gsub("[^a-z0-9]+", "_"):gsub("^_+", ""):gsub("_+$", ""))
end

local function has(code)
   return Tracker:ProviderCountForCode(code) > 0
end

local function count(code)
   local item = Tracker:FindObjectForCode(code)
   if item == nil then
      return 0
   end
   return item.AcquiredCount
end

local function zone_item(zone)
   return "zone_" .. slugify(zone)
end

local function zone_char_item(zone, char)
   return "zone_" .. slugify(zone) .. "_" .. slugify(char)
end

local function char_item(char)
   return "char_" .. slugify(char)
end

local function progressive_stage(code)
   local item = Tracker:FindObjectForCode(code)
   if item == nil then
      return 0
   end
   return item.CurrentStage
end

function zone_unlocks()
   return progressive_stage("setting_zone_unlocks_all")
end

function big_rings_goal()
   return progressive_stage("setting_big_rings_goal_none")
end

function chaos_emeralds_goal()
   return progressive_stage("setting_chaos_emeralds_goal_none")
end

function super_emeralds_goal()
   return progressive_stage("setting_super_emeralds_goal_none")
end

local function hard_logic()
   return has("setting_hard_logic")
end

local function big_rings_to_check()
   return count("setting_big_rings_to_check")
end

local function chaos_emeralds()
   return count("chaos_emerald")
end

local function hyper_state_available()
   return super_emeralds_goal() ~= GOAL_NONE or chaos_emeralds_goal() == GOAL_NONE
end

local function goal_applicable(goal, zone)
   return GOAL_ZONES[goal] == zone
end

local function is_enabled_goal_zone(zone)
   return goal_applicable(big_rings_goal(), zone) or
      goal_applicable(chaos_emeralds_goal(), zone) or
      goal_applicable(super_emeralds_goal(), zone)
end

local function in_seed(loc)
   return LOCATIONS_IN_SEED == nil or LOCATIONS_IN_SEED[loc.id] ~= nil
end

local function zone_item_for(zone)
   if zone == "Knuckles Sky Sanctuary" then
      return zone_item("Sky Sanctuary")
   end
   return zone_item(zone)
end

local function can_reach_all_special_stages()
   local mode = zone_unlocks()
   if mode == ZONE_UNLOCKS_ALL_UNLOCKED or mode == ZONE_UNLOCKS_CHARACTERS_ONLY then
      return true
   end
   for stage = 1, 14 do
      local zone = "Special Stage " .. stage
      if mode == ZONE_UNLOCKS_ZONES_ONLY then
         if not has(zone_item(zone)) then
            return false
         end
      else
         local any = false
         for _, char in ipairs({"Sonic", "Tails", "Knuckles"}) do
            if has(zone_char_item(zone, char)) then
               any = true
               break
            end
         end
         if not any then
            return false
         end
      end
   end
   return true
end

local function can_check_required_num_big_rings()
   local mode = zone_unlocks()
   if mode == ZONE_UNLOCKS_ALL_UNLOCKED then
      return true
   end
   local reachable = 0
   for _, loc in ipairs(LOCATIONS) do
      if loc.type == "big_ring" and in_seed(loc) then
         local ok = false
         if mode == ZONE_UNLOCKS_ZONES_ONLY then
            ok = has(zone_item_for(loc.zone))
         else
            for _, req in ipairs(loc.requirements) do
               if mode == ZONE_UNLOCKS_CHARACTERS_ONLY then
                  ok = has(char_item(req.char))
               else
                  ok = has(zone_char_item(loc.zone, req.char))
               end
               if ok then
                  break
               end
            end
         end
         if ok then
            reachable = reachable + 1
         end
      end
   end
   return reachable >= big_rings_to_check()
end

local function can_enter_zone(zone)
   if goal_applicable(big_rings_goal(), zone) then
      return can_check_required_num_big_rings()
   elseif goal_applicable(chaos_emeralds_goal(), zone) then
      return chaos_emeralds() >= EMERALDS_FOR_CHAOS_HUNT
   elseif goal_applicable(super_emeralds_goal(), zone) then
      return chaos_emeralds() >= EMERALDS_FOR_SUPER_HUNT
   end
   local mode = zone_unlocks()
   if mode == ZONE_UNLOCKS_ZONES_ONLY then
      return has(zone_item_for(zone))
   elseif mode == ZONE_UNLOCKS_ZONES_AND_CHARACTERS then
      if zone == "Doomsday" then
         return has(zone_char_item(zone, "Sonic"))
      elseif zone == "Death Egg" then
         return has(zone_char_item(zone, "Sonic")) or has(zone_char_item(zone, "Tails"))
      elseif zone == "Knuckles Sky Sanctuary" then
         return has(zone_char_item(zone, "Knuckles"))
      elseif zone == "Sky Sanctuary" then
         return has(zone_char_item(zone, "Sonic")) or has(zone_char_item(zone, "Tails"))
      else
         return has(zone_char_item(zone, "Sonic")) or has(zone_char_item(zone, "Tails")) or has(zone_char_item(zone, "Knuckles"))
      end
   else
      return true
   end
end

local function requirement_met(loc, req)
   local mode = zone_unlocks()
   if mode == ZONE_UNLOCKS_CHARACTERS_ONLY then
      if not has(char_item(req.char)) then
         return false
      end
   elseif mode == ZONE_UNLOCKS_ZONES_AND_CHARACTERS then
      if not has(zone_char_item(loc.zone, req.char)) then
         return false
      end
   elseif mode == ZONE_UNLOCKS_ZONES_ONLY then
      if not has(zone_item_for(loc.zone)) then
         return false
      end
   end

   if req.super_state ~= nil then
      if chaos_emeralds_goal() == GOAL_NONE and super_emeralds_goal() == GOAL_NONE then
         if not can_reach_all_special_stages() then
            return false
         end
      else
         local needed = EMERALDS_FOR_CHAOS_HUNT
         if req.super_state ~= "super" or req.char == "Tails" then
            needed = EMERALDS_FOR_SUPER_HUNT
         end
         if needed == EMERALDS_FOR_SUPER_HUNT and not hyper_state_available() then
            return false
         end
         if chaos_emeralds() < needed then
            return false
         end
      end
   end
   return true
end

function location_access(loc)
   if not can_enter_zone(loc.zone) then
      return AccessibilityLevel.None
   end
   if #loc.requirements == 0 or is_enabled_goal_zone(loc.zone) then
      return AccessibilityLevel.Normal
   end
   local sequence_break = false
   for _, req in ipairs(loc.requirements) do
      if requirement_met(loc, req) then
         if not req.hard or hard_logic() then
            return AccessibilityLevel.Normal
         end
         sequence_break = true
      end
   end
   if sequence_break then
      return AccessibilityLevel.SequenceBreak
   end
   return AccessibilityLevel.None
end

function s3k_access(id)
   local loc = LOCATIONS_BY_ID[tonumber(id)]
   if loc == nil then
      return AccessibilityLevel.None
   end
   return location_access(loc)
end

function s3k_in_seed(id)
   local loc = LOCATIONS_BY_ID[tonumber(id)]
   return loc ~= nil and in_seed(loc)
end
