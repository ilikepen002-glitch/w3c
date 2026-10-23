-- Y3 scene presentation. Combat and ownership remain in the synchronized game.
local C=require 'spirit.config'
local B=require 'spirit.combat'
local FX=require 'spirit.effects'
local World={};World.__index=World
-- Verified in the current native preview: input 6500 reads back as distance 65m.
-- Pitch is degrees directly; 295 is clamped to 89.5 degrees by this engine.
-- The last argument is FOV, despite lualib's historical "visibility range" label.
local CAMERA_DISTANCE_CM=6500
local CAMERA_FOV=40
local CAMERA_DOWN_PITCH=65
local function remove(unit)if unit and unit:is_exist() then unit:remove() end end
local function passive(unit)
    for _,state in ipairs({'禁止普攻','禁止施法','禁止移动','无法控制','无法被攻击','无视动态碰撞','无视静态碰撞'}) do unit:add_state(state) end
    unit:set_attr('hp_rec',0)
end
function World.new(game,assets)
    local self=setmetatable({game=game,assets=assets,lanes={},cameras={},decorations={},units={},towers={},retiring={}},World)
    local area=y3.area.get_map_area()
    local x0,x1,y0,y1=area:get_min_x(),area:get_max_x(),area:get_min_y(),area:get_max_y()
    log.info(('SPIRIT_MAP_BOUNDS %.1f %.1f %.1f %.1f'):format(x0,x1,y0,y1))
    local cols=#game.player_order>1 and 2 or 1
    local rows=math.ceil(#game.player_order/cols)
    self.scale=math.min(1,(x1-x0-400)/(6200*cols),(y1-y0-400)/(4600*rows))
    assert(self.scale>0.1,'地图可用范围太小，请使用至少32×32的空白地图')
    for index,id in ipairs(game.player_order) do
        local col=(index-1)%cols;local row=math.floor((index-1)/cols)
        self.lanes[id]={x=(x0+x1)/2+(col-(cols-1)/2)*6200*self.scale,
            y=(y0+y1)/2+(row-(rows-1)/2)*4600*self.scale}
        area:set_visible(y3.player.get_by_id(id),true,true)
        self:build_lane(id)
        -- Moving the focus south lifts the battlefield above the management HUD.
        local distance_cm=CAMERA_DISTANCE_CM*self.scale
        self.cameras[id]=y3.camera.create_camera(self:point(id,0,-800),distance_cm,0,0,CAMERA_DOWN_PITCH,CAMERA_FOV)
        log.info(('SPIRIT_CAMERA player=%d distance_cm=%.2f fov_deg=%d pitch_deg=%d focus_y_cm=%.1f'):format(
            id,distance_cm,CAMERA_FOV,CAMERA_DOWN_PITCH,self.lanes[id].y-800*self.scale))
    end
    self.effects=FX.new(self)
    return self
end
function World:point(id,x,y,z)
    local lane=self.lanes[id]
    return y3.point.create(lane.x+x*self.scale,lane.y+y*self.scale,(z or 0)*self.scale)
end
function World:decoration(id,key,x,y,sx,sy,sz)
    local u=y3.unit.create_unit(y3.player.get_by_id(31),key,self:point(id,x,y),0)
    assert(u and u:is_exist(),'场景物件创建失败: '..key)
    passive(u);u:add_state('无法被选中');u:set_unit_scale(sx*self.scale,sy*self.scale,sz*self.scale)
    self.decorations[#self.decorations+1]=u
    return u
end
function World:build_lane(id)
    -- A visible serpentine paved route, with two rows of twelve total building pads.
    for d=0,B.path_length,240 do
        local x,y=B.position(d)
        self:decoration(id,self.assets.floor,x,y,2.5,2.5,0.12)
    end
    for index,pos in ipairs(C.slots) do
        local pad=self:decoration(id,self.assets.pad,pos.x,pos.y,2.6,2.6,0.2)
        pad:set_name('建造位 '..index)
        pad:set_name_show_type('单位名')
    end
    local entry=self:decoration(id,self.assets.gate,-2500,-1500,3,3,3)
    entry:set_name('黑潮入口');entry:set_name_show_type('单位名')
    local core=self:decoration(id,self.assets.gate,2500,1500,3,3,3)
    core:set_name('契灵核心');core:set_name_show_type('单位名')
end
function World:focus(id)
    local player=y3.player.get_by_id(id)
    self.cameras[id]:apply(player,0)
    y3.camera.disable_camera_move(player)
end
function World:create_tower(p,t)
    local u=y3.unit.create_unit(y3.player.get_by_id(p.id),self.assets.towers[t.family],self:point(p.id,t.x,t.y),90)
    assert(u and u:is_exist(),'防御塔创建失败')
    passive(u);u:set_name(C.tower_name(t));u:set_scale((0.8+t.level*0.08)*self.scale)
    self.towers[t.id]={unit=u,level=t.level}
end
function World:create_enemy(p,e)
    local key=e.boss and self.assets.enemies.boss or e.armor>.3 and self.assets.enemies.armor or e.speed>=220 and self.assets.enemies.fast or self.assets.enemies.normal
    local u=y3.unit.create_unit(y3.player.get_by_id(32),key,self:point(p.id,e.x,e.y),0)
    assert(u and u:is_exist(),'敌人创建失败')
    passive(u);u:set_name(p.wave_data.name);u:set_scale((e.boss and 1.8 or e.elite and 1.15 or .7)*self.scale)
    u:set_attr('hp_max',e.max_hp);u:set_hp(e.hp);u:play_animation('walk',1,0,-1,true)
    self.units[e.id]={unit=u,x=e.x,y=e.y,hp=e.hp}
end
function World:update(events)
    for _,event in ipairs(events) do
        if event.kind=='restart' then
            self.effects:clear()
            for _,record in pairs(self.towers) do remove(record.unit) end
            for _,record in pairs(self.units) do remove(record.unit) end
            for _,record in ipairs(self.retiring) do remove(record.unit) end
            self.towers={};self.units={};self.retiring={}
        end
    end
    for _,id in ipairs(self.game.player_order) do
        local p=self.game.players[id]
        for _,tid in ipairs(p.tower_order) do
            local t=p.towers[tid];local record=self.towers[tid]
            if not record then self:create_tower(p,t)
            elseif record.level~=t.level then
                record.unit:set_name(C.tower_name(t));record.unit:set_scale((.8+t.level*.08)*self.scale);record.level=t.level
            end
        end
        for _,eid in ipairs(p.enemy_order) do
            local e=p.enemies[eid];local record=self.units[eid]
            if not record then self:create_enemy(p,e)
            else
                if e.x~=record.x or e.y~=record.y then
                    record.unit:set_facing(math.deg(math.atan(e.y-record.y,e.x-record.x)),.05)
                    record.unit:set_point(self:point(id,e.x,e.y),true);record.x=e.x;record.y=e.y
                end
                if e.hp~=record.hp then record.unit:set_hp(math.max(1,e.hp));record.hp=e.hp end
            end
        end
    end
    for _,event in ipairs(events) do
        local d=event.data
        if event.kind=='attack' then
            local t=self.towers[d.tower_id]
            if t then
                t.unit:set_facing(math.deg(math.atan(d.target_y-d.y,d.target_x-d.x)),.06)
                t.unit:play_animation('attack1',1,0,-1,false,true,.05)
            end
        elseif event.kind=='death' then
            local record=self.units[d.enemy_id]
            if record then
                record.unit:play_animation('die',1,0,-1,false,false,0)
                self.retiring[#self.retiring+1]={unit=record.unit,until_time=self.game.time+.8}
                self.units[d.enemy_id]=nil
            end
        elseif event.kind=='wave' or event.kind=='result' then
            log.info('SPIRIT_EVENT',event.kind,event.player,d.wave or d.won)
        end
    end
    self.effects:update(events)
    local alive_towers,alive_enemies={},{}
    for _,id in ipairs(self.game.player_order) do
        local p=self.game.players[id]
        for _,tid in ipairs(p.tower_order) do alive_towers[tid]=true end
        for _,eid in ipairs(p.enemy_order) do alive_enemies[eid]=true end
    end
    for id,record in pairs(self.towers) do if not alive_towers[id] then remove(record.unit);self.towers[id]=nil end end
    for id,record in pairs(self.units) do if not alive_enemies[id] then remove(record.unit);self.units[id]=nil end end
    for i=#self.retiring,1,-1 do
        if self.game.time>=self.retiring[i].until_time or self.game.status=='over' then remove(self.retiring[i].unit);table.remove(self.retiring,i) end
    end
end
return World
