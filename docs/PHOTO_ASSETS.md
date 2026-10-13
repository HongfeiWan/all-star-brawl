# 照片头像与照片脸 · v0.3.0

本轮为 IKUN、刘华强、瓜摊老板三位接入真实照片。图鉴、快捷选人与预览对照采用本地图片；三维脸部采用有深度的曲面、照片 UV 和独立表情。其余 125 位仍使用程序化风格脸，照片覆盖数量不等于名册数量。

## 来源与素材标识

| 角色 | 人物身份和素材 | 来源与署名 | 文件 |
| --- | --- | --- | --- |
| IKUN | 蔡徐坤 2018 COSMO 活动本人照片；不是篮球原视频截图 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Cai_Xukun_in_2018.jpg)。摄影 Rosethron丨蔡徐坤，原图裁剪 Masdggg。[CC BY 2.5](https://creativecommons.org/licenses/by/2.5/)。本项目做显示裁剪及 UV 重映射 | `public/assets/portraits/ikun.jpg` |
| 刘华强 | 孙红雷在《征服》买瓜片段的正脸帧 | [观察者网 / 新浪，2019-07-16](https://news.sina.cn/2019-07-16/detail-ihytcerm4065290.d.html)。从页面 GIF 的首帧提取，原图 240×200；网页未提供开放素材许可 | `public/assets/portraits/huaqiang-frontal.png` |
| 瓜摊老板 | 李广奇在《征服》中饰演的瓜摊老板；不能误当孙红雷 | [搜狐人物文章，2021-09-12](https://www.sohu.com/a/489418830_100120160)。采用其中角色画面，原图 1402×912；网页未提供开放素材许可 | `public/assets/portraits/guatan.png` |

外部照片的权利及许可分别保留，不纳入本仓库的 MIT 授权。`public/assets/ikun.glb`、`public/assets/roster/huaqiang.glb`、`public/assets/roster/guatan.glb` 内嵌了这些照片，也包含上述素材部分。这里的出处记录不是对未提供开放许可素材的授权声明。照片之外的本项目代码、原创几何和关键帧仍按根目录 LICENSE 列示。

## 实际制作方法

- 原照片保留，图鉴的脸部取景通过显示参数完成；`shared/portraits.js` 保存身份、出处、尺寸和取景框。
- `art/photo-faces.json` 保存照片路径、双眼、鼻尖、嘴角和脸缘测量值。转头照片先按五官位置重映射到对称脸部，再投射到三维曲面。
- 去掉原有可见眉、眼、鼻、唇小几何，避免出现照片与模型两套五官；保留后脑、耳朵、发型和身体骨架。
- 立体脸网格附着 `head` 骨，保留浅鼻梁、鼻尖与嘴部深度。`blink / angry / smile / hurt` 各自改变曲面，UV 固定在基础形态上，照片五官随网格运动。
- 照片脸在游戏中使用无光材质，避免原照片的光照再叠加场景阴影；脸缘逐渐透明，与原头壳衔接。
- 照片内嵌 GLB，保留 16 根骨。IKUN 保留原 7 个动作，华强与瓜摊老板继续共享对应动作族。游戏运行时不从外部图站取图。

在仓库根目录重新生成预览：

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python tools/apply_photo_faces.py -- --config art/photo-faces.json
```

默认输出到工作目录的 `work/photo-model-preview/`。可指定 `--output-dir`，或 `--only huaqiang` 只处理一位。检查完成后，加 `--write-assets` 更新游戏内三份 GLB。其他系统使用自己的 Blender 可执行文件运行同一脚本。

重新运行旧人物生成工具会恢复原来的风格化脸；随后重跑照片工具即可恢复照片版。原 `.blend` 文件保留风格化身体和头部基础，照片曲面由脚本与测量配置复现。

## 检查与限制

三位的正脸、侧脸和四种状态均在桌面 Chrome 实际加载查看，照片路径和表情播放无页面错误。华强与瓜摊老板完成两个浏览器会话的四回合对战，包含快攻、重击、格挡和绝招。实际截图与录像见 [验证记录](VALIDATION.md)。

这仍是照片脸原型：华强原图低清；转头照的 UV 校正会拉伸局部细节；侧面、肤色接缝及闭眼形态可继续打磨。曲面形变不等于完整三维肖像扫描、真实眼睑解剖或逐人面部动作捕捉。
