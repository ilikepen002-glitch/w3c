local C=require 'spirit.config'
local T=require 'spirit.towers'
local W=require 'spirit.ui_widgets'
local UI={};UI.__index=UI
local function round(n)return tostring(math.floor(n+0.5)) end
function UI.new(game,player,assets,send,focus)
    local self=setmetatable({game=game,player=player,id=player:get_id(),assets=assets,send=send,focus=focus,
        family=1,slot=1,pet_id=nil,gear_id=nil,skill_slot=1,tab='pets',opened=false,confirm=nil,rows={}},UI)
    self.canvas=y3.ui.get_ui(player,assets.ui_root)
    self.canvas:set_visible(true)
    -- This fixed tree is built for all players in synchronized order.
    self.root=W.container(self.canvas,1920,1080)
    self.root:set_visible(true)
    self:build_hud();self:build_manager();self:build_guide();self:build_help();self:build_result();self:refresh()
    return self
end
-- Call only from the local player's context, after all synchronized trees exist.
-- Derive logical canvas size from the current client window, never desktop screen size.
function UI:adapt_viewport()
    local window_width,window_height=y3.ui.get_window_width(),y3.ui.get_window_height()
    local valid=W.fit_viewport(window_width,window_height)
    local width,height=valid and 1080*window_width/window_height or window_width,valid and 1080 or window_height
    local scale,x,y=W.fit_viewport(width,height)
    if not scale then
        if not self.viewport_unavailable then
            log.warn('SPIRIT_UI_VIEWPORT_UNAVAILABLE',width,height)
            self.viewport_unavailable=true
        end
        return false
    end
    self.viewport_unavailable=false
    if width~=self.viewport_width or height~=self.viewport_height then
        self.root:set_widget_relative_scale(scale,scale)
        self.root:set_pos(x,y)
        self.viewport_width=width;self.viewport_height=height
        log.info('SPIRIT_UI_VIEWPORT',window_width,window_height,width,height,scale)
    end
    return true
end
-- Button intent must refer to the version the player actually saw.
function UI:p()return self.view end
function UI:command(c)
    local current=self.game.players[self.id]
    if not current or current.status=='left' then return end
    self.confirm=nil
    c.epoch=self.view_epoch
    self.send(c)
end
function UI:tower()
    local p=self:p();return p.towers[p.slots[self.slot]]
end
function UI:pet()return self:p().pets[self.pet_id] end
function UI:pet_command(action,extra)
    local pet=self:pet();if not pet then return end
    local c=extra or {};c.action=action;c.pet_id=pet.id;c.version=pet.version;self:command(c)
end
function UI:tower_command(action,extra)
    local t=self:tower();if not t then return end
    local c=extra or {};c.action=action;c.tower_id=t.id;c.tower_version=t.version;self:command(c)
end
function UI:open(tab)
    self.opened=true;self.tab=tab;self.confirm=nil;self:refresh()
end
function UI:confirm_action(key,run)
    if self.confirm==key then self.confirm=nil;run() else self.confirm=key;self:refresh() end
