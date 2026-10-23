local C=require 'spirit.config'
local U=require 'spirit.util'
local T={}
local function fail(s)return false,s end
function T.command(g,p,c)
    if c.action=='build' then
        if not U.integer(c.family,1,#C.towers) or not U.integer(c.slot,1,#C.slots) then return fail('请选择塔族和建造位置') end
        if p.slots[c.slot] then return fail('该位置已有塔') end
        local cost=C.towers[c.family].cost
        if p.gold<cost then return fail('金币不足') end
        p.gold=p.gold-cost
        local id=g:uid();local pos=C.slots[c.slot]
        p.towers[id]={id=id,family=c.family,slot=c.slot,x=pos.x,y=pos.y,level=1,branch=0,version=1,spent=cost,gear={},pet=nil,
            next_attack=g.time,hit_count=0,last_target=0,streak=0,damage=0,kills=0}
        p.slots[c.slot]=id;p.tower_order[#p.tower_order+1]=id
        g:emit('build',p.id,{tower_id=id})
        return true,'建造完成'
    end
    local t=p.towers[c.tower_id]
    if not t or c.tower_version~=t.version then return fail('塔不存在或已变化') end
    if c.action=='upgrade' then
        if t.level>=6 then return fail('已达到终阶') end
        if t.level==5 and not U.integer(c.branch,1,2) then return fail('请选择终阶分支') end
        local cost=C.upgrade_costs[t.level+1]
        if p.gold<cost then return fail('金币不足') end
        p.gold=p.gold-cost;t.spent=t.spent+cost;t.level=t.level+1
        if t.level==6 then t.branch=c.branch end
    elseif c.action=='sell' then
        if c.confirm~=true then return fail('出售需要确认') end
        if t.pet and p.pets[t.pet] then local pet=p.pets[t.pet];pet.host=nil;pet.version=pet.version+1 end
        for _,id in ipairs(t.gear) do p.gear[id].tower=nil;p.gear[id].version=p.gear[id].version+1 end
        p.gold=p.gold+math.floor(t.spent*0.8);p.slots[t.slot]=nil;p.towers[t.id]=nil;U.remove_value(p.tower_order,t.id)
        g:emit('sell',p.id,{tower_id=t.id})
        return true,'出售返还80%建造升级费用；精灵与装备已归还'
    else return fail('未知塔操作') end
    t.version=t.version+1
    return true,'升级完成'
end
function T.gear_command(g,p,c)
    if c.action=='buy_gear' then
        if not U.integer(c.kind,1,#C.equipment) then return fail('装备不存在') end
        if #p.gear_order>=36 then return fail('装备仓库已满') end
        if p.gold<C.gear_costs[1] then return fail('金币不足') end
        p.gold=p.gold-C.gear_costs[1]
        local id=g:uid();p.gear[id]={id=id,kind=c.kind,tier=1,version=1};p.gear_order[#p.gear_order+1]=id
        return true,'装备已放入仓库'
    end
    local gear=p.gear[c.gear_id]
    if not gear or gear.version~=c.gear_version then return fail('装备不存在或已变化') end
    if c.action=='upgrade_gear' then
        if gear.tier>=5 then return fail('装备已满阶') end
        local cost=C.gear_costs[gear.tier+1]
        if p.gold<cost then return fail('金币不足') end
        p.gold=p.gold-cost;gear.tier=gear.tier+1
    elseif c.action=='recycle_gear' then
        if gear.tower then return fail('先卸下装备再回收') end
        if c.confirm~=true then return fail('回收需要确认') end
        local spent=0;for tier=1,gear.tier do spent=spent+C.gear_costs[tier] end
        local refund=math.floor(spent*.5)
        p.gold=p.gold+refund;p.gear[gear.id]=nil;U.remove_value(p.gear_order,gear.id)
        return true,'装备已回收，返还'..refund..'金币'
    elseif c.action=='equip' then
        local t=p.towers[c.tower_id]
        if not t or t.version~=c.tower_version then return fail('目标塔已变化') end
        if gear.tower==t.id then return fail('已经装备') end
        if #t.gear>=3 then return fail('每座塔最多装备3件') end
        for _,id in ipairs(t.gear) do if p.gear[id].kind==gear.kind then return fail('不能装备两件同类装备') end end
        if gear.tower and p.towers[gear.tower] then
            local old=p.towers[gear.tower];U.remove_value(old.gear,gear.id);old.version=old.version+1
        end
        t.gear[#t.gear+1]=gear.id;t.version=t.version+1;gear.tower=t.id
    elseif c.action=='unequip' then
        if not gear.tower then return fail('装备已在仓库') end
        local t=p.towers[gear.tower]
        if t then U.remove_value(t.gear,gear.id);t.version=t.version+1 end
        gear.tower=nil
    else return fail('未知装备操作') end
    gear.version=gear.version+1
    return true,'装备操作完成'
end
function T.stats(p,t)
    local d=C.towers[t.family]
    local s={attack=0,speed=0,range=0,pierce=0,splash=0,boss=0,cooldown=0,plunder=0,spirit=0,double=0,critical=0,heavy=0,execute=0}
    for k,v in pairs(p.bonuses) do if s[k]~=nil then s[k]=s[k]+v end end
    for _,id in ipairs(t.gear) do local e=p.gear[id];local def=C.equipment[e.kind];s[def.kind]=s[def.kind]+def.base*e.tier end
    local pet=t.pet and p.pets[t.pet]
    if pet then
        for i=1,math.min(3,#pet.skills) do
            if i<3 or p.completed>=4 then
                local def=C.skills[pet.skills[i]];s[def.kind]=s[def.kind]+def.values[pet.qualities[i]]
            end
        end
    end
    for _,id in ipairs(p.tower_order) do local a=p.towers[id];if a.family==3 and a.level==6 and a.branch==2 then s.attack=s.attack+18;break end end
    if t.family==2 and t.level==6 and t.branch==2 then s.pierce=s.pierce+30 end
    s.damage=d.attack*C.level_scale[t.level]*(1+s.attack/100)
    s.interval=d.interval/(1+math.min(250,s.speed)/100)
    s.radius=d.range*(1+s.range/100)
    s.cooldown=math.min(40,s.cooldown)
    return s
end
return T
