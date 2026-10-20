# MewNook v4 原画实验模型

当前版本已接入独立测试页 `/inochi2d-test/smoke`，默认显示双腿不交叉、双膝靠拢的新坐姿。支持原画眼睑、连续口型、左右眉毛、摸头时的头部/头发/猫耳联动，以及尾巴和呼吸。同一模型现已作为正式房间的默认角色。

最新源工程：

- `face-source-v5`：原虹膜、眼白与注视遮罩修复。
- `face-source-v6`：原睫毛、闭眼补画、九级眼睑关键帧。
- `face-source-v7`：完整口腔补画、原微笑、左右眉毛和组合表情。
- `hair-source-v1` 至 `hair-source-v10`：原画发片与必要隐藏区补画；各目录记录对应阶段。
- `pose-source-v1`：正坐姿补画候选。
- `scene-source-v1`：最新整身源工程、33 个部件及绑定位置。
- `validation/source-runtime`：实际 WebGL2 截图与动作/复位检查结果。

生成运行时模型：`python scripts/build-mewnook-v4-source-rig.py`。输出经验证后复制到 `public/inochi2d-test/models/MewNook-v4-review.inx`。测试步骤和范围见 [修复清单](../../../docs/V4_REPAIR_TODO.md)。旧目录包含弃用候选，不应直接混用旧部件。

所有 left/right 均按画面左右命名。OpenRaster/PNG 为可编辑源素材，并非 Inochi Creator 原生工程；当前模型只实现已验证的小幅动作。源工程不发布到网站 public 目录。

AI 辅助生成与维护：GPT-6 Sol。