end
function UI:build_hud()
    local top=W.panel(self.root,0,1000,1920,80)
    W.label(top,24,29,260,38,'契灵守卫战',30,W.colors.accent)
    self.resources=W.label(top,295,36,800,32,'',22)
    self.wave=W.label(top,295,7,1050,26,'',16,W.colors.muted)
    self.start=W.button(top,1360,21,160,40,'开始战役',function()
        self:command({action=self.view_status=='lobby' and 'start' or self.view_status=='over' and 'restart' or 'next_wave'})
    end,true)
    self.challenge=W.button(top,1532,21,160,40,'开启挑战',function()self:command({action='challenge'})end)
    W.button(top,1705,21,85,40,'回防线',function()self.focus(self.id)end)
    W.button(top,1800,21,96,40,'玩法',function()self.help:set_visible(not self.help:is_visible())end)
    self.difficulty={}
    for i,d in ipairs(C.difficulties) do
        self.difficulty[i]=W.button(self.root,24+(i-1)*110,945,100,36,d.name,function()self:command({action='difficulty',value=i})end)
    end
    self.notice=W.label(self.root,380,945,1150,38,'',21,W.colors.accent)
    local build=W.panel(self.root,20,16,515,190)
    W.label(build,16,158,480,26,'布阵 · 选塔族与编号，再建造',18,W.colors.accent)
    self.families={}
    for i,d in ipairs(C.towers) do
        self.families[i]=W.button(build,15+(i-1)*99,118,94,32,d.name,function()self.family=i;self:refresh()end)
    end
    self.slots={}
    for i=1,12 do
        local col=(i-1)%6;local row=math.floor((i-1)/6)
        self.slots[i]=W.button(build,15+col*82,76-row*34,76,30,tostring(i),function()
            self.slot=i;self.confirm=nil;self:refresh()
        end)
        self.slots[i].label:set_font_size(16)
    end
    self.build_button=W.button(build,15,7,480,30,'建造',function()self:command({action='build',family=self.family,slot=self.slot})end,true)
    local inspect=W.panel(self.root,547,16,685,190)
    self.tower_title=W.label(inspect,18,152,640,26,'选择建造位',20,W.colors.accent)
    self.tower_detail=W.label(inspect,18,68,640,78,'',16)
    self.upgrade_a=W.button(inspect,18,32,245,32,'升级',function()self:tower_command('upgrade',{branch=1})end,true)
    self.upgrade_b=W.button(inspect,275,32,245,32,'分支二',function()self:tower_command('upgrade',{branch=2})end)
    self.sell=W.button(inspect,534,32,132,32,'出售',function()
        local t=self:tower();if t then self:confirm_action('sell:'..t.id..':'..t.version,function()self:tower_command('sell',{confirm=true})end) end
    end)
    self.tower_note=W.label(inspect,18,5,640,22,'出售返还80%；精灵和装备保留。',14,W.colors.muted)
    local menu=W.panel(self.root,1244,16,656,190)
    W.label(menu,18,156,600,25,'契灵工坊',20,W.colors.accent)
    W.button(menu,18,111,194,36,'精灵收藏',function()self:open('pets')end,true)
    W.button(menu,230,111,194,36,'装备工坊',function()self:open('gear')end)
    self.contract_button=W.button(menu,442,111,194,36,'契约奖励',function()self:open('contracts')end)
    self.wild_button=W.button(menu,18,67,300,36,'野生精灵',function()self:open('wild')end)
    W.button(menu,336,67,300,36,'补给与进度',function()self:open('supply')end)
    self.summary=W.label(menu,18,8,600,50,'',16,W.colors.muted)
