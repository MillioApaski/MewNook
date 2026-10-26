# 内置 image_gen 提示词与输入

工具：内置 image_gen，透明素材启用 transparent_background；原始生成结果完整保留于 inputs。

## 工作与阅读身体（两次独立编辑）

参考：body-extended-reference.png。保持头部以外的原画胸口、蝴蝶结、奶白外套、肤色、细线与淡紫阴影；严格保留肩颈位置，不增加头部、脸、耳朵、背景或桌子。画布参考为 481×650，原手在 y480 以下的空白区伸向虚拟桌面，双手位于 y540–570，恰好两只手、正常五指。消除原来膝上握拳的双手。

打字：左右手在 x130/x335、y540/y545，放在 x75–410、y550–605 的淡紫色无字无标识小键盘上，手指自然按键。

阅读：前臂放在桌上，双手握住 x80–415、y465–605 的展开书本两侧下缘；奶白纸页、淡紫/藏青封皮、无可读文字。不要托腮，不让手靠近脸。

## 旧手部下的固定身体（一次编辑）

参考：scene-source-v1/part-19.png。仅删除底部中央的两只膝上双手及手腕开口，补为连续奶白外套织物和自然褶皱；保留领口、胸前蓝蝴蝶结、肩袖、发丝片段、裙子及外轮廓。无手、无新肢体、无背景，透明输出。

## 专注桌面（四次独立编辑，day/rain/sunset/night）

参考：对应场景的 background.webp（day）或 foreground.webp。仅删除桌面左半边的大粉色机械键盘和键盘投影，补齐平坦粉紫桌垫与木纹，匹配对应场景的光照和透视。保留鼠标、鼠标投影、桌垫边缘与爪印、笔记本、杯子、植物、书本、前景树叶、桌后边缘及构图，不增加物体和文字。严格保留原透明区。使用原画布比例输出。最终导出器只取 manifest 中的键盘区域，保留原桌面 alpha 覆盖范围。


## 2026-10-27：桌后腰部衣料补画
内置 image_gen，编辑输入 inputs/reading-painted.png，透明背景。输出 inputs/torso-fill-painted-v2.png。

Use case: precise-object-edit. Edit target: attached transparent anime torso sprite, a headless catgirl wearing ivory cardigan, white shirt and navy bow, arms resting on an open book. This is a production layer repair, preserve exact canvas framing, all existing pixels/shapes of shoulders, sleeves, hands, open book, bow and upper chest as closely as possible. ONLY fill the transparent HOLE between the two forearms, below the flat-cut central cardigan hem and above the open book, with a natural continuous extension of the same cardigan and shirt front. The chest cardigan must continue down behind the book to the waist, with natural ivory folds and center shirt, NO crossed arms, NO extra cuffs, NO new hands. The fabric continues behind the existing outstretched sleeves; the hole must become fully opaque clothing. Keep transparent background outside silhouette and do not fill transparency outside arms/book. Same clean soft pastel anime line art, same position and proportions. Do not add a head, desk, background, text or accessories.
