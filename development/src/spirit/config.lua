-- 契灵守卫战·Y3：完整战役配置。对象资源由独立的 assets.lua 映射。
local C = {version='0.2.1', waves=32, max_towers=12, collection_limit=20,
    start_gold=340, start_lives=30, start_stones=5, start_balls=4,
    dt=1/30, preparation=35, intermission=16, capture_chance=65}
C.colors = {'#bfcbd7','#7adea3','#65bbff','#bd88ff'}
C.quality_names = {'普通','精良','稀有','史诗'}
C.elements = {'金','木','水','火','土'}
C.towers = {
    {name='游侠',role='多目标 / 远程',cost=80,attack=22,interval=0.85,range=1050,kind='archer',
        branches={'逐星游侠','穿云神射'},descs={'同时攻击4个目标','对精英和首领伤害提高80%'},color='#c9d77b'},
    {name='剑卫',role='单体 / 暴击',cost=90,attack=38,interval=1.15,range=830,kind='blade',
        branches={'狂刃剑圣','破军剑圣'},descs={'每第四击发动范围剑舞','暴击倍率提高并无视部分护甲'},color='#edb563'},
    {name='禁卫',role='控制 / 阵地',cost=75,attack=25,interval=1.15,range=850,kind='guard',
        branches={'雷霆统帅','铁壁统帅'},descs={'重击产生连锁雷电','全路塔攻击提高18%'},color='#7cb9ef'},
    {name='森语者',role='毒伤 / 减速',cost=85,attack=16,interval=1.1,range=1080,kind='grove',
        branches={'翡翠先知','荆棘女王'},descs={'毒伤跳转两个目标','减速增强，毒伤提高70%'},color='#65d8a3'},
    {name='幽魂',role='攻速 / 尸爆',cost=85,attack=17,interval=0.6,range=900,kind='wraith',
        branches={'血疫领主','暮影猎手'},descs={'击杀产生强力尸爆','连续攻击同一目标逐渐增伤'},color='#c690e7'},
}
C.upgrade_costs = {0,150,330,720,1500,3000}
C.level_scale = {1,2.15,4.62,9.94,21.37,45.95}
C.species = {
    '银鬃灵兽','锋翼隼','铜甲穿山灵','叶翼仙灵','树芽鹿','菌伞灵',
    '潮尾灵蛟','霜鳍灵鲼','雪鬃水獭','赤翎火鸟','熔角火蜥','烬尾火狐',
    '岩壳龟','磐臂山魈','砂环灵螺',
}
-- 每项技能的计算只在 combat.lua 使用；描述与数值由同一配置产生。
C.skills = {
    {name='强攻',slot=1,kind='attack',values={12,18,25,35},desc='宿主攻击提高%d%%'},
    {name='疾风',slot=1,kind='speed',values={10,16,23,32},desc='宿主攻击速度提高%d%%'},
    {name='远瞳',slot=1,kind='range',values={10,15,20,28},desc='宿主射程提高%d%%'},
    {name='连击',slot=2,kind='double',values={12,18,25,35},desc='%d%%概率追加一次60%%攻击伤害'},
    {name='决意',slot=2,kind='critical',values={12,18,25,35},desc='获得%d%%概率造成180%%伤害'},
    {name='猛击',slot=2,kind='heavy',values={45,65,90,125},desc='每第四击追加%d%%攻击伤害'},
    {name='追猎',slot=3,kind='execute',values={20,30,45,65},desc='对半血以下目标伤害提高%d%%'},
    {name='震荡',slot=3,kind='splash',values={15,25,35,50},desc='主攻击对周围目标溅射%d%%伤害'},
    {name='蚀甲',slot=3,kind='pierce',values={10,18,26,36},desc='忽略目标%d%%护甲'},
    {name='金刃',slot=4,kind='metal',values={90,130,180,250},desc='每6秒向4个目标发射%d%%攻击的灵刃'},
    {name='木灵',slot=4,kind='wood',values={30,45,65,90},desc='每6秒给4个敌人施加每秒%d%%攻击的毒，持续4秒'},
    {name='霜潮',slot=4,kind='water',values={70,100,145,200},desc='每6秒对4个目标造成%d%%攻击伤害并减速'},
    {name='炎陨',slot=4,kind='fire',values={100,145,205,280},desc='每6秒对区域敌人造成%d%%攻击伤害'},
    {name='岩震',slot=4,kind='earth',values={80,120,170,230},desc='每6秒对4个目标造成%d%%攻击伤害并短暂定身'},
}
C.equipment = {
    {name='锐锋',kind='attack',base=10,desc='攻击 +%d%%'},
    {name='风羽',kind='speed',base=8,desc='攻速 +%d%%'},
    {name='鹰眼',kind='range',base=8,desc='射程 +%d%%'},
    {name='破甲',kind='pierce',base=8,desc='护甲穿透 +%d%%'},
    {name='裂光',kind='splash',base=8,desc='溅射伤害 +%d%%'},
    {name='猎王',kind='boss',base=15,desc='首领伤害 +%d%%'},
    {name='灵钟',kind='cooldown',base=5,desc='精灵主动冷却缩减 +%d%%'},
    {name='战利印',kind='plunder',base=20,desc='本塔触发的战利金币 +%d%%（每怪次数有限）'},
}
C.gear_costs = {100,180,350,700,1400}
C.contracts = {
    {name='猎金契约',kind='plunder',value=25,desc='战利金币提高25%，每只敌人的触发次数仍有限'},
    {name='锋芒契约',kind='attack',value=12,desc='所有塔的攻击提高12%'},
    {name='疾风契约',kind='speed',value=12,desc='所有塔的攻击速度提高12%'},
    {name='灵感契约',kind='cooldown',value=10,desc='精灵主动冷却缩减10%（合计上限40%）'},
    {name='猎王契约',kind='boss',value=20,desc='所有塔对精英和首领伤害提高20%'},
    {name='连锁契约',kind='splash',value=10,desc='所有塔主攻击附带10%溅射'},
    {name='丰饶契约',kind='income',value=20,desc='波次结算金币提高20%'},
    {name='共鸣契约',kind='spirit',value=15,desc='精灵主动技能伤害提高15%'},
    {name='守护契约',kind='repair',value=8,desc='立即恢复8点生命，获得2枚洗练石'},
}
C.difficulties = {
    {name='普通',hp=1,reward=1,desc='适合首次游玩'},
    {name='困难',hp=1.35,reward=1.12,desc='需要合理搭配精灵与装备'},
    {name='噩梦',hp=1.8,reward=1.25,desc='需要成型流派与主动挑战收益'},
}
C.path = {{-2200,-1500},{2200,-1500},{2200,0},{-2200,0},{-2200,1500},{2200,1500}}
C.slots = {}
for row=1,2 do for col=1,6 do
    C.slots[#C.slots+1]={x=-1750+(col-1)*700,y=row==1 and -750 or 750}
end end
C.wave_names={'斥候','疾行','甲卫','精英突袭','虫潮','复苏','狂潮','黑潮首领'}
function C.wave(n)
    assert(n>=1 and n<=C.waves,'invalid wave')
    local phase=(n-1)%8+1
    local chapter=math.floor((n-1)/8)+1
    return {name=C.wave_names[phase],chapter=chapter,count=phase==8 and 1 or (phase==5 and 34 or 18+chapter*3),
        hp=math.floor(85*1.205^(n-1)*(phase==8 and 15 or phase==4 and 2.0 or 1)),
        speed=phase==2 and 230 or phase==8 and 92 or 145+chapter*5,
        armor=phase==3 and 0.38 or phase==8 and 0.20 or 0.05,
        regen=phase==6 and 0.008 or 0, boss=phase==8, elite=phase==4,
        bounty=math.floor(5+n*1.15),reward=math.floor(70+25*n),
        spawn_interval=phase==5 and 0.4 or 0.8,
        hint=phase==3 and '重甲：破甲与法术更有效' or phase==2 and '疾行：减速与多点覆盖' or phase==6 and '复苏：集中火力避免拖战' or phase==8 and '首领：单体输出与猎王装备' or '均衡配置，留意战利与精灵'}
end
function C.element(species) return math.floor((species-1)/3)+1 end
function C.skill_text(id,q) local s=C.skills[id]; return string.format(s.desc,s.values[q]) end
function C.tower_name(t)
    local d=C.towers[t.family]
    return t.level==6 and d.branches[t.branch] or d.name..' '..t.level..'阶'
end
return C