end
function UI:build_manager()
    self.manager=W.panel(self.root,1010,290,890,635)
    self.manager:set_visible(false)
    self.manager_title=W.label(self.manager,22,582,720,38,'精灵收藏',27,W.colors.accent)
    W.button(self.manager,794,584,74,32,'关闭',function()self.opened=false;self.confirm=nil;self:refresh()end)
    self.panes={}
    for _,tab in ipairs({'pets','gear','contracts','wild','supply'}) do
        self.panes[tab]=W.panel(self.manager,14,12,862,560,W.colors.deep)
    end
    local pets=self.panes.pets
    self.pet_rows={}
    for i=1,20 do
        self.pet_rows[i]=W.button(pets,10,520-(i-1)*25,222,23,'',function()
            self.pet_id=self:p().pet_order[i];self.confirm=nil;self:refresh()
        end)
    end
    self.pet_title=W.label(pets,250,515,580,32,'选择一只精灵',23,W.colors.accent)
    self.pet_icon=W.image(pets,250,459,52,52)
    self.pet_status=W.label(pets,316,466,520,44,'',17,W.colors.muted)
    self.pet_skills={}
    for i=1,4 do
        self.pet_skills[i]=W.button(pets,250,404-(i-1)*63,590,57,'',function()self.skill_slot=i;self:refresh()end)
    end
    self.bind=W.button(pets,250,150,186,37,'绑定当前塔',function()
        local t=self:tower();if t then self:pet_command('bind',{tower_id=t.id,tower_version=t.version}) end
    end,true)
    self.recall=W.button(pets,447,150,186,37,'召回',function()self:pet_command('recall')end)
    self.open_slot=W.button(pets,644,150,196,37,'开栏 · 1开栏石',function()self:pet_command('open_slot')end)
    self.reroll=W.button(pets,250,106,186,37,'洗练 · 2洗练石',function()self:pet_command('reroll',{slot=self.skill_slot})end)
    self.release=W.button(pets,447,106,186,37,'释放 · 得2洗练石',function()
        local pet=self:pet();if pet then self:confirm_action('release:'..pet.id..':'..pet.version,function()self:pet_command('release',{confirm=true})end) end
    end)
    self.directed={}
    for i=1,3 do self.directed[i]=W.button(pets,250+(i-1)*197,60,186,37,'定向',function()
        local pet=self:pet()
        if pet and self.skill_slot<=3 then
            local skill=(self.skill_slot-1)*3+i
            self:confirm_action('directed:'..pet.id..':'..pet.version..':'..skill,function()self:pet_command('directed',{slot=self.skill_slot,skill=skill})end)
        end
    end) end
    self.cultivation_note=W.label(pets,250,4,590,50,'',15,W.colors.muted)
    self.proposal=W.panel(pets,240,48,610,407)
    self.proposal_text=W.label(self.proposal,20,108,570,280,'',20)
    self.keep=W.button(self.proposal,20,36,274,50,'保留旧技能',function()
        local pet=self:pet();if pet and pet.proposal then self:pet_command('resolve',{proposal_id=pet.proposal.id,adopt=false}) end
    end)
    self.adopt=W.button(self.proposal,310,36,274,50,'采用新技能',function()
        local pet=self:pet();if pet and pet.proposal then self:pet_command('resolve',{proposal_id=pet.proposal.id,adopt=true}) end
    end,true)
    self:build_other_panes()
end
function UI:build_other_panes()
    local gear=self.panes.gear
    W.label(gear,16,515,820,30,'每塔3件，同类不能重复；购买后自动选中，再装备到目标塔',20,W.colors.accent)
    self.gear_shop={}
    for i,d in ipairs(C.equipment) do
        local col=(i-1)%4;local row=math.floor((i-1)/4)
        self.gear_shop[i]=W.button(gear,16+col*208,460-row*48,196,40,d.name..' · 100金',function()self:command({action='buy_gear',kind=i})end)
    end
    self.gear_rows={}
    for i=1,36 do
        local col=(i-1)%3;local row=math.floor((i-1)/3)
        self.gear_rows[i]=W.button(gear,16+col*276,365-row*25,264,23,'',function()self.gear_id=self:p().gear_order[i];self:refresh()end)
    end
    self.gear_detail=W.label(gear,16,28,250,48,'选择装备',15)
    self.recycle=W.button(gear,280,18,138,42,'回收',function()
        local e=self:p().gear[self.gear_id]
        if e then self:confirm_action('recycle:'..e.id..':'..e.version,function()
            self:command({action='recycle_gear',gear_id=e.id,gear_version=e.version,confirm=true})
        end) end
    end)
    self.equip=W.button(gear,430,18,128,42,'装备当前塔',function()
        local p=self:p();local e=p.gear[self.gear_id];local t=self:tower()
        if e and t then self:command({action='equip',gear_id=e.id,gear_version=e.version,tower_id=t.id,tower_version=t.version}) end
    end,true)
    self.unequip=W.button(gear,570,18,128,42,'卸下',function()
        local e=self:p().gear[self.gear_id];if e then self:command({action='unequip',gear_id=e.id,gear_version=e.version}) end
    end)
    self.gear_upgrade=W.button(gear,710,18,128,42,'升阶',function()
        local e=self:p().gear[self.gear_id];if e then self:command({action='upgrade_gear',gear_id=e.id,gear_version=e.version}) end
    end)
    local contract=self.panes.contracts
    if self.assets.icons.contract then W.image(contract,310,300,240,240,self.assets.icons.contract) end
    self.contract_title=W.label(contract,24,260,810,50,'',24,W.colors.accent)
    self.contracts={}
    for i=1,3 do self.contracts[i]=W.button(contract,24+(i-1)*278,80,260,170,'',function()
        local p=self:p();local id=p.offer_order[1];if id then self:command({action='contract',offer_id=id,choice=i}) end
    end,true) end
    self.contract_summary=W.label(contract,24,10,810,60,'',16,W.colors.muted)
    local wild=self.panes.wild
    W.label(wild,24,495,810,45,'野生精灵 · 首只首次捕获必定成功',24,W.colors.accent)
    self.wild_rows={}
    for i=1,3 do self.wild_rows[i]=W.button(wild,24,340-(i-1)*140,810,116,'',function()
        local id=self:p().wild_order[i];if id then self:command({action='capture',wild_id=id}) end
    end,true) end
    local supply=self.panes.supply
    W.label(supply,24,495,810,45,'补给与战役进度',25,W.colors.accent)
    W.button(supply,24,414,260,55,'捕获球 +1 · 80金',function()self:command({action='buy_supply',kind='ball'})end)
    W.button(supply,300,414,260,55,'洗练石 +2 · 100金',function()self:command({action='buy_supply',kind='stone'})end)
    W.button(supply,576,414,260,55,'开栏石 +1 · 500金',function()self:command({action='buy_supply',kind='open'})end)
    self.progress=W.label(supply,24,30,810,350,'',22)
