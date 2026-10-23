# 恢复原脸缘与侧发衔接

上一版对整张新脸做凸包和横向轮廓映射，又更改连接发片层级，使两侧脸颊/侧发交界被重塑。这些更改已移除。

本版直接使用 scene-source-v1 的原脸/原颈部部件。仅在固定底稿的原眼睛范围使用已补画的无眼研究稿，填满原眼部孔洞。此固定底稿不随眨眼替换。眼部区域之外的 RGBA 必须与原素材逐像素相同；两侧用户标记的脸缘区域也作完整像素检查。原发片文件及层级恢复，前发裁片不再使用上一版的修剪版本。

- face-and-neck.png：保留原脸缘与原下巴/颈部的固定底稿。
- fixed-eye-underpaint-mask.png：固定眼部补画范围。
- filled-eye-hole-mask.png：原眼部透明孔洞的填充位置。
- MewNook-native-contour-face.ora：可编辑底稿工程。
- manifest.json：像素一致性、孔洞数量及哈希。

眼球与眼睑仍独立。固定底稿在限定眼部补画范围填满眼睛开口、原睫毛及高光裁切孔洞，避免独立睫毛移开后露出后方旧眼线。眼睑网格逐列锚定原眼睛开口，从开口边缘展开至闭眼曲线；不再使用延伸至脸颊/发丝的矩形皮肤。UV 仅采样开口内固定皮肤。眼球 alpha 收在开口内部，并留一个源像素的采样余量，防止双线性过滤产生蓝色细边。外侧脸缘、发片及层级保持原样。

真实 WebGL 检查验证四档开合中左外眼角下方脸缘变化为 0；完整闭眼时另加载隐藏眼球的模型，与正常闭眼截图全画布比较，眼球可见贡献为 0；开合、摆发、转头后完整复位。检查截图和报告在 validation/fixed-face，corner-aperture-review.png 为实际渲染的新旧局部对照。

重建：python scripts/register-v4-fixed-face.py，然后 python scripts/build-mewnook-v4-source-rig.py。新版独立测试页缓存标记为 source-art-20261023-aperture-lids。实际新旧脸颊对比在 validation/fixed-face/both-cheeks-review.png；视觉验收仍待用户确认，正式页模型未替换。
