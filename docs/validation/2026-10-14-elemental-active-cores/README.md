# 二十种元素主动的可靠核心反馈

生产源码：75202dd。最终图SHA256：c3a50d47b9a5c47677e52ca6cb5bd8081e2f4d792385f8f63a9ba3cef3cb85bc。

每个元素主动最多一个核心特效/闪电，计入既有每次技能8句柄与全局核心40、装饰88、每秒总创建120限制。核心未创建时预留本次槽位并低频重试，过期不补播。需要目标的特效随真实目标有效性清理；寄种按已记录位置转地面，不重新选择目标；结尾转为装饰尾迹时必须先降级准入，不能扩大上限。装饰失败不改变战斗结果。

七个新低面数MDX800核心循环均立即可见，使用同一小型白色纹理；范围与真实技能半径匹配。冻结/陨石等具体阶段由真实战斗回调触发表现，循环模型不自行按预定时间假扮命中。

## 实际验证与复用边界

- 官方完整checks/build通过；生产源码、imports、配置与构建输入匹配。后续只改Python验证夹具和文档，不重构图。
- 实际MPQ七模型+共享纹理精确字节/哈希与源清单一致。
- 全22技能×12模式×131帧完整有序战斗轨迹与正式基线一致。文件存逐案例hash及原大报告hash，不重复提交逐帧原始轨迹。
- Retention当前23登记组分段全部覆盖：原lifetimes/aborts/lifecycle各独立报告通过；原admission在coreOverlapStress前明确通过7组，后因测试把四路放在同一点而超过解释器保护上限，原FAIL日志保留。修为四条物理路线后，40核心同秒压力及后续三个生命周期组重新通过。
- 更强的单/双context真实Vortex正例、40结束引用和索引归零验证了共享目标记录。旧观察器错误要求每个context退出就把共享record归零；现改成精确扣减本context持有次数，其他context仍可合法持有。26个负向变异全部拒绝，包含漏release、双release。
- 旧overlap坐标夹具和新增late-target-loss-after-stage也已定向重跑；没有提高10000步解释器阈值，也没有减少40塔、20技能或同秒核心压力。
- 15精灵动作复用前批9f8地图实际门禁：此c3图中15MDX/15BLP字节完全相同，DisplayRuntime/Rules源码不变。不得描述为c3重新跑了525组合动作门禁。

所有执行的是实际packed JASS配受控原生桩。Warcraft 1.27a原生画面、附着贴合与FPS未实测。此批不改伤害、冷却、技能品质或成长经济。

非阻塞观察：寄种在已死亡目标上的起始地面core可能与一次装饰同位，仍受装饰额度限制；不为此增加构建或扩大特效上限。

完整复现：
```
python3 tools/VerifySpiritActiveRetentionArtifact.py ExampleMap.w3x --output retention-full.json
python3 tools/VerifyAllSpiritActiveVisualTrace.py ExampleMap.w3x --baseline BASELINE.w3x --output all22-full.json
```
