# 40 件目录与固定配方（Astra PASS 表）

以下表与 `TDItemCatalogConfig.wurst` 采用同一已批准配置；品质按白、绿、蓝、紫，固定下一阶显式登记，不以 rawcode 差值推导。旧28个物品名称constant已退役，调用与测试迁移为明确品质+装备线constant。旧rawcode保留但按冻结表赋予新身份，没有旧装备别名入池。

| 线 | 白 | 绿 | 蓝 | 紫 |
| --- | --- | --- | --- | --- |
| SCOPE | 远望镜 (`iW02`) | 精制远望镜 (`iG02`) | 鹰眼望远镜 (`iB01`) | 风行旗 (`iP01`) |
| WAR_AXE | 战斧 (`iW01`) | 精钢战斧 (`iG01`) | 狂战战斧 (`iB02`) | 剑圣印记 (`iP02`) |
| SWIFT | 迅击手套 (`iW03`) | 迅击护手 (`iG05`) | 疾袭护腕 (`iB07`) | 饥饿心核 (`iP04`) |
| SHIELD | 盾符 (`iW09`) | 镇守盾符 (`iG04`) | 坚壁盾符 (`iB04`) | 镇军盾徽 (`iP03`) |
| POISON | 毒囊 (`iW08`) | 淬毒藤囊 (`iG09`) | 腐毒囊 (`iB08`) | 森蚀之种 (`iP05`) |
| ARMOR | 破甲尖刺 (`iW06`) | 裂甲骨刺 (`iG03`) | 碎甲战印 (`iB03`) | 裂甲战鼓 (`iP06`) |
| COMMAND | 行军旗 (`iW04`) | 督军旗 (`iG07`) | 统领旗 (`iB06`) | 统御号角 (`iP07`) |
| GOLD | 猎金指环 (`iW05`) | 佣兵钱袋 (`iG06`) | 赏金契约 (`iB05`) | 灵感法典 (`iP08`) |
| WIND | 疾风鼓 (`iW07`) | 疾风军鼓 (`iG08`) | 劲风战鼓 (`iB09`) | 疾风战鼓 (`iP09`) |
| FROST | 寒霜碎晶 (`iW10`) | 寒霜晶石 (`iG10`) | 寒霜晶核 (`iB10`) | 永霜核心 (`iP10`) |

## 退役名称 API 的集中迁移

| 旧 constant | 当前明确身份 |
| --- | --- |
| TD_ITEM_SHORT_BOW_ID | TD_ITEM_WHITE_WAR_AXE_ID |
| TD_ITEM_EAGLE_SCOPE_ID | TD_ITEM_WHITE_SCOPE_ID |
| TD_ITEM_SWIFT_GLOVES_ID | TD_ITEM_WHITE_SWIFT_ID |
| TD_ITEM_COOLING_RUNE_ID | TD_ITEM_WHITE_COMMAND_ID |
| TD_ITEM_GOLD_RING_ID | TD_ITEM_WHITE_GOLD_ID |
| TD_ITEM_ARMOR_SPIKE_ID | TD_ITEM_WHITE_ARMOR_ID |
| TD_ITEM_EXECUTION_DAGGER_ID | TD_ITEM_WHITE_WIND_ID |
| TD_ITEM_POISON_SAC_ID | TD_ITEM_WHITE_POISON_ID |
| TD_ITEM_STABLE_TOTEM_ID | TD_ITEM_WHITE_SHIELD_ID |
| TD_ITEM_SCAVENGER_BAG_ID | TD_ITEM_WHITE_FROST_ID |
| TD_ITEM_STEEL_LONGBOW_ID | TD_ITEM_GREEN_WAR_AXE_ID |
| TD_ITEM_HUNTER_SCOPE_ID | TD_ITEM_GREEN_SCOPE_ID |
| TD_ITEM_WAR_AXE_ID | TD_ITEM_GREEN_ARMOR_ID |
| TD_ITEM_RHYTHM_TOTEM_ID | TD_ITEM_GREEN_SHIELD_ID |
| TD_ITEM_TOXIC_VINE_ID | TD_ITEM_GREEN_SWIFT_ID |
| TD_ITEM_MERCENARY_PURSE_ID | TD_ITEM_GREEN_GOLD_ID |
| TD_ITEM_LACERATING_SPIKE_ID | TD_ITEM_GREEN_COMMAND_ID |
| TD_ITEM_FOCUS_STONE_ID | TD_ITEM_GREEN_WIND_ID |
| TD_ITEM_WINDRUNNER_BOW_ID | TD_ITEM_BLUE_SCOPE_ID |
| TD_ITEM_BERSERKER_BADGE_ID | TD_ITEM_BLUE_WAR_AXE_ID |
| TD_ITEM_ARMOR_DRUM_ID | TD_ITEM_BLUE_ARMOR_ID |
| TD_ITEM_FROST_TOME_ID | TD_ITEM_BLUE_SHIELD_ID |
| TD_ITEM_BOUNTY_CONTRACT_ID | TD_ITEM_BLUE_GOLD_ID |
| TD_ITEM_EXECUTION_MARK_ID | TD_ITEM_BLUE_COMMAND_ID |
| TD_ITEM_WHITE_TIGER_BANNER_ID | TD_ITEM_PURPLE_SCOPE_ID |
| TD_ITEM_BLADEMASTER_SIGIL_ID | TD_ITEM_PURPLE_WAR_AXE_ID |
| TD_ITEM_COMMAND_SEAL_ID | TD_ITEM_PURPLE_SHIELD_ID |
| TD_ITEM_CORRUPTED_HEART_ID | TD_ITEM_PURPLE_SWIFT_ID |

所有数值、副词条、光环半径与专精参数只在配置包定义。未列副词条均为0。A阶段登记光环/专精数据；B/C运行时尚待相应块实施与审查，不因此宣称全部词条已生效。
