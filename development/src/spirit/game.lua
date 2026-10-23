local C=require 'spirit.config'
local U=require 'spirit.util'
local Pets=require 'spirit.pets'
local Towers=require 'spirit.towers'
local Combat=require 'spirit.combat'
local G={};G.__index=G
local pet_actions={capture=true,bind=true,recall=true,reroll=true,resolve=true,open_slot=true,directed=true,release=true}
local tower_actions={build=true,upgrade=true,sell=true}
local gear_actions={buy_gear=true,upgrade_gear=true,equip=true,unequip=true,recycle_gear=true}
function G.new(ids,seed,serial)
    assert(type(ids)=='table' and #ids>=1 and #ids<=4,'requires 1-4 players')
    local g=setmetatable({players={},player_order={},host=ids[1],time=0,status='lobby',difficulty=1,rng=(seed or 2026)%65536,
        serial=serial or 0,epoch=1,events={},accumulator=0},G)
    for _,id in ipairs(ids) do
        assert(U.integer(id,1,4) and not g.players[id],'invalid or duplicate player')
        g.player_order[#g.player_order+1]=id
        g.players[id]={id=id,gold=C.start_gold,lives=C.start_lives,stones=C.start_stones,balls=C.start_balls,open_stones=0,
            last_request=0,status='ready',wave=0,completed=0,kills=0,damage=0,leaks=0,loot_gold=0,
            towers={},tower_order={},slots={},pets={},pet_order={},captured=0,wild={},wild_order={},
            gear={},gear_order={},bonuses={},offers={},offer_order={},contracts={},enemies={},enemy_order={},
            next_wave=0,spawned=0,next_spawn=0,challenge=false,notice='先建造两座塔，再开始战役。',notice_at=0}
        Pets.spawn(g,g.players[id])
    end
    return g
end
function G:uid() self.serial=self.serial+1;return self.serial end
function G:emit(kind,player,data)
    self.events[#self.events+1]={kind=kind,player=player,data=data or {}}
end
function G:drain_events()local e=self.events;self.events={};return e end
function G:offer(p)
    local pool={};for i=1,#C.contracts do pool[i]=i end
    local choices={};for i=1,3 do choices[i]=table.remove(pool,U.random(self,#pool)) end
    local id=self:uid();p.offers[id]={id=id,choices=choices};p.offer_order[#p.offer_order+1]=id
    self:emit('offer',p.id,{offer_id=id})
end
function G:start_wave(p)
    p.wave=p.wave+1;p.spawned=0;p.next_spawn=self.time;p.status='combat';p.wave_data=C.wave(p.wave)
    p.wave_challenge=p.challenge;p.challenge=false
    self:emit('wave',p.id,{wave=p.wave,challenge=p.wave_challenge})
end
function G:complete_wave(p)
    p.completed=p.wave
    local reward=math.floor(p.wave_data.reward*C.difficulties[self.difficulty].reward*(1+(p.bonuses.income or 0)/100)*(p.wave_challenge and 1.5 or 1))
    p.gold=p.gold+reward;p.balls=math.min(60,p.balls+1);p.stones=p.stones+1+(p.wave_challenge and 1 or 0)
    if p.wave%4==0 then
        p.open_stones=p.open_stones+1;p.stones=p.stones+2
        if p.wave<C.waves then self:offer(p) end
    end
    if p.wave%2==0 and p.wave<C.waves then Pets.spawn(self,p) end
    self:emit('wave_complete',p.id,{wave=p.wave,reward=reward})
    if p.wave==C.waves then p.status='won';self:emit('result',p.id,{won=true})
    else p.status='break';p.next_wave=self.time+C.intermission end
end
function G:progress_command(p,c)
    if c.action=='restart' then
        if self.status~='over' or p.id~=self.host then return false,'所有防线结束后由房主重新开始' end
        local ids={};for _,id in ipairs(self.player_order) do if self.players[id].status~='left' then ids[#ids+1]=id end end
        local epoch,difficulty=self.epoch+1,self.difficulty
        local fresh=G.new(ids,self.rng+7919,self.serial)
        for key in pairs(self) do self[key]=nil end
        for key,value in pairs(fresh) do self[key]=value end
        self.epoch=epoch;self.difficulty=difficulty
        self:emit('restart',p.id,{epoch=epoch})
        return true,'新战役已准备好'
    elseif c.action=='difficulty' then
        if self.status~='lobby' or p.id~=self.host then return false,'仅房主可在开局前选择难度' end
        if not U.integer(c.value,1,#C.difficulties) then return false,'无效难度' end
        self.difficulty=c.value;return true,'难度：'..C.difficulties[c.value].name
    elseif c.action=='start' then
        if self.status~='lobby' or p.id~=self.host then return false,'仅房主可开始战役' end
        self.status='playing'
        for _,id in ipairs(self.player_order) do
            local q=self.players[id];if q.status~='left' then q.status='break';q.next_wave=self.time+C.preparation end
        end
        return true,'战役开始，准备迎敌'
    elseif c.action=='next_wave' then
        if p.status~='break' then return false,'当前无法提前开始' end
        p.next_wave=self.time;return true,'准备迎敌'
    elseif c.action=='challenge' then
        if p.status~='break' then return false,'仅波间可开启挑战' end
        if p.challenge then return false,'已开启挑战' end
        p.challenge=true;return true,'下波敌人生命提高35%，结算金币提高50%并额外获得洗练石'
    elseif c.action=='contract' then
        local offer=p.offers[c.offer_id]
        if not offer or not U.integer(c.choice,1,3) then return false,'契约选择已失效' end
        local id=offer.choices[c.choice];local def=C.contracts[id]
        if def.kind=='repair' then p.lives=math.min(C.start_lives,p.lives+def.value);p.stones=p.stones+2
        else p.bonuses[def.kind]=(p.bonuses[def.kind] or 0)+def.value end
        p.contracts[#p.contracts+1]=id;p.offers[offer.id]=nil;U.remove_value(p.offer_order,offer.id)
        return true,'获得 '..def.name
    elseif c.action=='buy_supply' then
        local cost=c.kind=='ball' and 80 or c.kind=='stone' and 100 or c.kind=='open' and 500 or nil
        if not cost then return false,'补给不存在' end
        if p.gold<cost then return false,'金币不足' end
        if c.kind=='ball' and p.balls>=60 then return false,'捕获球已满' end
        p.gold=p.gold-cost
        if c.kind=='ball' then p.balls=p.balls+1 elseif c.kind=='stone' then p.stones=p.stones+2 else p.open_stones=p.open_stones+1 end
        return true,'补给已到账'
    end
    return false,'未知操作'
end
function G:dispatch(actor,c)
    local p=self.players[actor]
    if not p or type(c)~='table' then return false,'无效玩家或指令' end
    if c.epoch~=self.epoch then return false,'对局已变化' end
    if not U.integer(c.request,1,2147483647) or c.request<=p.last_request then return false,'重复或过期请求' end
    if p.status=='left' or ((p.status=='lost' or p.status=='won') and c.action~='restart') then return false,'本路对局已结束' end
    if type(c.action)~='string' then return false,'无效操作' end
    p.last_request=c.request
    local ok,reason
    if pet_actions[c.action] then ok,reason=Pets.command(self,p,c)
    elseif tower_actions[c.action] then ok,reason=Towers.command(self,p,c)
    elseif gear_actions[c.action] then ok,reason=Towers.gear_command(self,p,c)
    else ok,reason=self:progress_command(p,c) end
    p=self.players[actor];p.notice=reason;p.notice_at=self.time
    self:emit('command',actor,{ok=ok,reason=reason,request=c.request})
    return ok,reason
end
function G:leave(actor)
    local p=self.players[actor]
    if not p or p.status=='left' then return end
    p.status='left';p.enemies={};p.enemy_order={};p.towers={};p.tower_order={};p.slots={}
    for _,id in ipairs(p.pet_order) do local pet=p.pets[id];pet.host=nil;pet.version=pet.version+1 end
    for _,id in ipairs(p.gear_order) do local gear=p.gear[id];gear.tower=nil;gear.version=gear.version+1 end
    self:emit('leave',actor)
    if self.host==actor then for _,id in ipairs(self.player_order) do if self.players[id].status~='left' then self.host=id;break end end end
end
function G:step(dt)
    assert(type(dt)=='number' and dt>0 and dt<=1,'invalid timestep')
    -- Preparation in the lobby is untimed, including the guaranteed first spirit.
    if self.status=='over' or self.status=='lobby' then return end
    self.time=self.time+dt
    for _,id in ipairs(self.player_order) do
        local p=self.players[id]
        if p.status=='ready' or p.status=='break' or p.status=='combat' then
            Pets.expire(self,p)
            if self.status=='playing' then
                if p.status=='break' and self.time>=p.next_wave then self:start_wave(p) end
                if p.status=='combat' then
                    local w=p.wave_data
                    if p.spawned<w.count and self.time>=p.next_spawn then
                        Combat.spawn(self,p,w,p.wave_challenge);p.spawned=p.spawned+1;p.next_spawn=self.time+w.spawn_interval
                    end
                    Combat.step(self,p,dt)
                    if p.lives<=0 then p.status='lost';p.enemies={};p.enemy_order={};self:emit('result',p.id,{won=false})
                    elseif p.spawned==w.count and #p.enemy_order==0 then self:complete_wave(p) end
                end
            end
        end
    end
    if self.status=='playing' then
        local active=false
        for _,id in ipairs(self.player_order) do local s=self.players[id].status;if s=='combat' or s=='break' then active=true;break end end
        if not active then self.status='over' end
    end
end
function G:snapshot(actor)
    local p=self.players[actor]
    if not p then return nil end
    return U.copy(p)
end
return G
