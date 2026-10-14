# 第2批：3枚洗练石定向学习绿色技能

冻结地图 SHA-256：769baeff14204aaae592224bac48423e950a70f8dbe4e0080200ab8ac4293c17。生产源码 `5cd5bd1`；精确单级物编及固定族门禁 `e98d782`。完整 checks 与 build PASS，Grill 进程已退出。检查/构建/当前所有 Wurst 输入逐一 SHA-256 相同（provenance.json）。

## 实现范围

- 已拥有栏位的固定合法绿色目录；第3栏三页，可提前培养专属但宿主适配生效规则不变；第4栏仅本系绿20/24/28/32/36与通用11/12。相同已拥有绿色留空，不重复、跨栏或跨族。
- 预览与取消零扣费；确认成功恰扣3枚。现有随机1枚流程独立；pending关闭保留，替换候选须先明确处理旧候选。身份、revision、generation、候选版本、局重置epoch、库存与结束状态检查均失败不扣费。旧readyAt不重置。
- 只新增38个能力对象：Pm0F..Pm18共10个与Pn合法绿28个，固定角色格；无392种位置变体。旧物编仅Pc06/Pm0E的aub1提示更新。成员集合不变，仅war3map.j/w3a/w3i变化，其余资源字节不变。

## 验证

- checks-manifest.json / checks.log：官方完整typecheck与全部Wurst测试PASS。build-manifest.json / build.log：官方原生构建、Legacy JASS、CDR与启动门禁PASS。
- full-ui-artifact.log：完整物编/UI/全局rawcode及Channel共享订单严格门禁PASS；Pn字段只存在第1级，各Channel字段dataPointer精确匹配，无跨格/跨族订单碰撞。
- packed-replay.json：实际packed生产事务与UI/onCommand正向链、stock0/2/3/4、重复确认、两宠抢3枚、11生命周期负例、三页所有专属/空格、两栏隐藏第3/4栏、首末页、旧随机拒定向、generation换绑旧页拒绝且候选保留、新页可确认。相同oracle抓住免费旧随机采用定向、重复扣费、残留第2级字段3个真实packed变异。
- growth-supply-compatibility.json：本最终图四路32波奖励、幂等/延迟/结束与饱和异常全部PASS；奖励源码未变。资源差异使用本批精确+38规则，不调用旧奖励专用无w3a变更规则。
- cdr-manager-list-tests.log：修复levels与第6参fixture后，相关4项拒绝变异全部PASS（正CD、receiver换绑、错order、未知caller/越域rawcode与family/战塔挂载）。旧完整Python43项未完成重跑，cdr-full-suite-interrupted.log只是中断前7个通过进度，不是完整PASS，不计作发布门禁。
- Astra独立复核完整实际manager、源码与checks/build输入，独立重跑上述packed正向/3变异/delta：PASS WITH NOTES（仅未Warcraft实机）。

源校验显式使用3aefc08作为baseline；历史默认c9d59e在本克隆不存在，因此不声称VerifyPetManagerSource.py的默认历史全脚本PASS。其旧随机/技能/readyAt及六个战斗包由精确方法体/文件比较锁定。

## 已拒绝的中间结果

首轮CDR职责/测试命名失败、实际两栏误挂第3栏均已修复并经最终全部测试验证。旧图a3c1916a591e7e5451932306d8bef9d496eb2a1e0ad3af1efce09109b9ada937留下9个第2级Channel字段，被完整门禁拒绝，不可发布。最终通过精确levels参数修复，并补同oracle残留级别变异检测。失败事务/被拒图及manifest仍保存于各原事务和归档，不删除证据。

未运行Warcraft；实际渲染/选择/网络排队事件/加载时间/FPS不在自动验证范围。未改工资、进化、路线或战斗数值；继承第1批0c59488的全部验证文档与保底工具。未push。
