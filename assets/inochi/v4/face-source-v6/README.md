# 原画眼睑

运行 `scripts/prepare-v4-blink-source.py` 重建。原睫毛和虹膜来自原画；闭眼睫毛、露出的皮肤来自既有完整补画，经配准和选区蒙版提取。虹膜保持圆形，由闭合眼睑遮挡，不绘制替代眼形。

`manifest.json` 给出九级开合与左右插槽位置。`blink-motion-check.png` 是源图检查；实际绑定和中间值验证见 `validation/source-runtime/report.json`。

所有纹理重采样使用预乘透明度。完全闭眼时检查原眼眶内的黑色残影；素材外黑色透明像素不参与睫毛提取。OpenRaster 保留源材料与中性组合。

AI 辅助生成与维护：GPT-6 Sol。
