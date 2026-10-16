# MewNook v4：正坐姿 Inochi2D 完整目录结构

**当前阶段：脚手架。** v4 将使用 1122 × 1402 的正坐姿透明白发猫娘原画，与原先的歪头 v3 模型彻底分离。

```text
assets/inochi/v4/
  manifest.json                    # 资产定义、状态和原图画布
  source/                          # pose_reference.png 和多层 master.ora（待制作）
  parts/head/
  parts/eyes/
  parts/mouth/
  parts/hair/
  parts/ears/
  parts/body/
  parts/arms/
  parts/legs/
  parts/tail/
  parts/chair/
  expressions/                     # neutral / chat / sleepy...
  motions/                         # idle / touch / chat / focus / rest...
  rig/                             # Inochi Creator .inp（待制作）
  validation/                      # 视觉回归验收
public/inochi2d/v4/                # 仅导出模型，待制作
docs/INOCHI_V4_STRUCTURE.md
scripts/check-inochi-v4-layout.mjs
```

**工作区和发布区分开：** assets/inochi/v4/ 存放母版、手工补画部件和 Inochi Creator 工程，public/inochi2d/v4/ 仅存最终经过验收的导出 .inx。为使 Git 跟踪空目录，目前各目录加入 README；目录里还没有真正图层。

**制作顺序：** 上传 pose_reference.png → 清理白边和杂点 → 绘制正坐姿 master.ora 多层源图 → 逐层补画并导出 parts → 建立原生 Inochi Creator 网格和参数 → 导出 .inp/.inx → 真实 WebGL2 表情及动作截图验收 → 才更换主应用测试模型。

**画布与材质：** 全部分层采用相同的 1122 × 1402 左上角为原点的画布；left/right 以屏幕左右为准；可编辑源 PNG 使用 straight-alpha sRGB，发布 Inox2D 纹理时才预乘 Alpha，避免白块和双重预乘。

**动作优先级：** idle、blink、mouth A/B、touch_ear、sleepy，之后 focus/rest 和身体摆动。不能拿旧 v3 的斜头位置套新正坐姿脸；也不能只凭像素发生变化就宣称自然。

**不能误读的状态：** 本提交不会改动现有 React 模型路径；没有创建 v4 .ora、.inp 或 .inx；新正坐姿 PNG 还未提交进仓库。manifest 中 required_parts 是待交付清单，不是实际文件清单。

**检查命令：** node scripts/check-inochi-v4-layout.mjs，仅校验约定中的目录和 JSON，不验证尚未存在的素材质量。

## v4 Motion engineering prototype

Added `scripts/upgrade-mewnook-v4.py`, which extends the upright `build-mewnook-v4.py` INX with 5 genuine native `deform` ArtMesh regions: left/right ears, left/right outer hair and tail. Adds 10 new scalar controls (ear/hair/tail, ear tilt, each sleepy eye and breathing), for **16 total parts and 14 total parameters**. Each deform is a grid, not an entire rectangle being translated.

Reproduce after adding the **real** `source/pose_reference.png`:

```bash
python scripts/build-mewnook-v4.py --output /tmp/MewNook-v4-base.inx
python scripts/upgrade-mewnook-v4.py --source assets/inochi/v4/source/pose_reference.png --input /tmp/MewNook-v4-base.inx --output assets/inochi/v4/rig/MewNook-v4-motion.inx
python scripts/check-mewnook-v4-motion.py assets/inochi/v4/rig/MewNook-v4-motion.inx
```

CI executes the same generator using the real image when present, or an explicitly labeled synthetic fixture while the actual image is absent. **Synthetic-fixture CI cannot establish visual quality or production readiness.** The editor `.inp` and painted hidden areas remain to be made. Current live UI stays v3/PNG.

## 正坐姿母版已入库、独立 v4 测试入口

已将 1122 × 1402 的正坐姿透明立绘 **原始 PNG** 放入 `assets/inochi/v4/source/pose_reference.png`，SHA-256 为 `5c47238062e6b7f99e95c14658d3af87f1a147ada44173375c90a1cf0f479231`。GitHub Actions 在真实原图上生成 v4 工程模型、严格验证预乘 Alpha 和 5 组原生网格变形，并通过 `?model=v4&probe=1` 运行 Chromium 实际截图测试。测试结果保存在 Actions 的 `inochi-v4-candidate` 附件。

**未通过视觉审查以前，v4 只在独立页面 `inochi2d-test/smoke.html?model=v4` 中使用，MewNook 主场景继续 v3/PNG。** 这不是完成的手工 Inochi Creator `.inp` 工程；重新绘制遮挡区域、提高眼睑与口型的观感仍是待办。
