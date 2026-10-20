# 原画呆毛与发冠根部局部工程

当前模型：GPT-6 Sol。

原画来源：`../source/pose_reference.png`。本目录只处理原画呆毛与其根部隐藏区，不代表完整发冠、头发或模型完成。

- `ahoge-source-candidate.png`：原画 RGB，沿原轮廓选区分离，偏移 `(420,6)`。705 个不透明核心像素保持原样。剔除了曾误选的发冠斜轮廓线。
- `inputs/crown-underpaint-generated.png`：使用内置 imagegen 对原图局部去呆毛、补出根部遮挡的发冠。提示要求只移除环形呆毛与茎部，维持猫耳、发冠、原画笔触和透明背景。生成结果改变了部分发冠线条，因此只消费窄小根部区域，不采用整张生成图。
- `registered-crown-underpaint.png`：对保留部分配准，15 个空间分散内点 / 127 对匹配，中位误差 0.208 原图像素、P95 0.290。支持范围跨原画耳部与下方头发；只能支撑局部补画用途。
- `crown-without-ahoge.png`：保留原图其他部分，局部清除旧呆毛、混合根部隐藏区。发现根部右侧深色短接缝后，恢复该处原本可见的发冠边缘。所有插值与混合采用预乘透明度。
- `ahoge-motion-check.png`：根部锚定，向顶部递增的 -6 / 0 / +6 像素检查。另有五个全尺寸位移图。它们是静态源图位移检查，尚非网格绑定或运行时动作。
- `MewNook-v4-ahoge-source.ora`：默认原画参考；隐藏 `AHOGE STATIC CHECK — full crown incomplete` 工作组包含独立原画呆毛及局部补画底图。查看工作组时隐藏原画参考。写入后检查 ZIP CRC、参考像素与实际序列化工作组的合成结果。

运行 `python3 scripts/separate-v4-ahoge.py` 可重建。待完成完整发冠与耳侧轮廓、四片前发联合遮挡、侧后发及真正的模型绑定。测试页未接入此素材。
