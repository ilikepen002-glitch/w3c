local U={}
function U.copy(t)
    if type(t)~='table' then return t end
    local r={}; for k,v in pairs(t) do r[k]=U.copy(v) end; return r
end
function U.integer(n,lo,hi) return type(n)=='number' and n==math.floor(n) and n>=lo and n<=hi end
function U.distance2(ax,ay,bx,by) return (ax-bx)^2+(ay-by)^2 end
function U.clamp(n,lo,hi) return math.max(lo,math.min(hi,n)) end
-- Integer RNG: bounded products remain exactly representable by Y3 fixed point.
-- Randomness is used only from synchronized simulation/command dispatch.
function U.random(g,n)
    g.rng=(g.rng*25173+13849)%65536
    return math.floor(g.rng*n/65536)+1
end
function U.remove_value(list,v) for i=#list,1,-1 do if list[i]==v then table.remove(list,i); return end end end
return U
