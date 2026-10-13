# 美术与动作说明

当前资产是本项目制作的可编辑、手工风格化角色。三名人物各有 **16 根骨骼、7 个动作、4 个独立面部形态控制**；运行时用 Three.js 播放，不需要 Blender 或在线生成服务。

## 人物与动作

| 人物 | 造型与武器 | 动作区别 |
| --- | --- | --- |
| IKUN | 分束银发、背带、运动鞋、带接缝篮球 | 快攻前推、重击上钩、绝招举球后下砸 |
| 王司徒 | 官帽、白须、层叠衣袍、羽扇 | 扇面横挥、掌扇前推、指斥与扇面展开 |
| 吕布 | 赤金甲片、弯曲双翎、方天画戟 | 斜向挥戟、举戟下劈、转身横扫 |

每名角色保留 `idle / attack / heavy / guard / special / hurt / victory` 七个片段，共 21 个。`idle` 与 `victory` 循环，其他动作单次播放，结束回到待机。片段间短暂淡入，旧动作退出后停止，避免过期动作把新攻击重置成待机。

面部控制为 `blink / angry / smile / hurt`。它们独立于骨骼片段，因此可以在挥武器、格挡或待机时叠加表情。

## 前摇、接触与回收

攻击片段长 **1.45 秒**，从出招开始计时，第 **620 毫秒**接触。Blender 使用 100 fps 的制作时间轴，让接触成为真实导出的第 62 帧，而非落在两个采样帧之间。篮球、扇面和戟尖的接触位置按导出的蒙皮姿势测量。

演出先蓄势，再加速命中，随后收招；格挡在来袭前就抬起，覆盖双方的两个动作时段。命中停顿同时保持骨骼、第一人称手部、冲刺和特效的接触姿势：格挡 38 ms、快攻 58 ms、重击 78 ms、绝招 88 ms。之后稍压缩回收段，仍在原服务器时段内结束，不累积联机时间偏移。

第一人称使用专用手指、袖口和武器模型，独立渲染到前景，避免场景阴影和深度裁切把手臂变成遮挡。篮球直击、羽扇横挥、画戟斜扫使用不同轨迹。镜头短暂靠近接触点，受击后有快速回弹；这些移动属于演出，伤害、回合和比分仍由服务器计算。

命中特效使用短促光线、圆环、斩击线和格挡火花，贴合武器接触点；靠近镜头的特效会缩小。音效由 Web Audio 合成，包含挥动声、命中瞬态与低频、格挡金属声；静音会停止已经排队的声音。

## 小动作与表情预览

角色保留自然待机呼吸和间隔眨眼。攻击时轻微收紧表情；受击先疼痛，再短暂生气并逐渐恢复；庆祝时微笑。低于 40% 生命后，表情、头部姿态和呼吸略显紧张。思考阶段有小幅侧看和回看玩家，避免持续夸张摇摆。

首页可以选择 **7 个动作**并重复播放；表情选择提供 **自然、生气、疼痛、开心**四种状态。“查看表情”切换到脸部特写，“查看全身”返回造型预览。自然状态保留自动眨眼；固定表情预览暂停眨眼，便于观察眉眼与嘴角。

启用系统的“减少动态效果”时，关闭镜头冲刺、后坐、受击闪光、命中特效与额外姿态变化；骨骼动作和面部表情继续播放。

## 可编辑位置与限制

- `art/all-stars.blend`：三名人物、材质、骨架、面部形态与 NLA 动作轨道。
- `tools/make_characters.py`：生成与导出脚本。重新运行会覆盖 `.blend` 和三份 GLB；手工修改前先另存副本。
- `public/game.js`：第一人称模型、表情状态、镜头、特效与声音。
- `shared/presentation.js`：接触节奏、恢复曲线与测量得到的武器接触点。重新制作攻击姿势后，需重新测量接触点并检查镜头安全距离。

当前没有动作捕捉、布料或头发物理、手指 IK、自由移动与步幅匹配。衣袍、头发、胡须和翎羽通过模型与骨骼表现；脸部是简化的形态变形，不是完整面部肌肉系统。此轮完善的是风格化原型，写实雕刻、贴图绘制和复杂二次运动仍需后续制作。

## 参考与可选制作工具

参考的是表现组织方法，资产与游戏逻辑在本仓库独立制作：

| 官方参考 | 在本项目中的取舍 |
| --- | --- |
| [Epic Lyra：Animation in Lyra](https://dev.epicgames.com/documentation/unreal-engine/animation-in-lyra-sample-game-in-unreal-engine) | 借鉴不同武器拥有不同姿态、上身表现和瞄准修正的组织思路；本项目使用现有 Three.js 片段与小幅叠加，不引入 Unreal 动画系统 |
| [Three.js：骨骼与 Morph 表情示例](https://github.com/mrdoob/three.js/blob/dev/examples/webgl_animation_skinning_morph.html) | 将循环状态、单次动作与独立面部形态结合 |
| [Godot：Using AnimationTree](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html) | 参考状态切换、动作混合和叠加的概念；本项目没有移植 Godot |

如果后续有明确人物参考图，建议先匹配比例与轮廓，再完善脸部、绑定和动作。以下是可选工作流，**本轮未安装这些 skills，未调用 Meshy 付费生成**：

| Skill / 工具 | 适合下一步做什么 |
| --- | --- |
| [blender-image-to-3d](https://github.com/majidmanzarpour/blender-game-skills/blob/main/skills/blender-image-to-3d/SKILL.md) | 按参考图分阶段制作，用相同视角的渲染对照比例和轮廓 |
| [character-artist](https://github.com/arjun988/blender-skills/blob/main/.claude/skills/character-artist/SKILL.md) | 优化人体比例、脸部拓扑、服饰与风格化发型 |
| [rigging](https://github.com/arjun988/blender-skills/blob/main/.claude/skills/rigging/SKILL.md) | 改善关节、蒙皮权重及更复杂的控制骨架 |
| [animation](https://github.com/arjun988/blender-skills/blob/main/.claude/skills/animation/SKILL.md) | 精修预备姿势、运动弧线、重心、接触和回收 |
| [Meshy 官方 3D Agent skills](https://github.com/meshy-dev/meshy-3d-agent) / [官方 API](https://www.meshy.ai/api) | 可从文字或图像生成资产初稿，再回到 Blender 检查造型、拓扑与动作；使用需要相应账户与额度 |

测试和浏览器观察的最终记录见 [VALIDATION.md](VALIDATION.md)。
