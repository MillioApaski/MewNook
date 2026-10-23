> 已弃用：本版整脸轮廓映射扩大了两侧错位。当前构建使用 v3 的原脸边界保留方案；本目录仅留作历史参考。

# 原脸轮廓注册与侧发交界

新皮肤底稿与原脸轮廓不一致，直接替换使原脸范围有 2,141 个原本不透明的像素未被覆盖，左眼外侧露出底层，成为斜边和缺口。不能靠模糊纹理修补。

`register-v4-fixed-face.py` 将整张干净皮肤材质按原脸轮廓逐行注册。原脸为拆件时挖掉细发丝的形状，先恢复连续的皮肤承托面，眼部孔洞也由固定底图填满；在头发下方加四像素重叠。注册时取干净底稿的内部皮肤，避免把生成图的外轮廓线留在新轮廓内部；鼻子、嘴部仍来自同一皮肤材质，未做模糊滤镜。下巴到原颈部保留既有静态过渡，y>=350 的原颈部字节不变。

另清掉左前发顶部夹带的 35 个旧脸颊色像素，保留其余头发 RGB。左右连接发片明确放到眼睛和脸的前方。

- `face-and-neck.png`：运行时单张固定脸底。
- `registered-skin.png`：注册后的皮肤层。
- `native-face-alpha.png`：原脸覆盖范围。
- `hidden-hair-underlap.png`：头发下的重叠范围。
- `left-chest-lock.png`：去除旧脸颊色残留的前发。
- `MewNook-registered-face.ora`：可编辑皮肤与原颈部分层工程。
- `manifest.json`：覆盖范围和哈希。

重建：先执行 `python scripts/register-v4-fixed-face.py`，再执行 `python scripts/build-mewnook-v4-source-rig.py`。眼睑与脸部使用同一注册皮肤来源。`check-v4-fixed-face.mjs` 覆盖开合、困倦小口、头发摆动与复位；新旧左眼局部截图在 `validation/fixed-face/left-eye-seam-review.png`。仍需用户视觉验收，正式页模型未替换。