end
function UI:build_help()
    self.help=W.panel(self.root,420,320,1080,600)
    W.label(self.help,32,532,960,40,'契灵守卫战 · 上手指南',32,W.colors.accent)
    W.label(self.help,32,80,1000,430,
        '1  布阵：选塔族 → 选空位 → 建造。建议先建游侠与森语者。\n\n'..
        '2  捕获：打开野生精灵，点击捕获；第一只必定成功。\n\n'..
        '3  培养：收藏中选精灵 → 左下选塔 → 绑定；洗练候选关闭后仍保留。\n\n'..
        '4  共鸣：第4/8波后，第三/第四栏生效；开栏石增加技能栏。\n\n'..
        '5  成长：升级塔、搭配装备，每四波选择一次契约；波间可挑战加奖。\n\n'..
        '6  战利：击杀直接结清敌人的剩余战利，快速清怪更划算。\n\n'..
        '7  胜利：守住32波；普通首领漏过扣10生命，最终首领漏过直接失败。',22)
    W.button(self.help,350,22,380,46,'明白了，开始布阵',function()self.help:set_visible(false)end,true)
    self.help:set_visible(false)
end
function UI:build_guide()
    self.guide=W.panel(self.root,20,220,620,142)
    self.guide_title=W.label(self.guide,18,102,585,28,'',21,W.colors.accent)
    self.guide_text=W.label(self.guide,18,51,585,46,'',17)
    self.guide_button=W.button(self.guide,18,10,280,34,'',function()
        local p=self:p()
        if self.guide_action=='build' then
            for i=1,#C.slots do if not p.slots[i] then self.slot=i;break end end
            self.family=#p.tower_order==0 and 1 or 4;self:refresh()
        elseif self.guide_action=='capture' then self:open('wild')
        elseif self.guide_action=='bind' then
            self.pet_id=p.pet_order[1];self.slot=p.towers[p.tower_order[1]].slot;self:open('pets')
        elseif self.guide_action=='start' then self:command({action='start'}) end
    end,true)
