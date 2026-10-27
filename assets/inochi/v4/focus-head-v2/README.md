# 专注俯视头部 v2

原画头部不再使用纵向缩放或虹膜形变模拟低头。新增独立绘制的俯视头部，只用等比缩放和位移注册到原肩颈位置。开始专注时切换此姿势，暂停恢复原画；摸头保持俯视头部，只作小幅点头。

- head-painted / blink-painted / mouth-painted.png：内置 image_gen 原始编辑输出，提示词见 PROMPTS.md。
- head-reference.png：从原画拆层重组的编辑参考。
- head.png：注册后的完整俯视底图。
- left/right-blink.png：只覆盖眼部开口的闭眼补画，原生网格下落遮挡原眼睛。
- mouth-open.png：独立说话补画。
- manifest.json：等比注册尺寸与锚点，未使用头脸非等比缩放。

生成：python scripts/prepare-v4-focus-head.py。随后重新导出身体模型；运行时使用 ParamWorkLookDown 切换透明度，不绑定头部缩放或眼球挤压。

兼容层的 opacity_mode=multiply 是可见性包络，乘在原有眨眼/嘴型透明度之上，避免恢复坐姿时所有旧嘴型同时显示。单元测试覆盖此交互，真实浏览器验证新旧姿势的闭眼、说话、复位和遮挡。
