require "structure"

Tracker:AddItems("items.json")

require "logic"
require "location_list"

LOCATION_FILES = {
    "locations/aiz1.json",
    "locations/aiz2.json",
    "locations/hcz1.json",
    "locations/hcz2.json",
    "locations/mgz1.json",
    "locations/mgz2.json",
    "locations/cnz1.json",
    "locations/cnz2.json",
    "locations/icz1.json",
    "locations/icz2.json",
    "locations/lbz1.json",
    "locations/lbz2.json",
    "locations/mhz1.json",
    "locations/mhz2.json",
    "locations/fbz1.json",
    "locations/fbz2.json",
    "locations/sz1.json",
    "locations/sz2.json",
    "locations/lrz1.json",
    "locations/lrz2.json",
    "locations/lrz3.json",
    "locations/hpz.json",
    "locations/ssz.json",
    "locations/dez1.json",
    "locations/dez2.json",
    "locations/kssz.json",
    "locations/ddz.json",
    "locations/ss1.json",
    "locations/ss2.json",
    "locations/ss3.json",
    "locations/ss4.json",
    "locations/ss5.json",
    "locations/ss6.json",
    "locations/ss7.json",
    "locations/ss8.json",
    "locations/ss9.json",
    "locations/ss10.json",
    "locations/ss11.json",
    "locations/ss12.json",
    "locations/ss13.json",
    "locations/ss14.json",
}

Tracker:AddMaps("maps.json")
for _, file in ipairs(LOCATION_FILES) do
    Tracker:AddLocations(file)
end
Tracker:AddLayouts("tracker.json")

if Archipelago ~= nil then
    require "autotracking"
end
