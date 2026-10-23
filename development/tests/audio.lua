local Audio=require 'spirit.audio'
local calls,warnings={},{}
local unavailable=false
y3={player={get_by_id=function(id)return {id=id} end},sound={play=function(player,key,options)
    calls[#calls+1]={player=player.id,key=key,loop=options.loop}
    if unavailable then return nil end
    local sound={stopped=false}
    function sound:set_volume(target,volume)assert(target.id==player.id and volume>0 and volume<=100) end
    function sound:stop(target,immediately)assert(target.id==player.id and immediately);self.stopped=true end
    calls[#calls].sound=sound
    return sound
end}}
log={warn=function(message,key)warnings[#warnings+1]={message,key} end}
local function event(kind,id,data)return {kind=kind,player=id,data=data or {}} end
local audio=Audio.new()
audio:update({event('attack',1),event('loot',1),event('capture',1),event('offer',1),event('wave',2)},0)
assert(#calls==2,'combat attacks and loot must not flood sound; same-player rewards must merge')
local seen={};for _,c in ipairs(calls) do seen[c.player]=c;assert(c.loop==false) end
assert(seen[1].key==100004 and seen[2].key==100003,'sounds must target their event owner')
audio:update({event('capture',1),event('wave',2)},.1)
assert(#calls==2,'rapid non-result notifications must be throttled independently per player')
audio:update({event('wave',1),event('result',1,{won=true}),event('result',2,{won=false})},.2)
assert(#calls==4 and seen[1].sound.stopped and seen[2].sound.stopped,'result must replace existing sounds')
local outcomes={};for i=3,4 do outcomes[calls[i].player]=calls[i] end
assert(outcomes[1].key==103162 and outcomes[2].key==103157,'result priority and outcome sound')
audio:update({event('capture',1),event('leave',1),event('wave',1)},1)
assert(#calls==4 and outcomes[1].sound.stopped and audio.playing[1]==nil,'leave cancels pending and live sound')
audio:update({event('restart',2)},0)
assert(outcomes[2].sound.stopped and next(audio.playing)==nil and next(audio.next_at)==nil,'restart stops all old sound and resets cooldown clock')
audio:update({event('wave',2)},0)
assert(#calls==5,'new campaign sound must not be suppressed by previous campaign time')
unavailable=true
audio:update({event('capture',3)},2)
audio:update({event('capture',3)},3)
assert(#warnings==1 and warnings[1][1]=='SPIRIT_SOUND_UNAVAILABLE','missing resource is explicit and logged once per key')
audio:clear()
print('PASS audio owner routing, batching, cooldown, outcome priority, leave/restart cleanup and missing resource reporting')
