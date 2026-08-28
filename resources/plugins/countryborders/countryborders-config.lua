---------------------------------------------------------------------------------------------------
-- Country borders on the F10 map.
--
-- Reads dcsRetribution.CountryBorders (emitted only when the terrain ships a border file) and draws
-- each country's real national boundary with its name. Drawing only: nothing here reacts to an
-- aircraft, and no unit is ever spawned.
--
-- Constraints a reader could undo by accident:
--   * DCS will NOT fill a concave freeform (markupToAll shape 7): it draws the outline and stops,
--     and a national border is about as concave as a shape gets. The fill therefore comes from
--     MOOSE's ZONE_POLYGON:ReFill, which triangulates. MOOSE hit the same wall -- its own
--     single-freeform path is dead-coded behind `if false then`. Do not "simplify" this back into
--     one filled freeform; it silently renders as a bare line.
--   * The outline stays a separate freeform because the fill triangles cannot carry a line style.
--   * Values arrive as Lua strings (LuaItem contract) -- tonumber() everything numeric.
--   * Vertices are terrain XY: vert.x = DCS x (north), vert.z = DCS z (east).
--   * Definition order matters (Lua 5.1): helpers precede use. pcall-guarded throughout.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.CountryBorders) then
    return
end

local cfg = dcsRetribution.CountryBorders
local opts = (dcsRetribution.plugins and dcsRetribution.plugins.countryborders) or {}

--: Markup ids are global in DCS, so this base has to stay clear of other plugins'.
local MARKUP_ID_BASE = 8600
local LABEL_ID_OFFSET = 500

local LINE_RGBA = { 0.85, 0.85, 0.85, 0.9 }
local FILL_RGB = { 0.85, 0.85, 0.85 }
local FILL_ALPHA = 0.05
local LINE_TYPE = 2 -- dashed: a boundary, not a hazard ring
local LABEL_FONT_SIZE = tonumber(opts.labelFontSize) or 16
local DRAW_NAMES = opts.drawNames ~= false

local function log(msg)
    env.info("COUNTRYBORDERS|: " .. tostring(msg))
end

local function read_zones()
    local out = {}
    for _, raw in pairs(cfg.zones or {}) do
        local verts = {}
        for _, v in ipairs(raw.verts or {}) do
            local x, z = tonumber(v.x), tonumber(v.z)
            if x and z then
                verts[#verts + 1] = { x = x, z = z }
            end
        end
        if #verts >= 3 then
            out[#out + 1] = {
                country = tostring(raw.country or "?"),
                verts = verts,
                label_x = tonumber(raw.labelX),
                label_z = tonumber(raw.labelZ),
            }
        end
    end
    return out
end

local function draw_fill(zone, index)
    pcall(function()
        local pts = {}
        for _, v in ipairs(zone.verts) do
            pts[#pts + 1] = { x = v.x, y = v.z }
        end
        local poly = ZONE_POLYGON:NewFromPointsArray("CB-" .. index, pts)
        poly:SetDrawCoalition(-1)
        poly:ReFill(FILL_RGB, FILL_ALPHA)
    end)
end

local function draw_outline(zone, index)
    pcall(function()
        local args = { 7, -1, MARKUP_ID_BASE + index } -- freeform, all coalitions
        for _, v in ipairs(zone.verts) do
            args[#args + 1] = { x = v.x, y = 0, z = v.z }
        end
        args[#args + 1] = LINE_RGBA
        args[#args + 1] = { 0, 0, 0, 0 } -- the fill is the triangles' job
        args[#args + 1] = LINE_TYPE
        args[#args + 1] = true -- read only
        trigger.action.markupToAll(unpack(args))
    end)
end

local function draw_name(zone, index)
    if not (DRAW_NAMES and zone.label_x and zone.label_z) then
        return
    end
    pcall(function()
        local y = 0
        pcall(function()
            y = land.getHeight({ x = zone.label_x, y = zone.label_z }) or 0
        end)
        trigger.action.textToAll(
            -1,
            MARKUP_ID_BASE + LABEL_ID_OFFSET + index,
            { x = zone.label_x, y = y, z = zone.label_z },
            { LINE_RGBA[1], LINE_RGBA[2], LINE_RGBA[3], 1.0 },
            { 0, 0, 0, 0.45 },
            LABEL_FONT_SIZE,
            true,
            string.upper(zone.country)
        )
    end)
end

local ok, err = pcall(function()
    local zones = read_zones()
    for index, zone in ipairs(zones) do
        draw_fill(zone, index)
        draw_name(zone, index)
        draw_outline(zone, index)
    end
    log(string.format("%d country border(s) drawn.", #zones))
end)
if not ok then
    env.error("COUNTRYBORDERS|: setup error: " .. tostring(err))
end
