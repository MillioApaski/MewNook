# 已确认的困倦小开口

2026-10-22 用户确认：眼睛自然闭合，嘴唇只有很小的开口，眉毛放松。

本工程使用 face-source-v7 已有口腔材质及皮肤底稿，沿嘴部本地轴缩小到 0.36 × 0.22，保留原画唇边、口腔和高光。新开口可见范围约 12 × 7 原画像素；63 × 47 插槽覆盖原微笑，避免重复嘴巴。

- `MewNook-v4-sleepy-mouth.ora`：可编辑的口腔材质与皮肤支持层。
- `mouth-material-full.png`：注册到原画坐标的透明口腔材质。
- `mouth-sleepy.png`：运行时插槽。
- `manifest.json`：坐标、源材质哈希及变换参数。

运行 `python scripts/prepare-v4-sleepy-source.py` 可重新导出，然后运行 `python scripts/build-mewnook-v4-source-rig.py`。运行时通过 ParamDrowsyMouth 平滑覆盖中性嘴部，讲话时释放。
