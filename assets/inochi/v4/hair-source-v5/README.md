# 发冠、呆毛与四片前发联合源工程

当前模型：GPT-6 Sol。

此工程继续沿原画拆层。发冠主体来自原画与上一阶段呆毛根部补画，不采用生成图替换整颗头部。侧后发、丝带旁发束、姿势、表情与真正模型绑定尚未完成。

## 文件与重建

依次运行：

```sh
python3 scripts/prepare-v4-crown.py
python3 scripts/repair-v4-crown.py
python3 scripts/check-v4-crown-assembly.py
```

`crown-mask.png` 沿原画发冠与耳根边界手工追踪。`crown-source.png` 偏移 `(436,50)`，保留原画色彩及上一阶段局部根部补画。工作版 `crown-full.png` 的半透明选区边缘按实际补画背景重新计算，避免柔边叠加出现第二条轮廓；低透明度外缘保留原图透明度与 RGB，不将透明杂色变为实色。

内置 imagegen 使用 `inputs/head-no-ahoge.png` 和标色的 `inputs/crown-guide.png` 编辑。要求移除标色发冠、补画其下连续白紫色底发，保留猫耳、刘海、发卡及构图，透明背景，不添加呆毛。结果 `inputs/crown-hidden-generated.png` 改动了整张局部图的其他线条，因此只消费发冠选区内的隐藏底发。

`registered-crown-hidden.png` 由保留区域特征配准：69 个内点 / 278 对匹配，中位误差约 0.286 原图像素，P95 约 0.455。初次向选区外扩展补画导致耳侧重复线，已收紧为原选区范围；这也意味着侧发完成后仍需复查更大运动范围的遮挡。

`crown-motion-check.png` 检查发冠 -3/0/+3 像素弯曲。`ahoge-front-joint-motion.png` 显示前发与呆毛的九个组合，发冠参数为 0。`crown-joint-motion.png` 显示发冠三个参数，前发与呆毛均为 0。实际执行全部 75 种组合：前发五档 × 呆毛五档 × 发冠三档。检查原虹膜 RGB、固定眼尾核心 RGB 与头部范围外可见 RGBA 保持不变。这些检查不代表动作或美术的最终验收。

`MewNook-v4-head-joint-source.ora` 是当前可编辑联合工程：默认只显示原画参考，隐藏 `JOINT CHECK — side and back hair incomplete` 工作组含原画拆出的发冠、呆毛、四片前发、发卡、固定眼尾、眉毛及补画底稿。检查工作组时隐藏参考层。导出使用临时文件、ZIP CRC 检查及实际序列化图层合成验证，再原子替换工程。

后续：侧后发与丝带旁发束，结合完整头发复查耳侧与根部边界，再进入其余眼口、正坐姿和绑定。此工程尚未接入 `/inochi2d-test/smoke`。
