# 恢复原脸缘与侧发衔接

上一版对整张新脸做凸包和横向轮廓映射，又更改连接发片层级，使两侧脸颊/侧发交界被重塑。这些更改已移除。

本版直接使用 scene-source-v1 的原脸/原颈部部件。仅在固定底稿的原眼睛范围使用已补画的无眼研究稿，填满原眼部孔洞。此固定底稿不随眨眼替换。眼部区域之外的 RGBA 必须与原素材逐像素相同；两侧用户标记的脸缘区域也作完整像素检查。原发片文件及层级恢复，前发裁片不再使用上一版的修剪版本。

- face-and-neck.png：保留原脸缘与原下巴/颈部的固定底稿。
- fixed-eye-underpaint-mask.png：固定眼部补画范围。
- filled-eye-hole-mask.png：原眼部透明孔洞的填充位置。
- MewNook-native-contour-face.ora：可编辑底稿工程。
- manifest.json：像素一致性、孔洞数量及哈希。

眼球与眼睑仍独立。上眼睑皮肤材质需不透明，避免原脸孔洞的 alpha 被带进移动眼睑造成虹膜漏出；外侧脸缘不由此材质重建。新的真实 WebGL 检查验证完整闭眼时虹膜蓝色漏出像素为 0，并检查开合、头发摆动和转头结束均完整复位。

重建：python scripts/register-v4-fixed-face.py，然后 python scripts/build-mewnook-v4-source-rig.py。新版独立测试页缓存标记为 source-art-20261023-native-contour。实际新旧脸颊对比在 validation/fixed-face/both-cheeks-review.png；视觉验收仍待用户确认，正式页模型未替换。
