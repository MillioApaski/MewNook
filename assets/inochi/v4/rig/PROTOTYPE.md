# 正坐姿 v4 原型生成（仅在原画入库后使用）

新的母版规格为 1122 × 1402 的 RGBA 立绘。旧 v3 源图、嘴部坐标与 Inochi 运行资源保持不变。

```bash
python -m pip install Pillow numpy opencv-python-headless
python scripts/build-mewnook-v4.py
python scripts/check-mewnook-v4.py
```

生成输入：`assets/inochi/v4/source/pose_reference.png`。

生成输出：`assets/inochi/v4/rig/MewNook-v4-prototype.inx`。

这一版只是 **11 个纹理部件 / 4 个面部参数的工程原型**。模型具有左右独立的眼睛、临时闭眼遮挡和根据新原画定位的小张口/大张口素材。它尚未经过网页 WebGL 视觉验收，不包含真正独立的头发、耳朵、尾巴和手臂补画网格，也不是正式 Inochi Creator 绑定工程。

**输入源图仍需放入 GitHub。** 聊天附件生成的 15 图层 ORA、源 PNG 与临时 .inx 可以作为手工加工的初始材料；仓库内的脚本可以在母版上传后重新生成本地实验模型。不要把它自动设为主页面默认角色。