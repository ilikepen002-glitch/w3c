-- Verify the engine-facing sync/local boundary, independent of rendered UI tests.
local in_local=false
local local_id=2
local players={}
for id=1,4 do
    players[id]={get_id=function()return id end,is_alive=function()return id<=2 end}
end
local built,sent,refreshed,focused,adapted={},{},{},{},{}
local frame_callback
local sync_callback
local leave_callback
log={info=function()end}
y3={config={logic_frame=30,sync={}},player={},ui={},sync={},game={},timer={}}
function y3.player.get_by_id(id)return players[id]end
function y3.player.with_local(callback)
    local previous=in_local;in_local=true
    callback(players[local_id]);in_local=previous
end
function y3.ui.get_ui(player,path)
    assert(not in_local,'initial UI setup must run in synchronized context')
    assert(path=='GameHUD')
    return {set_visible=function(_,visible)assert(not visible)end}
end
function y3.sync.onSync(channel,callback)assert(channel=='spirit_command');sync_callback=callback end
function y3.sync.send(channel,command)
    assert(in_local and channel=='spirit_command')
    sent[#sent+1]=command
    sync_callback(command,players[local_id])
end
function y3.game:event(name,callback)assert(name=='玩家-离开游戏');leave_callback=callback end
function y3.timer.loop_frame(period,callback)assert(period==1);frame_callback=callback;return {}end
package.loaded['spirit.ui']={new=function(game,player,assets,send,focus)
    assert(not in_local,'dynamic controls must not be created inside with_local')
    local id=player:get_id();built[#built+1]=id
    return {send=send,refresh=function()assert(in_local);refreshed[#refreshed+1]=id end,
        adapt_viewport=function()assert(in_local);adapted[#adapted+1]=id end}
end}
package.loaded['spirit.world']={new=function(game,assets)
    return {update=function()end,focus=function(_,id)assert(in_local);focused[#focused+1]=id end}
end}
package.loaded['spirit.assets']={load_icons=function()end}
local runtime=require('spirit.runtime').start()
assert(#built==2 and built[1]==1 and built[2]==2)
assert(runtime.ui==runtime.views[2] and #focused==1 and focused[1]==2)
assert(#adapted==1 and adapted[1]==2,'initial viewport adaptation must be local')
runtime.views[1].send({action='build',family=1,slot=1,epoch=1})
assert(#sent==0,'local player must not submit another player-owned UI intent')
runtime.views[2].send({action='build',family=1,slot=1,epoch=1})
assert(#sent==1 and runtime.game.players[2].slots[1])
assert(not runtime.game.players[1].slots[1])
for i=1,6 do frame_callback()end
assert(#refreshed==1 and refreshed[1]==2,'periodic refresh must target only local view')
assert(#adapted==2 and adapted[2]==2,'resize adaptation must stay local')
leave_callback(nil,{player=players[2]})
runtime.views[2].send({action='build',family=1,slot=2,epoch=1})
assert(#sent==1,'departed players must not send UI commands')
print('PASS synchronized UI construction, local refresh/input ownership and departure guard')
