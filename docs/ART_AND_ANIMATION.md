# 美术与动作说明

`v0.4.0` 包含当前调研集合中的 **128 位可选角色**。原三位保留各自的模型、表情与动作；新增 125 位采用独立模型和共享动作库。运行时用 Three.js 播放，不需要 Blender 或在线生成服务。

名册截至 **2026-10-13**，出处与身份合并说明见 [ROSTER_RESEARCH.md](ROSTER_RESEARCH.md)。鬼畜全明星没有固定官方全集，这里的 128 位是可持续扩展的研究集合。

## 人物与动作

| 人物 | 造型与武器 | 动作区别 |
| --- | --- | --- |
| IKUN | 分束银发、背带、运动鞋、带接缝篮球 | 快攻前推、重击上钩、绝招举球后下砸 |
| 王司徒 | 官帽、白须、层叠衣袍、羽扇 | 扇面横挥、掌扇前推、指斥与扇面展开 |
| 吕布 | 赤金甲片、弯曲双翎、方天画戟 | 斜向挥戟、举戟下劈、转身横扫 |

原三位各自内嵌 `idle / attack / heavy / guard / special / hurt / victory` 七个片段，共 21 个。新增 125 个独立 GLB 各有 **16 根骨骼和 4 个面部形态**，通过兼容骨骼名称引用四个共享动作族：

| 动作族 | 表现方向 | 储存位置 |
| --- | --- | --- |
| `knife` | 短刃、切入和收腕 | `public/assets/motions/knife.glb` |
| `orb` | 篮球、瓜和其他圆形道具的推送、抛击 | `public/assets/motions/orb.glb` |
| `staff` | 长柄、挥扫和下劈 | `public/assets/motions/staff.glb` |
| `brawler` | 徒手、拳套和近身击打 | `public/assets/motions/brawler.glb` |

每族均有七个片段，因此实际储存量是 **21 + 4 × 7 = 49 个片段**。新增角色复用动作，尚未为 128 人分别制作独占动作或动作捕捉。每位的道具尺寸、实际动作族和测量接触点由生成元数据提供。

`idle` 与 `victory` 循环，其他动作单次播放，结束回到待机。片段间短暂淡入，旧动作退出后停止，避免过期动作把新攻击重置成待机。

面部控制为 `blink / angry / smile / hurt`。它们独立于骨骼片段，因此可以在挥武器、格挡或待机时叠加表情。

新增 125 份模型合计约 **130.6 MiB**，单体约 **0.55–1.83 MiB**，几何约 **17.8k–59.6k 三角面**，含华强与瓜摊老板的照片曲面。资源统计和检查见 [验证记录](VALIDATION.md)。首页显示 6 位常用角色，图鉴可搜索和分类查看 128 位；选择人物时才载入其模型，模型缓存控制在 12 个，四个动作库分别复用。打开图鉴不需要先下载全部人物。

IKUN、刘华强与瓜摊老板已试用照片头像和三维照片脸：保留身体、骨骼及动作，原可见五官替换为有深度的照片曲面，表情单独控制。照片路径、五官标记、UV 校正和复现命令见 [PHOTO_ASSETS.md](PHOTO_ASSETS.md)。其余 125 位仍为风格化脸；旧 `.blend` 保留原基础，照片版通过制作脚本复现。

全部 125 位新增人物都使用 `art/character-profiles.json` 的逐角色造型配置；移除了用身份哈希随机修改脸型的方式。衣袍、军服、运动服、衬衫、西装、旗袍、围裙和盔甲各自补充构造细节。人物以风格化演绎为目标，比例、背面服装与装饰属于推断，配置逐项标明；来源视频封面可能是多人合集或二创图，不能自动当作对应人物的肖像。

本轮按三项已读取的技能实施：

