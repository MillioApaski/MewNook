# 固定皮肤与独立眼部素材 · 第一版

这是素材重建阶段，未替换正式页或测试页的运行时模型。先审阅素材分层、颜色和开合，再进行全头网格绑定与动作适配。

## 素材

- `face-skin-fixed.png`：imagegen 补画的无眼、无眉、无头发皮肤底稿，保留脸颊腮红、鼻子和自然嘴部。放到原画 1122×1402 坐标中，增加水平方向 underlap。该底图在所有眼部姿态中完全不变。
- `left/right-sclera.png`、`*-iris.png`：原画独立眼白、虹膜，透明背景。
- `*-upper/lower-lid-skin.png`、`*-lid-skin.png`：从同一固定底图取得的独立眼睑皮肤材质，供上下眼睑网格使用。
- `*-upper/lower-lash.png`、`*-closed-lash.png`：沿用原画透明睫毛材质，不包含旧版肤色矩形。
- `hair-foreground.png`、`hair-part-*.png`：现有原画前发合成及独立分件，原 alpha 保留。
- `brows.png`：独立眉毛。
- `MewNook-face-materials.ora`：真正可编辑的 OpenRaster 工程；张眼合成组可见，素材组隐藏，可逐层检查。
- `assembly-0/50/100.png`、`material-review.png`：素材级开合合成对照，仅用于审阅，不作为运行时整块脸部切换贴图。
- `manifest.json`：坐标、哈希、检查结果和状态。

生成输入与原画参考在 `inputs/`。`eyeless-painted.png` 是保留头发的补画研究稿，最终固定皮肤使用 `skin-only-painted.png`；前者不用于最终皮肤合成。生成方式：内置 imagegen。

补画提示：保留原画倾斜角度、脸型、腮红、鼻子和嘴部，移除所有眼睛、睫毛、眼睑折痕、眉毛与头发，补齐刘海后的连续皮肤，以透明背景输出固定的皮肤底层；无模糊滤镜。

## 重建与检查

`python scripts/rebuild-v4-face-materials.py`

检查五级姿态中皮肤底图和前发输入逐像素不变、闭眼时眼白与虹膜 alpha 为零、眼部材质没有不透明矩形皮肤底色、ORA 归档完整。已人工查看开合对照。素材仍待视觉验收；原画轮廓注册、全头连接、独立上下眼睑网格、说话小口及正式运行时回归是后续绑定阶段，不在本素材提交中宣称完成。
