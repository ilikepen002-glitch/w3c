-- Presentation-only particles. Bounded lifetimes and count; never modify combat.
local Audio=require 'spirit.audio'
local FX={};FX.__index=FX
local palette={{1,.78,.28},{.28,1,.53},{.25,.76,1},{1,.35,.12},{.83,.64,.31}}
local family_colors={{1,.83,.42},{1,.45,.24},{.35,.75,1},{.3,1,.48},{.75,.42,1}}
-- Resource keys verified in the official TD and casual-TD templates.
local arrow,blade,fire,water,portal=102643,102602,103353,101043,102674
local impacts={101819,100115,101393,103354,101425}
local projectiles={arrow,blade,water,100229,101252}
function FX.new(world)return setmetatable({world=world,flights={},audio=Audio.new()},FX) end
function FX:clear()
    for _,f in ipairs(self.flights) do f.particle:remove() end
    self.flights={}
    self.audio:clear()
end
function FX:burst(player,x,y,color,scale,element)
    local particle=y3.particle.create{type=element and impacts[element] or 102730,target=self.world:point(player,x,y),scale=scale*self.world.scale,time=.7,height=15}
    particle:set_color(color[1],color[2],color[3],.85)
end
function FX:launch(player,d,element)
    if #self.flights>=192 then return end
    local color=element and palette[element] or family_colors[d.family]
    local kind=element and ({arrow,100229,water,fire,blade})[element] or projectiles[d.family]
    local dx,dy=d.target_x-d.x,d.target_y-d.y
    local duration=math.max(.12,math.min(.32,math.sqrt(dx*dx+dy*dy)/4200))
    local particle=y3.particle.create{type=kind,target=self.world:point(player,d.x,d.y),height=110*self.world.scale,
        angle=math.deg(math.atan(dy,dx)),scale=(element and 1.3 or .65)*self.world.scale,time=duration+.1,immediate=true}
    particle:set_color(color[1],color[2],color[3],1)
    self.flights[#self.flights+1]={particle=particle,player=player,x=d.x,y=d.y,dx=dx,dy=dy,
        start=self.world.game.time,duration=duration,color=color,element=element,critical=d.critical}
end
function FX:update(events)
    local game=self.world.game
    self.audio:update(events,game.time)
    for i=#self.flights,1,-1 do
        local f=self.flights[i];local q=(game.time-f.start)/f.duration
        if q>=1 or game.status=='over' then
            f.particle:remove()
            if game.status~='over' and (f.element or f.critical) then
                self:burst(f.player,f.x+f.dx,f.y+f.dy,f.color,f.element and 1.1 or .35,f.element)
            end
            table.remove(self.flights,i)
        else
            f.particle:set_point(self.world:point(f.player,f.x+f.dx*q,f.y+f.dy*q))
        end
    end
    for _,event in ipairs(events) do
        local d=event.data
        if event.kind=='attack' then self:launch(event.player,d)
        elseif event.kind=='active' then self:launch(event.player,d,d.element)
        elseif event.kind=='build' then
            local t=game.players[event.player].towers[d.tower_id]
            if t then self:burst(event.player,t.x,t.y,palette[2],.9) end
        end
    end
end
return FX