| Skill | 本项目实际采用的部分 |
| --- | --- |
| [character-artist](https://github.com/arjun988/blender-skills/blob/main/.claude/skills/character-artist/SKILL.md) | 先确定人物轮廓与比例，再完善头部曲面、五官、发束与服饰；源网格使用环状四边面，头脸、皮肤、服装、头发配饰、硬甲和武器分件 |
| [rigging](https://github.com/arjun988/blender-skills/blob/main/.claude/skills/rigging/SKILL.md) | 连续手臂代替交叠球体，肩、肘、膝使用归一化渐变权重；每顶点最多四项骨权重，硬质武器保持刚性；沿用固定 16 骨接口 |
| [animation](https://github.com/arjun988/blender-skills/blob/main/.claude/skills/animation/SKILL.md) | 保留蓄势、接触、惯性和回收；源关键帧使用 Bezier 自动夹紧手柄，NLA 轨道导出；叠加小幅性格待机与怒气手部变化 |

新增模型各有 4–6 个导出网格，面部形态保留在脸部网格，衣服与武器不复制整套表情数据。普通脸部增加平滑鼻梁、颊部及嘴唇体积；头发采用贴合头皮的卷束和分层发片，胡须使用较细的渐变发束。服装有肩缝、袖口、拉链、口袋、领片、裙褶、旗装花纹和甲片铆钉；道具补握柄缠线、话筒网格、书页和袋面标记。

颜色配置统一为 sRGB，制作时转换到线性材质空间，避免深色夹克被渲染成灰色、肤色发白；第一人称袖口和手部读同一配色。自然、生气、全身和绝招画面逐人保存为 [125 位精修图集](character-refinement-gallery.html)，另有 [精修前后对照](character-refinement-comparison.jpg)。这是一轮系统性风格化精修，仍非逐人手工雕刻、照片扫描或电影级人物资产。

## 前摇、接触与回收

攻击片段长 **1.45 秒**，从出招开始计时，第 **620 毫秒**接触。Blender 使用 100 fps 的制作时间轴，让接触成为真实导出的第 62 帧，而非落在两个采样帧之间。原三位的篮球、扇面和戟尖，以及新增人物的道具接触位置，均按对应骨骼姿势测量；新增人物的数据在 `shared/roster-contacts.js`。

演出先蓄势，再加速命中，随后收招；格挡在来袭前就抬起，覆盖双方的两个动作时段。命中停顿同时保持骨骼、第一人称手部、冲刺和特效的接触姿势：格挡 38 ms、快攻 58 ms、重击 78 ms、绝招 88 ms。之后稍压缩回收段，仍在原服务器时段内结束，不累积联机时间偏移。

第一人称使用专用手指、袖口和武器模型，独立渲染到前景，避免场景阴影和深度裁切把手臂变成遮挡。篮球直击、羽扇横挥、画戟斜扫使用不同轨迹；新增人物优先读取实际模型的道具与配色配置，和研究名册中的粗分类分别保存。镜头短暂靠近接触点，受击后有快速回弹；这些移动属于演出，伤害、回合和比分仍由服务器计算。

命中特效使用短促光线、圆环、斩击线和格挡火花，贴合武器接触点；靠近镜头的特效会缩小。音效由 Web Audio 合成，包含挥动声、命中瞬态与低频、格挡金属声；静音会停止已经排队的声音。

## 小动作与表情预览

角色保留自然待机呼吸和间隔眨眼。攻击时轻微收紧表情；受击先疼痛，再短暂生气并逐渐恢复；庆祝时微笑。低于 40% 生命后，表情、头部姿态和呼吸略显紧张。思考阶段有小幅侧看和回看玩家，避免持续夸张摇摆。

首页可以选择 **7 个动作**并重复播放；表情选择提供 **自然、生气、疼痛、开心**四种状态。“查看表情”切换到脸部特写，“查看全身”返回造型预览。自然状态保留自动眨眼；固定表情预览暂停眨眼，便于观察眉眼与嘴角。非循环预览使用实际经过时间定位片段，避免低帧率时出招被拖慢；混合器仍推进，保留交叉淡入。

启用系统的“减少动态效果”时，关闭镜头冲刺、后坐、受击闪光、命中特效与额外姿态变化；骨骼动作和面部表情继续播放。

## 可编辑位置与限制

- `art/all-stars.blend`：三名人物、材质、骨架、面部形态与 NLA 动作轨道。
- `art/huaqiang.blend`、`guatan.blend`、`zhugeliang.blend`、`zhangfei.blend`、`snowking.blend`、`wukong.blend`、`tangseng.blend`、`bajie.blend`：八位已重建的可编辑代表人物，含分件、骨架、表情和共享动作。
- `art/character-profiles.json`：全部新增人物的精修配置、参考特征、来源和推断说明。
- `tools/make_characters.py`：原三位的生成与导出脚本，默认行为保持不变。重新运行会覆盖 `art/all-stars.blend` 和原三份 GLB；手工修改前先另存副本。
- `tools/make_roster.py` 与 `tools/refine_roster.py`：新增人物、细节、分件、蒙皮、四个动作库、实际视觉配置和接触点。
- `shared/roster.js`：名册、别名、出处和研究分类。`shared/catalog.js` 将名册与生成配置合成运行时目录。
- `shared/roster-contacts.js`：新增人物的 `ROSTER_MOTIONS`、`ROSTER_CONTACT` 和 `ROSTER_VISUAL`，对应已生成的实际道具、服装与配色。
- `public/game.js`：第一人称模型、表情状态、镜头、特效与声音。
- `shared/presentation.js`：接触节奏、恢复曲线与原三位的武器接触点。重新制作攻击姿势后，需重新测量接触点并检查镜头安全距离。

在仓库根目录重新生成华强并保存可编辑文件：

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python tools/make_roster.py -- --only huaqiang --save-blend --skip-motions
```

其他系统使用自己的 Blender 可执行文件运行同一脚本。`--only` 接受一个新增角色 ID 或逗号分隔的多个 ID；`--save-blend` 保存 `art/<id>.blend`；`--skip-motions` 保留已有四个动作库。省略 `--only` 生成全部新增角色，省略 `--skip-motions` 重建动作库。工具会更新所选模型的接触点和实际视觉配置，并保留其他角色的生成元数据。单人重做后仍需在预览与对战中观察动作、表情和第一人称道具是否一致。

当前没有动作捕捉、布料或头发物理、手指 IK、自由移动与步幅匹配。衣袍、头发、胡须和翎羽通过模型与骨骼表现；脸部是简化的形态变形，不是完整面部肌肉系统。三位照片脸也不是完整肖像扫描；低清素材、侧面接缝及眼睑仍可继续精修。

## 参考与可选制作工具

参考的是表现组织方法，资产与游戏逻辑在本仓库独立制作：

| 官方参考 | 在本项目中的取舍 |
| --- | --- |
| [Epic Lyra：Animation in Lyra](https://dev.epicgames.com/documentation/unreal-engine/animation-in-lyra-sample-game-in-unreal-engine) | 借鉴不同武器拥有不同姿态、上身表现和瞄准修正的组织思路；本项目使用现有 Three.js 片段与小幅叠加，不引入 Unreal 动画系统 |
| [Three.js：骨骼与 Morph 表情示例](https://github.com/mrdoob/three.js/blob/dev/examples/webgl_animation_skinning_morph.html) | 将循环状态、单次动作与独立面部形态结合 |
| [Godot：Using AnimationTree](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html) | 参考状态切换、动作混合和叠加的概念；本项目没有移植 Godot |

本轮直接读取并采用上述三项 skill 源码说明，通过现有本地 Blender 执行；没有增加付费生成服务。以下属于可选后续工具，没有执行其完整流程：

| Skill / 工具 | 适合下一步做什么 |
| --- | --- |
| [blender-image-to-3d](https://github.com/majidmanzarpour/blender-game-skills/blob/main/skills/blender-image-to-3d/SKILL.md) | 按参考图分阶段制作，用相同视角的渲染对照比例和轮廓 |
| [Meshy 官方 3D Agent skills](https://github.com/meshy-dev/meshy-3d-agent) / [官方 API](https://www.meshy.ai/api) | 可从文字或图像生成资产初稿，再回到 Blender 检查造型、拓扑与动作；使用需要相应账户与额度 |

测试和浏览器观察的最终记录见 [VALIDATION.md](VALIDATION.md)。
