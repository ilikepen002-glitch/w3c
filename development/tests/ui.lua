-- Contract tests for local UI intent and stale snapshots, not a rendered-engine test.
local G=require 'spirit.game'
local UI=require 'spirit.ui'
local Node={};Node.__index=Node
function Node.new()return setmetatable({visible=true,children={},enabled=true},Node)end
function Node:create_child(kind)
    assert(kind=='图片' or kind=='文本' or kind=='按钮' or kind=='空节点')
    local n=Node.new();n.kind=kind;self.children[#self.children+1]=n;return n
end
function Node:set_anchor(x,y)self.anchor={x,y}end
function Node:set_pos(x,y)self.pos={x,y}end
function Node:set_ui_size(w,h)assert(w>0 and h>0);self.size={w,h}end
function Node:set_widget_relative_scale(x,y)self.scale={x,y};self.scale_writes=(self.scale_writes or 0)+1 end
function Node:set_image_color_hex(color,a)
    assert(color:match('^#%x%x%x%x%x%x$') and type(a)=='number' and a>=0 and a<=255)
    self.image_alpha=a;self.image_color=color
end
function Node:set_text_color_hex(color,a)
    assert(type(color)=='string' and a>=0 and a<=100)
    self.text_color=color;self.text_alpha=a
end
function Node:set_intercepts_operations(value)assert(type(value)=='boolean');self.intercepts=value end
function Node:set_font_size(size)assert(size>0);self.font_size=size end
function Node:set_text_alignment(h,v)assert(h=='左' and v=='上')end
function Node:set_text(value)assert(type(value)=='string');self.text=value end
function Node:set_image(value)self.image=value end
function Node:set_btn_status_image(status,value)
    assert(self.kind=='按钮' and status>=1 and status<=4)
    self.status_images=self.status_images or {};self.status_images[status]=value
end
function Node:set_btn_status_string(status,value)
    assert(self.kind=='按钮' and status>=1 and status<=4 and type(value)=='string')
    self.status_texts=self.status_texts or {};self.status_texts[status]=value
end
function Node:set_visible(value)self.visible=value end
function Node:is_visible()return self.visible end
function Node:set_alpha(value)assert(value>=0 and value<=100)end
function Node:set_button_enable(value)self.enabled=value end
function Node:add_local_event(name,cb)assert(name=='左键-点击');self.click=cb end
y3={ui={get_ui=function(_,path)assert(path=='SpiritHUD');return Node.new()end}}
local g=G.new({1});local p=g.players[1];local request=0;local sent,ok,reason
local function send(c)
    request=request+1;c.request=request;sent=c
    ok,reason=g:dispatch(1,c)
end
local player={get_id=function()return 1 end}
local ui=UI.new(g,player,{ui_root='SpiritHUD',icons={}},send,function()end)
local function check_readable(node)
    if node.text_alpha then assert(node.text_alpha==100,'HUD text must be fully opaque in Y3 percentage units') end
    if node.image_alpha then assert(node.image_alpha==100 and node.image==100547,'tinted backgrounds must use the native-verified opaque rectangle') end
    if node.kind=='按钮' then
        for status=1,4 do
            assert(node.status_images[status]==999 and node.status_texts[status]=='',
                'native button states must not restore template skins or duplicate label text')
        end
        assert(node.children[1].image==100547 and node.children[1].intercepts==false,
            'button background must be tintable without stealing the click from the native button')
    end
    for _,child in ipairs(node.children) do check_readable(child) end
end
check_readable(ui.root)
local function check_bounds(node,path)
    for index,child in ipairs(node.children) do
        local child_path=path..'/'..index..':'..child.kind
        local x,y=child.pos[1],child.pos[2]
        local w,h=child.size[1],child.size[2]
        assert(x>=0 and y>=0 and x+w<=node.size[1] and y+h<=node.size[2],
            'control outside parent: '..child_path..' '..(child.text or ''))
        check_bounds(child,child_path)
    end
end
check_bounds(ui.root,'HUD')
local function overlaps(a,b)
    return a.pos[1]<b.pos[1]+b.size[1] and b.pos[1]<a.pos[1]+a.size[1]
        and a.pos[2]<b.pos[2]+b.size[2] and b.pos[2]<a.pos[2]+a.size[2]
end
-- Identify ordinary root panels by their geometry, excluding intentional modal help/results.
local panels={}
for _,node in ipairs(ui.root.children) do
    if node.kind=='图片' and node~=ui.help and node~=ui.result then panels[#panels+1]=node end
end
for i=1,#panels do for j=i+1,#panels do
    assert(not overlaps(panels[i],panels[j]),'ordinary HUD panels overlap')
end end
print('PASS UI control rectangles inside parents and ordinary HUD panels without overlap (offline geometry only)')
ui.build_button:set('test disabled',false)
assert(not ui.build_button.ui.enabled and ui.build_button.label.text_alpha==100,'disabled actions remain legible')
ui:refresh()
local function click(button)assert(button.ui.enabled);button.ui.click(player)end
click(ui.build_button);assert(ok);ui:refresh()
local tower=p.towers[p.slots[1]];local displayed=tower.version
tower.version=tower.version+1
click(ui.sell);click(ui.sell)
-- First click refreshed the view; a changed version must require fresh confirmation.
assert(sent.action=='build')
click(ui.sell);assert(sent.action=='sell' and ok and not p.slots[1])
ui:refresh();click(ui.build_button);ui:refresh();tower=p.towers[p.slots[1]]
ui:open('wild');click(ui.wild_rows[1]);assert(ok);ui:refresh()
assert(ui.tab=='pets' and ui.pet_id==p.pet_order[1],'successful capture must select the new spirit for binding')
local pet=p.pets[p.pet_order[1]];ui.pet_id=pet.id;ui:refresh()
click(ui.reroll);assert(ok);ui:refresh();local proposal=pet.proposal.id;local stones=p.stones
ui.opened=false;ui:refresh();ui:open('pets')
assert(pet.proposal.id==proposal and p.stones==stones)
-- If synchronized state changes after rendering, the button sends its old version.
local visible_version=ui:pet().version
pet.version=pet.version+1
click(ui.adopt);assert(sent.version==visible_version and not ok and pet.proposal.id==proposal)
ui:refresh();click(ui.adopt);assert(ok and not pet.proposal and p.stones==stones)
ui:refresh();click(ui.release);assert(ui.confirm)
pet.version=pet.version+1;ui:refresh();click(ui.release)
assert(p.pets[pet.id],'changed spirit must need fresh release confirmation')
click(ui.release);assert(ok and not p.pets[pet.id])
for _,tab in ipairs({'pets','gear','contracts','wild','supply'}) do ui:open(tab) end
g:leave(1);ui:refresh();ui:open('gear')
assert(not ui.root.visible,'departed player HUD must be hidden')
local last_sent=sent
ui:command({action='buy_gear',kind=1})
assert(sent==last_sent,'departed player must not send queued intents')
-- A surviving host restarts after a peer leaves; that peer disappears from the new roster.
local multi=G.new({1,2});local peer_sent=0
local peer=UI.new(multi,{get_id=function()return 2 end},{ui_root='SpiritHUD',icons={}},function()peer_sent=peer_sent+1 end,function()end)
peer:open('gear');multi:leave(2);multi.players[1].status='lost';multi.status='over'
assert(multi:dispatch(1,{action='restart',epoch=1,request=1}))
assert(not multi.players[2]);peer:refresh();assert(not peer.root.visible)
peer.equip.ui.click(player);peer:command({action='build',family=1,slot=1})
assert(peer_sent==0,'removed player must not send queued intents after restart')

local function fresh_ui()
    local game=G.new({1});local seq=0
    local panel=UI.new(game,player,{ui_root='SpiritHUD',icons={}},function(c)
        seq=seq+1;c.request=seq;assert(game:dispatch(1,c))
    end,function()end)
    return game,panel
end
local tutorial,guide=fresh_ui()
assert(not guide.help.visible and guide.guide.visible,'onboarding must leave the battlefield and build controls unobstructed')
for _=1,2 do click(guide.guide_button);click(guide.build_button);guide:refresh() end
assert(guide.guide_action=='capture' and #tutorial.players[1].tower_order==2)
click(guide.guide_button);assert(guide.tab=='wild')
click(guide.wild_rows[1]);guide:refresh()
assert(guide.tab=='pets' and guide.guide_action=='bind')
click(guide.guide_button);click(guide.bind);guide:refresh()
assert(guide.guide_action=='start' and tutorial.players[1].pets[guide.pet_id].host,'guided actions must finish binding through normal commands')
click(guide.guide_button);guide:refresh()
assert(tutorial.status=='playing' and not guide.guide.visible,'guide must clear the battlefield once the campaign starts')

local shop,inventory=fresh_ui()
click(inventory.build_button);inventory:refresh();inventory:open('gear')
click(inventory.gear_shop[1]);inventory:refresh()
local first=inventory.gear_id;assert(first==shop.players[1].gear_order[1])
click(inventory.equip);inventory:refresh()
assert(not inventory.equip.ui.enabled and inventory.equip.label.text=='已装备此塔')
click(inventory.gear_shop[1]);inventory:refresh()
assert(inventory.gear_id~=first and inventory.gear_id==shop.players[1].gear_order[2],'purchasing while another item is selected must focus the new item')
assert(not inventory.equip.ui.enabled and inventory.equip.label.text=='已有同类装备','duplicate equipment must explain why it cannot be equipped')
assert(not inventory.gear_shop[2].ui.enabled and inventory.gear_shop[2].label.text:find('金币不足'),'unaffordable purchases must show the reason')
print('PASS UI opacity, onboarding to real start, acquisition focus, equipment reasons, stale intents, confirmation, departure and restart')

-- Viewport queries must remain entirely absent from synchronized constructors/refresh.
local viewport_width,viewport_height=1920,1080
local local_context=false
y3.ui.get_window_width=function()assert(local_context,'window dimensions are local');return viewport_width end
y3.ui.get_window_height=function()assert(local_context,'window dimensions are local');return viewport_height end
local warning_count=0
log={warn=function(code)assert(code=='SPIRIT_UI_VIEWPORT_UNAVAILABLE');warning_count=warning_count+1 end,
    info=function(code)assert(code=='SPIRIT_UI_VIEWPORT')end}
local _,adaptive=fresh_ui()
adaptive:refresh() -- Would fail the context assertion if either queried dimensions.
local function adapt(width,height)
    viewport_width=width;viewport_height=height;local_context=true
    local ok=adaptive:adapt_viewport();local_context=false
    return ok
end
local function close(a,b)assert(math.abs(a-b)<.00001)end
assert(adapt(1920,1080));close(adaptive.root.scale[1],1);close(adaptive.root.pos[1],0);close(adaptive.root.pos[2],0)
assert(adapt(1600,1000));close(adaptive.root.scale[1],.9);close(adaptive.root.pos[1],0);close(adaptive.root.pos[2],54)
assert(adapt(2560,1080));close(adaptive.root.scale[1],1);close(adaptive.root.pos[1],320);close(adaptive.root.pos[2],0)
local writes=adaptive.root.scale_writes
assert(adapt(2560,1080) and adaptive.root.scale_writes==writes,'unchanged viewport must not repeatedly mutate layout')
assert(not adapt(0,0));assert(not adapt(0,1080));assert(warning_count==1 and adaptive.root.scale_writes==writes,'minimized/invalid size must preserve last layout and report once')
assert(not adapt(0/0,1080));assert(not adapt(math.huge,1080));assert(not adapt(nil,1080))
assert(adapt(1920,1080));close(adaptive.root.scale[1],1);close(adaptive.root.pos[1],0)
assert(adapt(1348,840))
assert(1900*adaptive.root.scale[1]+adaptive.root.pos[1]<=1080*1348/840,'right-side workshop must fit the actual screenshot client aspect ratio')
for i,b in ipairs(adaptive.slots) do
    assert(b.label.text==tostring(i) and not b.label.text:find('\n'),'empty slot labels must show a readable single-line number')
end
assert(adaptive.root.size[1]==1920 and adaptive.root.size[2]==1080,'resizing must not change the synchronized node structure')
print('PASS UI viewport 16:9, 16:10, 21:9, resize, invalid-size recovery and no synchronized screen reads')
