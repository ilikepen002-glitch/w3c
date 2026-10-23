require 'y3'
y3.config.log.level='info'
y3.game:event('游戏-初始化',function()
    -- Editor-started previews lack the launcher's lua_dummy flag. Use the
    -- official helper connection only in development, including quick restarts.
    if y3.game.get_start_mode()==1 and y3.game.is_debug_mode() then y3.develop.helper.init() end
    require('spirit.runtime').start()
end)
