local G=require 'spirit.game'
local C=require 'spirit.config'
local T=require 'spirit.towers'
local P=require 'spirit.pets'
local B=require 'spirit.combat'
local passed=0
local function test(name,f)
    local ok,err=pcall(f)
    if not ok then error(name..': '..tostring(err)) end
    passed=passed+1;print('PASS '..name)
end
local function command(g,p,c)
    c.request=g.players[p].last_request+1;c.epoch=g.epoch
    return g:dispatch(p,c)
end
local function build(g,p,family,slot)
    assert(command(g,p,{action='build',family=family or 1,slot=slot or 1}))
    return g.players[p].towers[g.players[p].slots[slot or 1]]
end
local function capture(g,p)
    assert(command(g,p,{action='capture',wild_id=g.players[p].wild_order[1]}))
    return g.players[p].pets[g.players[p].pet_order[1]]
end
test('invalid build preserves gold and slots',function()
    local g=G.new({1});local p=g.players[1];local gold=p.gold
    for _,c in ipairs({{action='build',family=0,slot=1},{action='build',family=1,slot=99},{action='build',family=1.5,slot=1}}) do assert(not command(g,1,c)) end
    assert(p.gold==gold and #p.tower_order==0)
end)
test('duplicate request cannot spend twice',function()
    local g=G.new({1});local c={epoch=1,request=1,action='build',family=1,slot=1}
    assert(g:dispatch(1,c));local gold=g.players[1].gold
    assert(not g:dispatch(1,c));assert(g.players[1].gold==gold and #g.players[1].tower_order==1)
end)
test('captured spirit is real, first capture guaranteed',function()
    for seed=1,40 do
        local g=G.new({1},seed);local p=g.players[1];local balls=p.balls;local pet=capture(g,1)
        assert(pet.species>=1 and pet.species<=15 and #pet.skills>=2 and p.balls==balls-1)
    end
end)
test('collection full does not consume capture ball',function()
    local g=G.new({1});local p=g.players[1]
    for i=1,20 do P.create(g,p,(i-1)%15+1) end
    local balls=p.balls;assert(not command(g,1,{action='capture',wild_id=p.wild_order[1]}));assert(p.balls==balls)
end)
test('binding and recall affect combat stats',function()
    local g=G.new({1});local p=g.players[1];local t=build(g,1);local pet=capture(g,1)
    pet.skills[1]=1;pet.qualities[1]=4
    local before=T.stats(p,t).damage
    assert(command(g,1,{action='bind',pet_id=pet.id,version=pet.version,tower_id=t.id,tower_version=t.version}))
    assert(T.stats(p,t).damage>before*1.3)
    assert(command(g,1,{action='recall',pet_id=pet.id,version=pet.version}));assert(T.stats(p,t).damage==before)
end)
test('player cannot bind another player spirit',function()
    local g=G.new({1,2});local t=build(g,1);local pet=capture(g,2)
    assert(not command(g,1,{action='bind',pet_id=pet.id,version=pet.version,tower_id=t.id,tower_version=t.version}))
    assert(not pet.host and not t.pet)
end)
test('replacement binding cleans both old relations',function()
    local g=G.new({1});local p=g.players[1];local a=build(g,1,1,1);local b=build(g,1,2,2)
    local pet=capture(g,1)
    assert(command(g,1,{action='bind',pet_id=pet.id,version=pet.version,tower_id=a.id,tower_version=a.version}))
    assert(command(g,1,{action='bind',pet_id=pet.id,version=pet.version,tower_id=b.id,tower_version=b.version}))
    assert(a.pet==nil and b.pet==pet.id and pet.host==b.id)
end)
test('reroll is charged once; proposal survives snapshot and cancel',function()
    local g=G.new({1});local p=g.players[1];local pet=capture(g,1);local old=pet.skills[1];local stones=p.stones
    assert(command(g,1,{action='reroll',pet_id=pet.id,version=pet.version,slot=1}))
    local proposal=pet.proposal.id
    local snapshot=g:snapshot(1);snapshot.pets[pet.id].proposal=nil
    assert(pet.proposal.id==proposal and p.stones==stones-2)
    assert(not command(g,1,{action='reroll',pet_id=pet.id,version=pet.version,slot=1}))
    assert(p.stones==stones-2)
    assert(command(g,1,{action='resolve',pet_id=pet.id,version=pet.version,proposal_id=proposal,adopt=false}))
    assert(pet.skills[1]==old and not pet.proposal)
end)
test('stale candidate cannot replace current skill',function()
    local g=G.new({1});local pet=capture(g,1)
    assert(command(g,1,{action='reroll',pet_id=pet.id,version=pet.version,slot=1}))
    local old=pet.skills[1];assert(not command(g,1,{action='resolve',pet_id=pet.id,version=pet.version,proposal_id=-1,adopt=true}))
    assert(pet.skills[1]==old and pet.proposal)
end)
test('adopt applies exact candidate without second payment',function()
    local g=G.new({1});local p=g.players[1];local pet=capture(g,1)
    assert(command(g,1,{action='reroll',pet_id=pet.id,version=pet.version,slot=2}))
    local pr=pet.proposal;local stones=p.stones
    assert(command(g,1,{action='resolve',pet_id=pet.id,version=pet.version,proposal_id=pr.id,adopt=true}))
    assert(pet.skills[2]==pr.skill and pet.qualities[2]==pr.quality and p.stones==stones)
end)
test('sold tower returns pet and gear; old tower commands rejected',function()
    local g=G.new({1});local p=g.players[1];local t=build(g,1);local pet=capture(g,1)
    assert(command(g,1,{action='bind',pet_id=pet.id,version=pet.version,tower_id=t.id,tower_version=t.version}))
    assert(command(g,1,{action='buy_gear',kind=1}));local e=p.gear[p.gear_order[1]]
    assert(command(g,1,{action='equip',gear_id=e.id,gear_version=e.version,tower_id=t.id,tower_version=t.version}))
    local gold=p.gold;assert(command(g,1,{action='sell',tower_id=t.id,tower_version=t.version,confirm=true}))
    assert(p.gold==gold+64 and not pet.host and not e.tower and not p.towers[t.id])
    assert(not command(g,1,{action='upgrade',tower_id=t.id,tower_version=t.version}))
end)
test('duplicate equipment type rejected without moving source',function()
    local g=G.new({1});local p=g.players[1];p.gold=1000;local t=build(g,1)
    for i=1,2 do assert(command(g,1,{action='buy_gear',kind=1})) end
    local a,b=p.gear[p.gear_order[1]],p.gear[p.gear_order[2]]
    assert(command(g,1,{action='equip',gear_id=a.id,gear_version=a.version,tower_id=t.id,tower_version=t.version}))
    assert(not command(g,1,{action='equip',gear_id=b.id,gear_version=b.version,tower_id=t.id,tower_version=t.version}))
    assert(#t.gear==1 and not b.tower)
end)
test('quick kill receives all remaining bounded loot',function()
    local g=G.new({1});local p=g.players[1];local t=build(g,1);p.wave=1
    B.spawn(g,p,C.wave(1),false);local e=p.enemies[p.enemy_order[1]];local before=p.gold
    B.damage(g,p,t,e,100000,false,false,T.stats(p,t))
    assert(e.dead and e.loot==0 and p.gold==before+e.bounty+4)
    local gold=p.gold;B.damage(g,p,t,e,100000,false,false,T.stats(p,t));assert(p.gold==gold)
end)
test('contract must be from current offer and claimed once',function()
    local g=G.new({1});local p=g.players[1];g:offer(p);local id=p.offer_order[1]
    assert(not command(g,1,{action='contract',offer_id=id,choice=9}))
    assert(command(g,1,{action='contract',offer_id=id,choice=1}))
    assert(not command(g,1,{action='contract',offer_id=id,choice=1}) and #p.contracts==1)
end)
test('unbuilt lane eventually loses, terminal state rejects spending',function()
    local g=G.new({1});command(g,1,{action='start'})
    for i=1,4000 do g:step(0.1);g:drain_events();if g.status=='over' then break end end
    local p=g.players[1];assert(p.status=='lost' and p.lives==0)
    local gold=p.gold;assert(not command(g,1,{action='build',family=1,slot=1}));assert(p.gold==gold)
end)
test('boss leaks cost ten lives',function()
    local g=G.new({1});local p=g.players[1];p.wave=8
    B.spawn(g,p,C.wave(8),false);local e=p.enemies[p.enemy_order[1]];e.progress=B.path_length-1
    B.step(g,p,0.1);assert(p.lives==20 and #p.enemy_order==0)
end)
test('departure cleans entities and reassigns lobby host',function()
    local g=G.new({1,2});local t=build(g,1);local pet=capture(g,1);local p=g.players[1]
    assert(command(g,1,{action='bind',pet_id=pet.id,version=pet.version,tower_id=t.id,tower_version=t.version}))
    assert(command(g,1,{action='buy_gear',kind=1}));local e=p.gear[p.gear_order[1]]
    assert(command(g,1,{action='equip',gear_id=e.id,gear_version=e.version,tower_id=t.id,tower_version=t.version}))
    g:leave(1)
    assert(g.host==2 and g.players[1].status=='left' and #g.players[1].tower_order==0)
    assert(not pet.host and not e.tower)
    assert(command(g,2,{action='start'}));assert(not command(g,1,{action='build',family=1,slot=1}))
end)

test('final boss escape loses even with a full life pool',function()
    local g=G.new({1});local p=g.players[1];g.status='playing';p.status='combat';p.wave=32
    p.wave_data=C.wave(32);p.spawned=1
    B.spawn(g,p,p.wave_data,false);p.enemies[p.enemy_order[1]].progress=B.path_length-1
    g:step(0.1)
    assert(p.status=='lost' and p.lives==0 and p.completed~=32 and g.status=='over')
end)

test('untimed lobby preserves first capture and preparation',function()
    local g=G.new({1});local p=g.players[1];local id=p.wild_order[1]
    for _=1,500 do g:step(1) end
    assert(g.time==0 and p.wild[id] and p.status=='ready')
    assert(command(g,1,{action='capture',wild_id=id}))
end)
test('same synchronized command stream yields same simulation',function()
    local a,b=G.new({1,2},427),G.new({1,2},427)
    local function setup(g)
        for id=1,2 do build(g,id,1,1);build(g,id,4,2);capture(g,id) end
        command(g,1,{action='start'})
    end
    setup(a);setup(b)
    for i=1,2000 do a:step(0.05);b:step(0.05);a:drain_events();b:drain_events() end
    for id=1,2 do
        local p,q=a.players[id],b.players[id]
        assert(p.gold==q.gold and p.lives==q.lives and p.damage==q.damage and p.kills==q.kills and #p.enemy_order==#q.enemy_order)
    end
    assert(a.rng==b.rng)
end)
test('restart requires finished campaign and host; old epoch cannot affect new run',function()
    local g=G.new({1,2});build(g,1);local epoch=g.epoch;local serial=g.serial
    assert(not command(g,1,{action='restart'}))
    g.status='over';g.players[1].status='lost';g.players[2].status='won'
    assert(not command(g,2,{action='restart'}))
    assert(command(g,1,{action='restart'}))
    assert(g.epoch==epoch+1 and g.status=='lobby' and g.time==0 and g.serial>serial)
    assert(#g.players[1].tower_order==0 and g.players[1].gold==C.start_gold)
    assert(not g:dispatch(1,{action='build',family=1,slot=1,epoch=epoch,request=1000}))
    assert(command(g,1,{action='build',family=1,slot=1}))
end)

test('gear recycle refunds once and refuses equipped or stale objects',function()
    local g=G.new({1});local p=g.players[1];p.gold=5000;local t=build(g,1)
    assert(command(g,1,{action='buy_gear',kind=1}));local e=p.gear[p.gear_order[1]]
    assert(command(g,1,{action='upgrade_gear',gear_id=e.id,gear_version=e.version}))
    assert(command(g,1,{action='equip',gear_id=e.id,gear_version=e.version,tower_id=t.id,tower_version=t.version}))
    assert(not command(g,1,{action='recycle_gear',gear_id=e.id,gear_version=e.version,confirm=true}))
    assert(command(g,1,{action='unequip',gear_id=e.id,gear_version=e.version}))
    local gold=p.gold
    assert(command(g,1,{action='recycle_gear',gear_id=e.id,gear_version=e.version,confirm=true}))
    assert(p.gold==gold+math.floor((C.gear_costs[1]+C.gear_costs[2])*.5) and #p.gear_order==0)
    local after=p.gold;assert(not command(g,1,{action='recycle_gear',gear_id=e.id,gear_version=e.version,confirm=true}))
    assert(p.gold==after)
end)

test('frequent poison refresh still ticks and preserves separate elemental source',function()
    local g=G.new({1});local p=g.players[1];local t=build(g,1,4,1);p.wave=1
    local pet=P.create(g,p,4);pet.skills={1,4,7,11};pet.qualities={1,1,1,1};pet.host=t.id;t.pet=pet.id;p.completed=8
    B.spawn(g,p,C.wave(1),false);local e=p.enemies[p.enemy_order[1]]
    e.hp=100000;e.max_hp=100000;e.x=t.x;e.y=t.y;e.speed=0;e.progress=450
    p.bonuses.speed=200
    for _=1,100 do g.time=g.time+1/30;B.step(g,p,1/30) end
    local normal,elemental=e.poisons[t.id*2],e.poisons[t.id*2+1]
    assert(normal and elemental and normal.next_tick>g.time and elemental.next_tick>g.time)
    assert(t.damage>t.hit_count*T.stats(p,t).damage,'poison must deal damage while refreshing')
end)
print(('PASS %d gameplay scenarios'):format(passed))
