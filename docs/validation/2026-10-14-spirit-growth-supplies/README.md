# 第一批：路线成长保底

按已批准方案追加材料，不替换原球与共鸣：
- 第4、12波各1开栏石。
- 第4、12、20、28波各2洗练石。
- 单路合计2开栏、8洗练；原4/8/13/19波各6球、开局3球保持。

沿用tdPetCreditWave的lane×wave账本；只有真实标记结算的有效活跃路线可领取。重复、延迟旧波、不同路线分别处理。库存饱和安全减法后累加；球满、无精灵或满收藏不阻止材料。提示显示实际到账数量，库存无变化不虚报。

风险为既有状态和结算接口内的普通局部扩展；root实施和验证，前置Astra PLAN已给出具体边界，不冒称另有高风险代码审查。

源码3aefc08，地图SHA256：657c55c619d03eacec6fdfe116fdefbfd9c0b952558fcd2966daee0dcae8c50d。
Linux官方完整checks/build通过；Wurst新增5测试覆盖累计、幂等、跨路/延迟、关闭路线和资源边界。实际packed replay覆盖4路×32波、6种拒绝状态、饱和/异常库存、无库存重领、非法事件及3个负向变异；资源与物编逐字節不变，仅war3map.j与w3i变化。详见packed.json和build-summary.json。

```
python3 tools/VerifyPetGrowthSupplyArtifact.py ExampleMap.w3x --baseline BASELINE.w3x --output packed.json
```

本批不包含定向学习、工资或每路进化。Python使用受控原生桩；未进行原生Warcraft游戏测试，未验证实际通关时长或经济余额。