end
function UI:refresh_guide(p)
    self.guide:set_visible(self.game.status=='lobby')
    if self.game.status~='lobby' then return end
    local bound=false
    for _,id in ipairs(p.pet_order) do if p.pets[id].host then bound=true;break end end
    if #p.tower_order<2 then
        self.guide_action='build';self.guide_title:set_text('准备 1/3 · 先布置两座防御塔')
        self.guide_text:set_text('推荐游侠＋森语者。左下选塔族与空位，再点击建造。')
        self.guide_button:set('定位推荐塔族与空位')
    elseif #p.pet_order==0 then
        self.guide_action='capture';self.guide_title:set_text('准备 2/3 · 捕获第一位伙伴')
        self.guide_text:set_text('首次捕获必定成功；捕获后会直接选中新精灵。')
        self.guide_button:set('打开野生精灵')
    elseif not bound then
        self.guide_action='bind';self.guide_title:set_text('准备 3/3 · 将精灵绑定到防御塔')
        self.guide_text:set_text('打开收藏后点击绑定。精灵技能会增强宿主防御塔。')
        self.guide_button:set('选中精灵与目标塔')
    else
        self.guide_action='start';self.guide_title:set_text('准备完成 · 迎接第一波黑潮')
        self.guide_text:set_text('战斗中仍可建造和培养；每四波记得领取契约奖励。')
        self.guide_button:set(self.id==self.game.host and '开始战役' or '等待房主开始',self.id==self.game.host)
    end
