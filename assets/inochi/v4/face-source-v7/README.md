# 原微笑、完整口腔与左右眉毛

运行 `scripts/prepare-v4-mouth-brows.py` 重建。使用原画微笑、原眉毛和完整 `expression-talking.png` 补画；不使用先前被裁掉下缘的口腔片段。

口腔按实际像素分为上下唇、内腔、舌面和高光，互斥材质重组与完整提取图一致。九级口型覆盖同一皮肤插槽，避免在旧微笑上再叠一张嘴。眉毛独立保留原画的前景顺序，不把眉线带进刘海。

`expression-source-check.png` 展示组合源图；实际 WebGL2 的眨眼/聊天/困倦/摸头与复位证据见 `validation/source-runtime`。

AI 辅助生成与维护：GPT-6 Sol。
