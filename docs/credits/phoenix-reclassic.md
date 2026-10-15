# 赤翎凤凰：Phoenix (Re-Classic) 来源与适配

原模型作者为 **johnwar**，发布页为 [Phoenix (Re-Classic)](https://www.hiveworkshop.com/threads/phoenix-re-classic.353829/)。作者在原页明确表示：

“Anyone can edit my models as long as you give proper credits.”

本项目据此保留作者署名，未将其标为 CC0、公共领域或本项目原创模型。原始 PhoenixV2.mdx 的 SHA256 为 `b2a890fe0062d3f0214725f0daa0f747fc11e233b5f0daa811a88caa0c38aeeb`。未改原始模型和原网页证据保存在素材恢复包中，不重复加入生产 imports。

## 本项目修改

- 沿用 johnwar 的网格、骨架与成熟动作，进行本任务所需的 UV、尾羽细节与新绘贴图适配。
- 使用内置 imagegen 绘制两张自定义纹理，保留原图、准确提示词、确定性 BLP1 转换及修改来源。
- 地图实际调用的动画索引统一为 0–4 基础动作、5–9 Float / Jump / Spin / Sleep / Cast。部分显示动作是现有成熟飞行动作的语义映射，并非新造完整360度旋转或地面睡姿。
- 独立野生模型仅用于物编的 species 10；主附身模型保持认可的尺度与原点。野生派生只保留基础动作，按确定性规则平移坐标并作对象比例补偿。没有增加每帧脚本。
- 原先黄色光片、装饰粒子与拖尾的运行时预算由本次最终资源审计记录；没有改变现有绑定星光或技能发动的游戏脚本。

最终生产路径、哈希、动作/材质统计与纹理清单以 `assets/source/elemental-spirits/import-manifest.json` 及本次验证报告为准，不使用历史候选哈希冒充最终资源。

## 署名与原生资源边界

地图内嵌 `Credits-Phoenix.txt`，与本文保留同一来源和署名。该文件是 MPQ 内的署名文件，不是新增 F9 帮助界面。

引用的 Warcraft III 原生纹理、队伍色与事件资源归 Blizzard；作者的模型编辑许可不等于原生贴图独立再分发许可。本次仅打包新绘自定义纹理，原生路径在最终 manifest 显式列出。本云环境未读取目标 Warcraft III 1.27a 安装包，因此原生依赖、实际灯光、粒子、遮挡和帧率仍需本地试玩确认。

原生 Death 包含下落后消失的表现。野生版本按 Stand / Walk 保持低悬浮，没有为死亡末段把活体整体抬高，也没有改写原生死亡轨迹；死亡后半会下沉到地面以下。正常捕获及到期移除不依赖完整 Death 播放。

野生专用源还保留 Attack 的原生俯冲和 Portrait 的原生锚点；+73 后这些动作的部分羽片可能低于地面。野生单位禁止攻击，正常游玩不调用 Attack；头像视角没有场景地面。本次不为未调用动作重新改写原骨骼轨迹。
