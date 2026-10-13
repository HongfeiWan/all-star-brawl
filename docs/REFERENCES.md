# 参考项目与选型记录

查阅日期：2026-10-13。

| 参考 | 借鉴内容 | 对本项目的取舍 |
| --- | --- | --- |
| [Three.js 官方骨骼动画混合示例](https://github.com/mrdoob/three.js/blob/dev/examples/webgl_animation_skinning_blending.html) | 骨骼动画、片段切换和混合 | 使用 GLB + AnimationMixer，原创建模与关键帧 |
| [Three.js Animation System](https://threejs.org/manual/pages/animation-system.html) | 动画播放器、单次动作和循环动作 | 动作间 120ms 淡入，待机与庆祝循环 |
| [LukeTsengTW/threejs-multiplayer-fps](https://github.com/LukeTsengTW/threejs-multiplayer-fps) | 浏览器第一人称房间、服务端权威状态、客户端演出 | 用更小的 Node HTTP + ws 实现回合对战，无需 FPS 射击与实时跑图系统 |
| [websockets/ws](https://github.com/websockets/ws) | WebSocket 服务端、心跳与数据大小限制 | 服务端房间通信使用该依赖 |
| [IYanel-DEV/FirstPerson-Multiplayer](https://github.com/IYanel-DEV/FirstPerson-Multiplayer) | Godot 第一人称多人模板 | 作为桌面引擎方案参考；首版浏览器入口更适合同局域网直接加入 |

Q 宠大乐斗相关公开搜索主要发现自动化助手，例如 [gaoyuanqi/daledou](https://github.com/gaoyuanqi/daledou)。它是原游戏的操作助手，不是第一人称游戏源码，因此没有作为游戏底座。

所有参考仅用于了解架构和玩法方向。本仓库没有从这些项目导入代码、模型、贴图或音频。

## 资产来源

| 资产 | 来源 | 可编辑位置 |
| --- | --- | --- |
| 三名角色、武器与骨骼 | 本仓库 Blender 生成脚本 | `art/all-stars.blend`、`tools/make_characters.py` |
| 七类动作，每个角色各一组 | 本仓库关键帧 | Blender NLA Tracks |
| 第一人称手部、武器、擂台与粒子 | 本仓库 Three.js 几何体 | `public/game.js` |
| 操作、出招和命中音效 | Web Audio 程序合成 | `public/game.js` |
| 图标和界面 | 本仓库 SVG / HTML / CSS | `public/` |

人物采用风格化卡通表达，没有使用真人肖像扫描或影视画面。
