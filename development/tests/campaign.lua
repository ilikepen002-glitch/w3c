local G=require 'spirit.game'
local C=require 'spirit.config'
local order={1,3,6,8,10,12,2,4,5,7,9,11}
local function cmd(g,p,c)c.epoch=g.epoch;c.request=p.last_request+1;return g:dispatch(p.id,c) end
local function manage(g,p,plan)
    if p.status=='won' or p.status=='lost' or p.status=='left' then return end
    for _,id in ipairs(p.wild_order) do
        if #p.pet_order<12 and p.balls>0 then cmd(g,p,{action='capture',wild_id=id}) end
    end
    for i,id in ipairs(p.pet_order) do
        local pet=p.pets[id];local t=p.towers[p.tower_order[i]]
        if t and not pet.host then cmd(g,p,{action='bind',pet_id=id,version=pet.version,tower_id=t.id,tower_version=t.version}) end
        if #pet.skills<4 and p.open_stones>0 then cmd(g,p,{action='open_slot',pet_id=id,version=pet.version}) end
    end
    for _,id in ipairs(p.offer_order) do
        local offer=p.offers[id];local best,score=1,-1
        local weights={attack=6,speed=6,cooldown=3,boss=5,splash=5,income=4,spirit=4,repair=p.lives<20 and 9 or 0,plunder=1}
        for i,k in ipairs(offer.choices) do if weights[C.contracts[k].kind]>score then best=i;score=weights[C.contracts[k].kind] end end
        cmd(g,p,{action='contract',offer_id=id,choice=best})
    end
    for _=1,16 do
        local selected,cost,gain
        if #p.tower_order<12 then
            local i=#p.tower_order+1;local family=plan[(i-1)%#plan+1]
            selected={action='build',family=family,slot=order[i]};cost=C.towers[family].cost;gain=C.towers[family].attack/C.towers[family].interval/cost
        end
        for _,id in ipairs(p.tower_order) do
            local t=p.towers[id]
            if t.level<6 then
                local d=C.towers[t.family];local price=C.upgrade_costs[t.level+1]
                local roi=d.attack*(C.level_scale[t.level+1]-C.level_scale[t.level])/d.interval/price
                if not gain or roi>gain then selected={action='upgrade',tower_id=id,tower_version=t.version,branch=t.family==1 and 2 or 1};cost=price;gain=roi end
            end
        end
        if not selected or p.gold<cost then break end
        assert(cmd(g,p,selected))
    end
    for _,id in ipairs(p.tower_order) do
        local t=p.towers[id]
        if t.level>=5 then
            if #t.gear<2 and p.gold>=C.gear_costs[1]+250 then
                local kind=#t.gear==0 and 1 or 2
                if cmd(g,p,{action='buy_gear',kind=kind}) then
                    local e=p.gear[p.gear_order[#p.gear_order]]
                    cmd(g,p,{action='equip',gear_id=e.id,gear_version=e.version,tower_id=t.id,tower_version=t.version})
                end
            end
            for _,eid in ipairs(t.gear) do local e=p.gear[eid]
                if e.tier<5 and p.gold>=C.gear_costs[e.tier+1]+600 then cmd(g,p,{action='upgrade_gear',gear_id=e.id,gear_version=e.version}) end
            end
        end
    end
    if p.status=='break' then cmd(g,p,{action='next_wave'}) end
end

local plans={{1,2,3,4,5},{1,1,2,3},{4,5,4,3}}
-- Four independent lanes share only the deterministic game clock and ID allocator.
-- The same purchases and earned rewards as above are used: no injected resources,
-- instant kills, altered wave data, or shortened simulation steps.
local function marker(p)
    return table.concat({p.gold,p.lives,p.balls,p.stones,p.open_stones,p.last_request,
        #p.tower_order,#p.pet_order,#p.gear_order,#p.contracts,p.kills,p.damage,p.status},':')
end
local function isolated_manage(g,p,plan)
    local before={}
    for id,q in pairs(g.players) do if id~=p.id then before[id]=marker(q) end end
    manage(g,p,plan)
    for id,value in pairs(before) do assert(marker(g.players[id])==value,'player '..p.id..' commands changed lane '..id) end
end
local function multiplayer(disruptions)
    local g=G.new({1,2,3,4},disruptions and 81024 or 81023)
    for id=1,4 do
        if not disruptions or id~=4 then isolated_manage(g,g.players[id],plans[(id-1)%#plans+1]) end
    end
    assert(cmd(g,g.players[1],{action='start'}))
    local ticks,left,loss_seen=0,false,false
    local results={}
    while g.status~='over' and ticks<100000 do
        if disruptions and not left and g.players[1].completed>=8 then
            g:leave(1);left=true
            assert(g.host==2,'host must transfer after the first player leaves')
            assert(#g.players[1].tower_order==0 and #g.players[1].enemy_order==0,'departed lane must release combat objects')
        end
        if ticks%30==0 then
            for id=1,4 do
                if not disruptions or id~=4 then isolated_manage(g,g.players[id],plans[(id-1)%#plans+1]) end
            end
        end
        g:step(C.dt)
        for _,event in ipairs(g:drain_events()) do
            assert(g.players[event.player],'events must retain a valid owner')
            if event.kind=='result' then
                assert(not results[event.player],'result must occur once per lane')
                results[event.player]=event.data.won and 'won' or 'lost'
            end
        end
        if disruptions and g.players[4].status=='lost' then
            loss_seen=true
            assert(#g.players[4].enemy_order==0,'lost lane must discard enemies')
            if g.players[2].status=='combat' or g.players[3].status=='combat' then
                assert(g.status=='playing','one defeated lane must not end the shared game')
            end
        end
        for id=1,4 do
            local p=g.players[id]
            assert(p.gold>=0 and p.balls>=0 and p.stones>=0 and p.open_stones>=0,'negative multiplayer resources')
        end
        ticks=ticks+1
    end
    assert(g.status=='over','multiplayer campaign exceeded time budget')
    for id=1,4 do
        local p=g.players[id]
        print(('MULTIPLAYER disruption=%s player=%d result=%s wave=%d lives=%d time=%.0f gold=%d kills=%d'):format(
            tostring(disruptions),id,p.status,p.completed,p.lives,g.time,p.gold,p.kills))
        if not disruptions or id==2 or id==3 then
            assert(p.status=='won' and p.completed==32 and p.lives>0 and results[id]=='won','surviving lane did not finish 32 waves')
            assert(#p.contracts==7 and #p.offer_order==0,'surviving lane did not claim seven contracts')
        end
    end
    if disruptions then
        assert(left and loss_seen and g.players[1].status=='left' and g.players[4].status=='lost','departure and natural defeat must both occur')
        assert(results[1]==nil and results[4]=='lost','departed player must not receive a victory')
    end
end
multiplayer(false)
multiplayer(true)
for index,plan in ipairs(plans) do
    local g=G.new({1},100+index);local p=g.players[1]
    manage(g,p,plan);cmd(g,p,{action='start'})
    local ticks=0
    while g.status~='over' and ticks<100000 do
        if ticks%30==0 then manage(g,p,plan) end
        g:step(C.dt)
        for _,event in ipairs(g:drain_events()) do
            if event.kind=='leak' and event.data.boss then print(('BOSS LEAK plan=%d wave=%d hp=%.0f/%.0f'):format(index,event.data.wave,event.data.hp,event.data.max_hp)) end
        end
        ticks=ticks+1
    end
    local levels={};for _,id in ipairs(p.tower_order) do levels[#levels+1]=p.towers[id].level end
    print(('CAMPAIGN %d result=%s wave=%d lives=%d time=%.0f gold=%d kills=%d damage=%.0f levels=%s pets=%d loot=%d'):format(
        index,p.status,p.completed,p.lives,g.time,p.gold,p.kills,p.damage,table.concat(levels,','),#p.pet_order,p.loot_gold))
    assert(p.status=='won' and p.completed==32 and p.lives>0,'full normal campaign failed for plan '..index)
    assert(#p.contracts==7 and #p.offer_order==0,'all seven usable contracts must have been claimed')
    assert(p.gold>=0 and p.balls>=0 and p.stones>=0 and p.open_stones>=0,'negative resources')
end
