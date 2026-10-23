-- Keys created from the official Y3 unit template by tools/deploy.py.
local A={
    ui_root='SpiritHUD',
    towers={134299001,134299002,134299003,134299004,134299005},
    enemies={normal=134299006,fast=134299007,armor=134299008,boss=134299009},
    floor=134299010,pad=134299011,gate=134299012,
    icons={},
}
function A.load_icons()
    -- IDs returned by the editor's native image import, recorded in package meta.json.
    A.icons.contract=134229234
    A.icons.elements={134271962,134234492,134251252,134229470,134250350}
end
return A
