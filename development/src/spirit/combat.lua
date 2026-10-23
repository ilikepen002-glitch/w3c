local C=require 'spirit.config'
local U=require 'spirit.util'
local Towers=require 'spirit.towers'
local B={}
local lengths,total={},0
for i=1,#C.path-1 do
    local a,b=C.path[i],C.path[i+1]
    lengths[i]=math.sqrt(U.distance2(a[1],a[2],b[1],b[2]));total=total+lengths[i]
end
B.path_length=total
function B.position(distance)
    for i,len in ipairs(lengths) do
        if distance<=len then
            local a,b=C.path[i],C.path[i+1];local q=distance/len
            return a[1]+(b[1]-a[1])*q,a[2]+(b[2]-a[2])*q
        end
        distance=distance-len
    end
    return C.path[#C.path][1],C.path[#C.path][2]
end
function B.spawn(g,p,w,challenge)
    local id=g:uid();local hp=math.floor(w.hp*C.difficulties[g.difficulty].hp*(challenge and 1.35 or 1))
    local e={id=id,hp=hp,max_hp=hp,progress=0,x=C.path[1][1],y=C.path[1][2],speed=w.speed,armor=w.armor,
        regen=w.regen,boss=w.boss,elite=w.elite,bounty=w.bounty,loot=4,loot_at=0,slows={},poisons={},stun_until=0,dead=false}
    p.enemies[id]=e;p.enemy_order[#p.enemy_order+1]=id
    g:emit('spawn',p.id,{enemy_id=id})
end
local function targets(p,x,y,radius,limit)
    local found={}
    for _,id in ipairs(p.enemy_order) do
        local e=p.enemies[id]
        if not e.dead and U.distance2(x,y,e.x,e.y)<=radius*radius then found[#found+1]=e end
    end
    table.sort(found,function(a,b) if a.progress==b.progress then return a.id<b.id end;return a.progress>b.progress end)
    while #found>limit do found[#found]=nil end
    return found
end
local function loot(g,p,t,e,count,s)
    count=math.min(count,e.loot)
    if count<=0 then return end
    local gold=math.floor(count*(1+math.floor(p.wave/8))*(1+(s and s.plunder or 0)/100))
    e.loot=e.loot-count;p.gold=p.gold+gold;p.loot_gold=p.loot_gold+gold
    g:emit('loot',p.id,{tower_id=t.id,enemy_id=e.id,amount=gold})
end
function B.damage(g,p,t,e,amount,magic,secondary,s)
    if e.dead or amount<=0 then return 0 end
    local armor=magic and e.armor*0.35 or e.armor*(1-math.min(85,s and s.pierce or 0)/100)
    local actual=math.max(1,amount*(1-armor))
    local dealt=math.min(e.hp,actual)
    e.hp=e.hp-dealt;t.damage=t.damage+dealt;p.damage=p.damage+dealt
    g:emit('damage',p.id,{tower_id=t.id,enemy_id=e.id,amount=dealt,magic=magic})
    if not secondary and g.time>=e.loot_at then loot(g,p,t,e,1,s);e.loot_at=g.time+0.5 end
    if e.hp<=0 then
        e.dead=true;t.kills=t.kills+1;p.kills=p.kills+1;p.gold=p.gold+e.bounty
        -- Killing fast pays every unclaimed loot charge: no incentive to stall.
        loot(g,p,t,e,e.loot,s)
        g:emit('death',p.id,{enemy_id=e.id,tower_id=t.id,boss=e.boss})
        if not secondary and t.family==5 then
            local power=t.level==6 and t.branch==1 and 1.7 or 0.55
            local victims=targets(p,e.x,e.y,450,8)
            for _,other in ipairs(victims) do B.damage(g,p,t,other,(s and s.damage or amount)*power,true,true,s) end
        end
    end
    return dealt
end
local function slow(g,t,e,percent,duration,elemental)
    e.slows[t.id*2+(elemental and 1 or 0)]={source=t.id,value=percent*(e.boss and 0.5 or 1),until_time=g.time+duration}
end
local function poison(g,t,e,power,elemental)
    local key=t.id*2+(elemental and 1 or 0)
    local old=e.poisons[key]
    -- Refresh duration without postponing the next tick on fast-attacking towers.
    local next_tick=old and old.until_time>=g.time and old.next_tick or g.time+1
    e.poisons[key]={source=t.id,damage=power,next_tick=next_tick,until_time=g.time+4}
end
local function attack(g,p,t,s)
    local count=t.family==1 and (t.level==6 and t.branch==1 and 4 or t.level>=3 and 3 or 2) or 1
    local list=targets(p,t.x,t.y,s.radius,count)
    if #list==0 then return false end
    t.hit_count=t.hit_count+1
    local critical=(t.family==2 and U.random(g,100)<=25) or (s.critical>0 and U.random(g,100)<=s.critical)
    local multiplier=critical and (t.family==2 and t.level==6 and t.branch==2 and 3.2 or 1.8) or 1
    for index,e in ipairs(list) do
        g:emit('attack',p.id,{tower_id=t.id,enemy_id=e.id,family=t.family,x=t.x,y=t.y,target_x=e.x,target_y=e.y,critical=critical})
        local amount=s.damage*multiplier
        if e.boss or e.elite then amount=amount*(1+s.boss/100+(t.family==1 and t.level==6 and t.branch==2 and 0.8 or 0)) end
        if e.hp<e.max_hp*0.5 then amount=amount*(1+s.execute/100) end
        if t.family==5 and t.level==6 and t.branch==2 then
            t.streak=t.last_target==e.id and math.min(15,t.streak+1) or 0;t.last_target=e.id;amount=amount*(1+t.streak*0.08)
        end
        if t.family==4 then
            local boost=t.level==6 and t.branch==2 and 1.7 or 1
            poison(g,t,e,s.damage*0.35*boost);slow(g,t,e,t.level==6 and t.branch==2 and 0.4 or 0.23,2.5)
            if t.level==6 and t.branch==1 then for _,v in ipairs(targets(p,e.x,e.y,500,3)) do poison(g,t,v,s.damage*0.35) end end
        end
        if t.family==3 then
            slow(g,t,e,0.18,2)
            if t.hit_count%4==0 then
                e.stun_until=math.max(e.stun_until,g.time+(e.boss and 0.15 or 0.5))
                if t.level==6 and t.branch==1 then
                    for _,v in ipairs(targets(p,e.x,e.y,700,4)) do B.damage(g,p,t,v,s.damage*0.8,true,true,s) end
                end
            end
        end
        B.damage(g,p,t,e,amount,false,false,s)
        if index==1 then
            if s.double>0 and U.random(g,100)<=s.double then B.damage(g,p,t,e,s.damage*0.6,false,true,s) end
            if t.hit_count%4==0 and s.heavy>0 then B.damage(g,p,t,e,s.damage*s.heavy/100,false,true,s) end
            local splash=s.splash+(t.family==2 and t.level==6 and t.branch==1 and t.hit_count%4==0 and 100 or 0)
            if splash>0 then
                for _,other in ipairs(targets(p,e.x,e.y,420,8)) do
                    if other.id~=e.id then B.damage(g,p,t,other,s.damage*splash/100,false,true,s) end
                end
            end
        end
    end
    return true
end
local function active(g,p,t,s)
    local pet=t.pet and p.pets[t.pet]
    if not pet or not pet.skills[4] or p.completed<8 or pet.active_ready>g.time then return end
    local victims=targets(p,t.x,t.y,s.radius+150,4)
    if #victims==0 then return end
    local def=C.skills[pet.skills[4]];local power=s.damage*def.values[pet.qualities[4]]/100*(1+s.spirit/100)
    pet.active_ready=g.time+6*(1-s.cooldown/100)
    local element=C.element(pet.species)
    if element==4 then victims=targets(p,victims[1].x,victims[1].y,650,12) end
    for _,e in ipairs(victims) do
        if element==2 then poison(g,t,e,power,true)
        else B.damage(g,p,t,e,power,true,true,s) end
        if element==3 then slow(g,t,e,0.4,3,true) end
        if element==5 then e.stun_until=math.max(e.stun_until,g.time+(e.boss and 0.25 or 0.8)) end
    end
    g:emit('active',p.id,{tower_id=t.id,enemy_id=victims[1].id,element=element,x=t.x,y=t.y,target_x=victims[1].x,target_y=victims[1].y})
end
function B.step(g,p,dt)
    -- Source ids are sorted to keep all client callbacks and rewards deterministic.
    for _,id in ipairs(p.enemy_order) do
        local e=p.enemies[id]
        if not e.dead then
            local sources={};for source in pairs(e.poisons) do sources[#sources+1]=source end;table.sort(sources)
            for _,source in ipairs(sources) do
                local poison_effect=e.poisons[source];local t=p.towers[poison_effect.source]
                if not t or poison_effect.until_time<g.time then e.poisons[source]=nil
                elseif g.time>=poison_effect.next_tick then
                    poison_effect.next_tick=poison_effect.next_tick+1
                    B.damage(g,p,t,e,poison_effect.damage,true,true,Towers.stats(p,t))
                end
            end
            if not e.dead then
                local strongest=0
                for source,s in pairs(e.slows) do
                    if s.until_time<g.time or not p.towers[s.source] then e.slows[source]=nil
                    else strongest=math.max(strongest,s.value) end
                end
                if g.time>=e.stun_until then e.progress=e.progress+e.speed*(1-strongest)*dt end
                e.x,e.y=B.position(e.progress)
                if e.regen>0 then e.hp=math.min(e.max_hp,e.hp+e.max_hp*e.regen*dt) end
                if e.progress>=total then
                    e.dead=true;p.lives=math.max(0,p.lives-(e.boss and 10 or e.elite and 2 or 1));p.leaks=p.leaks+1
                    -- The final boss must be defeated; surviving its leak is not a victory.
                    if e.boss and p.wave==C.waves then p.lives=0 end
                    g:emit('leak',p.id,{enemy_id=e.id,boss=e.boss,hp=e.hp,max_hp=e.max_hp,wave=p.wave})
                end
            end
        end
    end
    for _,id in ipairs(p.tower_order) do
        local t=p.towers[id];local s=Towers.stats(p,t)
        if t.next_attack<=g.time and attack(g,p,t,s) then t.next_attack=g.time+s.interval end
        active(g,p,t,s)
    end
    for i=#p.enemy_order,1,-1 do
        local id=p.enemy_order[i]
        if p.enemies[id].dead then p.enemies[id]=nil;table.remove(p.enemy_order,i) end
    end
end
return B
