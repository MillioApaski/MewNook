# 正坐姿整身原画组合

运行 `scripts/prepare-v4-upright-scene.py` 重建。新坐姿下半身使用必要补画，头发换回原画拆层；提取前景躯干、衣服、手、静态左右腿、脸颈、耳朵、尾巴与椅子，保留隐藏搭接。

`manifest.json` 含 33 个部件的画布位置、遮挡顺序、头部从属、颈部枢轴与耳根标记。耳根固定，耳尖变形；长发末端留在身体坐标，连接发片跟随头部。当前头部转动范围约 ±3.2°，用于摸头回应；不是大幅转头模型。

`upright-assembled.png` 为组合检查；`MewNook-v4-upright-assembly.ora` 为可编辑分层源工程。绑定由 `build-mewnook-v4-source-rig.py` 完成，实际运行结果见 `validation/source-runtime`。

AI 辅助生成与维护：GPT-6 Sol。
