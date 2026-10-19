# 左侧蝴蝶结与前方细白发源工程

当前模型：GPT-6 Sol。

沿原画提取左侧蝴蝶结与贴着其右缘的弯曲白发。原画蓝布主体与白发轮廓保留；生成图只用于被遮挡的蓝布和底发。此阶段白发保持固定，左右蝴蝶结可分别做源素材位移检查。长侧发、后发、完整头发遮挡、表情、正坐姿和真正模型绑定仍未完成。

## 重建

```sh
python3 scripts/prepare-v4-left-bow.py
python3 scripts/separate-v4-left-bow.py
python3 scripts/check-v4-both-bows.py
```

依赖 Pillow、NumPy、opencv-python-headless。`materials-validation.json` 记录工作素材偏移及配准，`joint-validation.json` 记录联合检查范围。

## 原画与补画

- `left-bow-working.png` 的 5654 个蓝布核心像素 RGB 与原画一致。外缘根据原画邻近蓝布颜色估计透明度，避免把白发混合边缘作为实心蓝布带走。
- `white-curl-working.png` 沿原画白发曲线分离，104 个不透明白色核心像素保持原画 RGB。初始选区曾偏左，已逐行核对原画亮色区后修正。当前只验证固定白发与移动丝带的遮挡，尚未为白发绑定动作。
- 内置 imagegen 编辑 `inputs/left-bow-source.png` 与标色指南，分别移除左侧蓝布补出底发（`inputs/bow-hidden-generated.png`），以及移除白发续画蓝布（`inputs/curl-hidden-generated.png`）。提示要求保留原构图、耳毛、未标记白发和两条尾带间的长白发，透明区保持透明，不重画整张角色。
- 生成图改变了部分线条，只将其配准后用于局部遮挡区。配准分别有 12/28、13/71 个内点/匹配，中位误差约 0.213、0.223 原图像素，P95 约 0.325、0.311。拟合检查包含至少 9 个不同位置、超过 500 个放大像素的纵向跨度及受限缩放/旋转；数量低于先前阶段，因此只支持当前局部补画用途，不能当作完整立绘精确配准。
- 检查发现仅按蓝色核心向外扩展会漏掉零散的抗锯齿蓝边；清除范围已补上完整可见蓝边并向外扩展 2 像素，避免底稿留下不连续的小孔。原蓝布可见区域在隐藏底稿中的实心深蓝残留计数为 0。此计数是已知残影问题的检查，不代替最终美术验收。

## 联合检查与可编辑工程

`MewNook-v4-both-bows-source.ora` 默认显示原图参考；隐藏 `JOINT CHECK — long side and back hair incomplete` 组继承上一版源部件，并加入原画左侧蝴蝶结、固定白发与局部底稿。检查工作组时关闭原图参考。导出验证 CRC、默认参考可见像素及实际序列化工作组与中立状态的一致性，再原子替换。

检查左侧五档（-5/-2/0/+2/+5）× 右侧五档（-4/-2/0/+2/+4）共 25 种组合。两侧前方白发的指定可见核心、原虹膜和无关的上一版工作像素保持原样。左侧蓝布中未检测到实心浅白污染，白发中未检测到实心深蓝污染。其他头部部件在本次检查中保持中立状态，未宣称检查全部部件的所有参数组合。

`left-bow-motion-check.png` 为左侧近景；`both-bows-joint-motion.png` 为双侧组合；`left-bow-and-curl-matte-check.png` 为深浅背景分层检查。源工程尚未接入 `/inochi2d-test/smoke`。
