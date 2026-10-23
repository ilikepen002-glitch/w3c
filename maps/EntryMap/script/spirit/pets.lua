local C=require 'spirit.config'
local U=require 'spirit.util'
local P={}
local function fail(s) return false,s end
local function quality(g)
    local n=U.random(g,100)
    return n<=45 and 1 or n<=75 and 2 or n<=95 and 3 or 4
end
local function skill(g,pet,slot)
    if slot==4 then return 9+C.element(pet.species) end
    return (slot-1)*3+U.random(g,3)
end
function P.create(g,p,species)
    if #p.pet_order>=C.collection_limit then return nil,'收藏已满' end
    local id=g:uid()
    local pet={id=id,species=species,version=1,skills={},qualities={},host=nil,proposal=nil,active_ready=0}
    local n=U.random(g,100); local count=n<=55 and 2 or n<=90 and 3 or 4
    for i=1,count do pet.skills[i]=skill(g,pet,i);pet.qualities[i]=quality(g) end
    p.pets[id]=pet;p.pet_order[#p.pet_order+1]=id
    return pet
end
function P.capture(g,p,c)
    local wild=p.wild[c.wild_id]
    if not wild or wild.expires<=g.time then return fail('精灵已离开') end
    if #p.pet_order>=C.collection_limit then return fail('收藏已满，未消耗捕获球') end
    if p.balls<1 then return fail('捕获球不足') end
    p.balls=p.balls-1
    local success=p.captured==0 or U.random(g,100)<=C.capture_chance
    if not success then return true,'捕获未成功；可以再次尝试' end
    local pet=P.create(g,p,wild.species)
    p.wild[wild.id]=nil;U.remove_value(p.wild_order,wild.id)
    p.captured=p.captured+1
    g:emit('capture',p.id,{pet_id=pet.id,species=pet.species})
    return true,'获得 '..C.species[pet.species]
end
function P.command(g,p,c)
    if c.action=='capture' then return P.capture(g,p,c) end
    local pet=p.pets[c.pet_id]
    if not pet then return fail('精灵不存在或不属于你') end
    if c.version~=pet.version then return fail('精灵状态已更新，请重试') end
    if c.action=='bind' then
        local t=p.towers[c.tower_id]
        if not t or t.version~=c.tower_version then return fail('目标塔不存在或已变化') end
        if pet.host==t.id then return fail('已绑定该塔') end
        if t.pet and p.pets[t.pet] then local old=p.pets[t.pet];old.host=nil;old.version=old.version+1 end
        if pet.host and p.towers[pet.host] then local old=p.towers[pet.host];old.pet=nil;old.version=old.version+1 end
        t.pet=pet.id;t.version=t.version+1;pet.host=t.id
    elseif c.action=='recall' then
        if not pet.host then return fail('精灵尚未绑定') end
        local t=p.towers[pet.host]; if t then t.pet=nil;t.version=t.version+1 end
        pet.host=nil
    elseif c.action=='reroll' then
        if not U.integer(c.slot,1,4) or not pet.skills[c.slot] then return fail('请选择已有技能栏') end
        if pet.proposal then return fail('请先保留或采用当前候选') end
        if p.stones<2 then return fail('需要2枚洗练石') end
        p.stones=p.stones-2
        pet.proposal={id=g:uid(),slot=c.slot,skill=skill(g,pet,c.slot),quality=quality(g)}
    elseif c.action=='resolve' then
        local pr=pet.proposal
        if not pr or pr.id~=c.proposal_id then return fail('候选已失效') end
        if type(c.adopt)~='boolean' then return fail('请选择保留或采用') end
        if c.adopt then pet.skills[pr.slot]=pr.skill;pet.qualities[pr.slot]=pr.quality end
        pet.proposal=nil
    elseif c.action=='open_slot' then
        if #pet.skills>=4 then return fail('已拥有四个技能栏') end
        if pet.proposal then return fail('请先处理洗练候选') end
        if p.open_stones<1 then return fail('需要1枚开栏石') end
        p.open_stones=p.open_stones-1
        local slot=#pet.skills+1;pet.skills[slot]=skill(g,pet,slot);pet.qualities[slot]=quality(g)
    elseif c.action=='directed' then
        if pet.proposal then return fail('请先处理洗练候选') end
        if not U.integer(c.slot,1,3) or not pet.skills[c.slot] or not U.integer(c.skill,1,9) or C.skills[c.skill].slot~=c.slot then return fail('技能不适合此栏位') end
        if p.stones<3 then return fail('定向学习需要3枚洗练石') end
        -- Directed learning provides a known green result, with explicit UI confirmation.
        p.stones=p.stones-3;pet.skills[c.slot]=c.skill;pet.qualities[c.slot]=2
    elseif c.action=='release' then
        if pet.host then return fail('请先召回精灵') end
        if pet.proposal then return fail('请先处理洗练候选') end
        if c.confirm~=true then return fail('释放需要确认') end
        p.pets[pet.id]=nil;U.remove_value(p.pet_order,pet.id);p.stones=p.stones+2
        return true,'精灵已释放，获得2枚洗练石'
    else return fail('未知精灵操作') end
    pet.version=pet.version+1
    return true,'操作完成'
end
function P.spawn(g,p)
    if #p.wild_order>=3 then return end
    local id=g:uid();p.wild[id]={id=id,species=U.random(g,15),expires=g.time+180}
    p.wild_order[#p.wild_order+1]=id
end
function P.expire(g,p)
    for i=#p.wild_order,1,-1 do
        local id=p.wild_order[i]
        if p.wild[id].expires<=g.time then p.wild[id]=nil;table.remove(p.wild_order,i) end
    end
end
return P
