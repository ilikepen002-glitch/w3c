-- Player-targeted presentation. Sound handles never affect synchronized gameplay.
local Audio={};Audio.__index=Audio
local sounds={reward=100004,wave=100003,win=103162,lose=103157}
local priorities={capture=1,offer=2,wave=3,result=4}
function Audio.new()return setmetatable({playing={},next_at={},missing={}},Audio) end
function Audio:stop(id)
    local record=self.playing[id]
    if record then record.sound:stop(record.player,true);self.playing[id]=nil end
    self.next_at[id]=nil
end
function Audio:clear()
    for id in pairs(self.playing) do self:stop(id) end
    self.next_at={}
end
function Audio:update(events,time)
    local chosen,departed={},{}
    for _,event in ipairs(events) do
        local id=event.player
        if event.kind=='restart' then self:clear();chosen={};departed={}
        elseif event.kind=='leave' then self:stop(id);departed[id]=true;chosen[id]=nil
        elseif priorities[event.kind] and not departed[id] then
            local previous=chosen[id]
            if not previous or priorities[event.kind]>priorities[previous.kind] then chosen[id]=event end
        end
    end
    for id,event in pairs(chosen) do
        if event.kind=='result' or time>=(self.next_at[id] or 0) then
            local key=event.kind=='result' and (event.data.won and sounds.win or sounds.lose)
                or event.kind=='wave' and sounds.wave or sounds.reward
            self:stop(id)
            local player=y3.player.get_by_id(id)
            local sound=y3.sound.play(player,key,{loop=false})
            if sound then
                sound:set_volume(player,event.kind=='result' and 70 or 45)
                self.playing[id]={player=player,sound=sound}
            elseif not self.missing[key] then
                self.missing[key]=true
                log.warn('SPIRIT_SOUND_UNAVAILABLE',key)
            end
            self.next_at[id]=time+.8
        end
    end
end
return Audio