end
function UI:refresh_pet(p)
    if not p.pets[self.pet_id] then self.pet_id=p.pet_order[1] end
    for i,b in ipairs(self.pet_rows) do
        local pet=p.pets[p.pet_order[i]];b.ui:set_visible(pet~=nil)
        if pet then b:set((pet.id==self.pet_id and '◆ ' or '')..C.species[pet.species]..(pet.host and ' · 已绑定' or '')) end
    end
    local pet=self:pet();self.proposal:set_visible(pet~=nil and pet.proposal~=nil)
    if not pet then
        self.pet_icon:set_visible(false)
        self.pet_title:set_text('收藏为空');self.pet_status:set_text('打开野生精灵，捕获你的第一位伙伴。')
        for _,b in ipairs(self.pet_skills) do b:set('尚无精灵',false) end
        for _,b in ipairs({self.bind,self.recall,self.open_slot,self.reroll,self.release}) do b.ui:set_button_enable(false) end
        for _,b in ipairs(self.directed) do b.ui:set_button_enable(false) end
        return
    end
    if self.assets.icons.elements then
        self.pet_icon:set_image(self.assets.icons.elements[C.element(pet.species)]);self.pet_icon:set_visible(true)
    end
    self.pet_title:set_text(C.species[pet.species]..' · '..C.elements[C.element(pet.species)]..'系')
    local t=pet.host and p.towers[pet.host];self.pet_status:set_text(t and ('宿主：'..C.tower_name(t)..'（位置'..t.slot..'）') or '未绑定 · 可在左下选择目标塔')
    for i,b in ipairs(self.pet_skills) do
        local id=pet.skills[i];local locked=i==3 and p.completed<4 or i==4 and p.completed<8
        b:set((i==self.skill_slot and '◆ ' or '')..'第'..i..'栏 '..(id and (C.quality_names[pet.qualities[i]]..' '..C.skills[id].name..'\n'..C.skill_text(id,pet.qualities[i])) or '空栏 · 使用开栏石开启')..(locked and ' [共鸣未解锁]' or ''))
    end
    self.bind:set('绑定位置'..self.slot,self:tower()~=nil);self.recall:set('召回',pet.host~=nil)
    self.open_slot:set('开栏 · 1开栏石',#pet.skills<4 and p.open_stones>0 and not pet.proposal)
    self.reroll:set('洗练第'..self.skill_slot..'栏 · 2石',pet.skills[self.skill_slot]~=nil and not pet.proposal and p.stones>=2)
    self.release:set(self.confirm=='release:'..pet.id..':'..pet.version and '再次点击确认释放' or '释放 · 得2洗练石',not pet.host and not pet.proposal)
    for i,b in ipairs(self.directed) do
        local id=(self.skill_slot-1)*3+i;local available=self.skill_slot<=3 and pet.skills[self.skill_slot]~=nil and not pet.proposal
        b:set(available and ((self.confirm=='directed:'..pet.id..':'..pet.version..':'..id and '确认：' or '定向：')..C.skills[id].name..' · 3石') or '元素技能由种族决定',available and p.stones>=3)
    end
    self.cultivation_note:set_text('定向学习固定获得精良品质；蓝/紫技能会降为绿色，需再次点击确认。\n洗练生成候选时扣费；关闭界面保留候选，不会额外扣费。')
    if pet.proposal then
        local pr=pet.proposal;local old=pet.skills[pr.slot]
        self.proposal_text:set_text('第'..pr.slot..'栏 · 洗练结果\n\n原有：'..C.quality_names[pet.qualities[pr.slot]]..' '..C.skills[old].name..'\n'..C.skill_text(old,pet.qualities[pr.slot])..
            '\n\n候选：'..C.quality_names[pr.quality]..' '..C.skills[pr.skill].name..'\n'..C.skill_text(pr.skill,pr.quality)..'\n\n本次已消耗2洗练石；选择不再扣费。')
    end
end
function UI:refresh()
    local current=self.game.players[self.id]
    if not current or current.status=='left' then
        -- Keep the last view for already queued local callbacks; command() rejects them.
        self.root:set_visible(false)
        return
    end
    self.root:set_visible(true)
    local previous=self.view_epoch==self.game.epoch and self.view or nil
    if self.view_epoch and self.view_epoch~=self.game.epoch then
        self.opened=false;self.confirm=nil;self.pet_id=nil;self.gear_id=nil;self.slot=1;self.result_dismissed=false
    end
    self.view_epoch=self.game.epoch;self.view_status=self.game.status
    self.view=self.game:snapshot(self.id)
    local p=self:p();if not p then return end
    -- Follow a completed acquisition, never an optimistic click or another tab's state.
    if previous and self.opened then
        if self.tab=='wild' then
            for _,id in ipairs(p.pet_order) do
                if not previous.pets[id] then self.pet_id=id;self.tab='pets';self.confirm=nil end
            end
        elseif self.tab=='gear' then
            for _,id in ipairs(p.gear_order) do
                if not previous.gear[id] then self.gear_id=id;self.confirm=nil end
            end
        end
    end
    self:refresh_guide(p)
    local terminal=p.status=='won' or p.status=='lost' or p.status=='left'
    self.resources:set_text('金币 '..round(p.gold)..'    生命 '..p.lives..'/'..C.start_lives..'    球 '..p.balls..'    洗练石 '..p.stones..'    开栏石 '..p.open_stones)
    local w=C.wave(math.min(32,math.max(1,p.wave+(p.status=='break' and 1 or 0))))
    local status=({ready='尚未开始',combat='迎敌中',['break']='准备 '..math.max(0,math.ceil(p.next_wave-self.game.time))..'秒',won='胜利 · 黑潮已被击退',lost='防线失守',left='已离开'})[p.status]
    self.wave:set_text('第 '..p.wave..'/32 波 · '..status..'    '..w.name..' — '..w.hint)
    self.notice:set_text(self.game.time-p.notice_at<8 and p.notice or '')
    local restart=self.game.status=='over' and self.id==self.game.host and p.status~='left'
    self.start:set(self.game.status=='over' and '再来一局' or self.game.status=='lobby' and '开始战役' or '提前迎敌',restart or not terminal and (self.game.status=='lobby' and self.id==self.game.host or p.status=='break'))
    self.result:set_visible(terminal and p.status~='left' and not self.result_dismissed)
    if terminal then
        self.result_title:set_text(p.status=='won' and '黑潮退散 · 守卫成功' or '防线失守 · 蓄势再战')
        self.result_detail:set_text('完成 '..p.completed..' / 32 波\n\n击杀 '..p.kills..'    总伤害 '..round(p.damage)..'\n\n战利金币 '..p.loot_gold..'    收集契约 '..#p.contracts..'\n\n'..(self.game.status=='over' and '本局已经结束，可以重新布阵挑战。' or '其他防线仍在战斗，可以关闭窗口查看本局阵容。'))
        self.retry:set(restart and '重新布阵 · 再来一局' or '等待其余防线 / 房主',restart)
    end
    self.challenge:set(p.challenge and '挑战已开启' or '挑战：+35%敌血',p.status=='break' and not p.challenge)
    for i,b in ipairs(self.difficulty) do b.ui:set_visible(self.game.status=='lobby');b:set((i==self.game.difficulty and '◆ ' or '')..C.difficulties[i].name,self.id==self.game.host) end
    for i,b in ipairs(self.families) do b:set((i==self.family and '◆' or '')..C.towers[i].name) end
    for i,b in ipairs(self.slots) do
        local t=p.towers[p.slots[i]]
        b:set(t and (i..'·'..t.level) or tostring(i))
        b.label:set_text_color_hex(i==self.slot and W.colors.accent or W.colors.text,100)
    end
    local t=self:tower();self.build_button:set('位置'..self.slot..' · 建造'..C.towers[self.family].name..' · '..C.towers[self.family].cost..'金',not t and not terminal and p.gold>=C.towers[self.family].cost)
    if t then
        local s=T.stats(p,t);local d=C.towers[t.family]
        self.tower_title:set_text('位置'..t.slot..' · '..C.tower_name(t)..' · '..d.role)
        local equipment={};for _,id in ipairs(t.gear) do local e=p.gear[id];equipment[#equipment+1]=C.equipment[e.kind].name..e.tier end
        self.tower_detail:set_text('攻击 '..round(s.damage)..'    间隔 '..string.format('%.2f',s.interval)..'秒    射程 '..round(s.radius)..'\n'..
            '精灵：'..(t.pet and C.species[p.pets[t.pet].species] or '未绑定')..'    装备：'..(#equipment>0 and table.concat(equipment,' / ') or '无')..'\n'..
            '累计伤害 '..round(t.damage)..'    击杀 '..t.kills..(t.level==6 and ('\n'..d.descs[t.branch]) or ''))
        local cost=C.upgrade_costs[t.level+1]
        self.upgrade_a:set(t.level==6 and '已到终阶' or (t.level==5 and d.branches[1] or '升至'..(t.level+1)..'阶')..' · '..tostring(cost)..'金',cost~=nil and p.gold>=cost and not terminal)
        self.upgrade_b.ui:set_visible(t.level==5);self.upgrade_b:set(d.branches[2]..' · 3000金',p.gold>=3000 and not terminal)
        self.sell:set(self.confirm=='sell:'..t.id..':'..t.version and '再次点击确认' or '出售 '..math.floor(t.spent*0.8)..'金',not terminal)
    else
        self.tower_title:set_text('位置'..self.slot..' · 空建造位');self.tower_detail:set_text(C.towers[self.family].role..'\n选择塔族后点击左侧建造。')
        self.upgrade_a:set('尚未建造',false);self.upgrade_b.ui:set_visible(false);self.sell:set('出售',false)
    end
    self.wild_button:set('野生精灵 · '..#p.wild_order..' 只');self.contract_button:set('契约奖励'..(#p.offer_order>0 and (' · '..#p.offer_order..' 待选') or ''))
    self.summary:set_text('收藏 '..#p.pet_order..'/20    契约 '..#p.contracts..'    击杀 '..p.kills..'\n战利金币 '..p.loot_gold..' · 击杀可结算剩余战利，无需留怪。')
    self.manager:set_visible(self.opened)
    for tab,pane in pairs(self.panes) do pane:set_visible(tab==self.tab) end
    self.manager_title:set_text(({pets='精灵收藏与培养',gear='装备工坊',contracts='契约三选一',wild='野生精灵',supply='补给与战役进度'})[self.tab])
    if not self.opened then return end
    if self.tab=='pets' then self:refresh_pet(p)
    elseif self.tab=='gear' then self:refresh_gear(p)
    elseif self.tab=='contracts' then
        local offer=p.offers[p.offer_order[1]]
        self.contract_title:set_text(offer and '选择一项，改变本局打法' or '每完成4波，获得一次契约选择')
        for i,b in ipairs(self.contracts) do local d=offer and C.contracts[offer.choices[i]];b:set(d and (d.name..'\n\n'..d.desc) or '暂无待选契约',offer~=nil and not terminal) end
        local names={};for _,id in ipairs(p.contracts) do names[#names+1]=C.contracts[id].name end
        self.contract_summary:set_text('已获得：'..table.concat(names,' / '))
    elseif self.tab=='wild' then
        for i,b in ipairs(self.wild_rows) do
            local wild=p.wild[p.wild_order[i]];b:set(wild and (C.species[wild.species]..' · '..C.elements[C.element(wild.species)]..'系\n剩余'..math.ceil(wild.expires-self.game.time)..'秒  |  点击捕获 · 1球\n'..(p.captured==0 and '首次教学捕获必定成功' or '成功率65%，失败消耗1球，可再次尝试')) or '暂无野生精灵 · 每两波出现',wild~=nil and p.balls>0 and not terminal)
        end
    elseif self.tab=='supply' then
        self.progress:set_text('难度：'..C.difficulties[self.game.difficulty].name..'\n\n已完成 '..p.completed..'/32 波\n每波：金币、捕获球与洗练石\n每4波：开栏石、额外洗练石、契约三选一\n每8波：黑潮首领\n\n第三栏：'..(p.completed>=4 and '已共鸣' or '完成第4波后生效')..'\n第四栏：'..(p.completed>=8 and '已共鸣' or '完成第8波后生效')..'\n\n累计伤害 '..round(p.damage)..'  ·  漏怪 '..p.leaks)
    end
end
function UI:refresh_gear(p)
    local terminal=p.status=='won' or p.status=='lost'
    for i,b in ipairs(self.gear_shop) do
        local reason=#p.gear_order>=36 and '仓库已满' or p.gold<C.gear_costs[1] and '金币不足' or C.gear_costs[1]..'金'
        b:set(C.equipment[i].name..' · '..reason,not terminal and #p.gear_order<36 and p.gold>=C.gear_costs[1])
    end
    if not p.gear[self.gear_id] then self.gear_id=p.gear_order[1] end
    for i,b in ipairs(self.gear_rows) do
        local e=p.gear[p.gear_order[i]];b.ui:set_visible(e~=nil)
        if e then b:set((e.id==self.gear_id and '◆ ' or '')..C.equipment[e.kind].name..' '..e.tier..'阶'..(e.tower and ' [已装备]' or '')) end
    end
    local e=p.gear[self.gear_id];local t=self:tower()
    local refund=0;if e then for tier=1,e.tier do refund=refund+C.gear_costs[tier] end end
    self.recycle:set(e and (self.confirm=='recycle:'..e.id..':'..e.version and '确认回收' or '回收 '..math.floor(refund*.5)..'金') or '回收',e~=nil and not e.tower and not terminal)
    local equip_reason=not e and '先选装备' or not t and '先选防御塔' or e.tower==t.id and '已装备此塔' or #t.gear>=3 and '目标塔已满'
    if not equip_reason then
        for _,id in ipairs(t.gear) do if p.gear[id].kind==e.kind then equip_reason='已有同类装备';break end end
    end
    self.equip:set(equip_reason or '装备位置'..self.slot,not terminal and not equip_reason)
    self.unequip:set('卸下',e~=nil and e.tower~=nil and not terminal)
    self.gear_upgrade:set(e and e.tier<5 and ('升阶 '..C.gear_costs[e.tier+1]..'金') or '已满阶',e~=nil and e.tier<5 and p.gold>=C.gear_costs[e.tier+1] and not terminal)
    if e then
        local def=C.equipment[e.kind];self.gear_detail:set_text(def.name..' '..e.tier..'阶 · '..string.format(def.desc,def.base*e.tier)..'\n'..(e.tower and ('装备于位置'..p.towers[e.tower].slot) or '位于仓库'))
    else self.gear_detail:set_text('从上方购买装备，再装备到当前选中塔。') end
end
function UI:build_result()
    self.result=W.panel(self.root,510,340,900,560)
    self.result_title=W.label(self.result,40,465,820,55,'',36,W.colors.accent)
    self.result_detail=W.label(self.result,40,150,820,290,'',24)
    self.retry=W.button(self.result,40,65,530,58,'再来一局',function()self:command({action='restart'})end,true)
    W.button(self.result,590,65,270,58,'查看本局阵容',function()self.result_dismissed=true;self:refresh()end)
    self.result:set_visible(false)
end
return UI
