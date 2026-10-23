local C=require 'spirit.config'
local G=require 'spirit.game'
local UI=require 'spirit.ui'
local World=require 'spirit.world'
local A=require 'spirit.assets'
local Runtime={}
function Runtime.start()
    A.load_icons()
    local ids={}
    for id=1,4 do local player=y3.player.get_by_id(id);if player and player:is_alive() then ids[#ids+1]=id end end
    assert(#ids>0,'未找到参与游戏的玩家')
    local game=G.new(ids,20261023)
    local world=World.new(game,A)
    local local_ui
    local views={}
    y3.config.sync.send_in_single_mode=true
    y3.sync.onSync('spirit_command',function(command,sender)
        if not sender then return end
        local ok,reason=game:dispatch(sender:get_id(),command)
        log.info('SPIRIT_COMMAND',sender:get_id(),type(command)=='table' and command.action or '?',ok,reason)
    end)
    y3.game:event('玩家-离开游戏',function(_,data)game:leave(data.player:get_id())end)
    -- create_ui_comp is a synchronized API. Every client creates the same player-owned
    -- trees in the same order; only subsequent view refresh and input stay local.
    for _,id in ipairs(ids) do
        local player=y3.player.get_by_id(id)
        local request=0
        y3.ui.get_ui(player,'GameHUD'):set_visible(false)
        views[id]=UI.new(game,player,A,function(command)
            y3.player.with_local(function(sender)
                if sender:get_id()~=id then return end
                local current=game.players[id]
                if not current or current.status=='left' then return end
                request=math.max(request,current.last_request)+1
                command.request=request
                y3.sync.send('spirit_command',command)
            end)
        end,function(focus_id)world:focus(focus_id)end)
    end
    y3.player.with_local(function(player)
        local_ui=views[player:get_id()]
        if not local_ui then return end
        local_ui:adapt_viewport()
        world:focus(player:get_id())
    end)
    local frame_time=1/y3.config.logic_frame
    local frames=0
    local timer=y3.timer.loop_frame(1,function()
        game:step(frame_time);world:update(game:drain_events());frames=frames+1
        if frames%math.max(1,math.floor(y3.config.logic_frame/5))==0 and local_ui then
            y3.player.with_local(function()
                local_ui:adapt_viewport()
                local_ui:refresh()
            end)
        end
    end)
    Runtime.game=game;Runtime.world=world;Runtime.ui=local_ui;Runtime.views=views;Runtime.timer=timer
    log.info('SPIRIT_READY',C.version,'players',#ids,'fps',y3.config.logic_frame)
    return Runtime
end
return Runtime
