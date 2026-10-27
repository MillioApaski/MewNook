# 专注姿态分层素材

保留现有原画头部、眼睑和眉嘴，新增打字与看书两套肩部以下的专注素材。绘画由内置 image_gen 完成；原始生成输入保存在 inputs，提示词记录见 PROMPTS.md。

- `typing/reading-body.png`：身体层，位于桌面后。原肩颈、领口和上半段胸前素材逐像素保留；沿用同一工作姿势的衣服，中央腰部透明空洞由 torso-fill-painted-v2 补齐；不复用原坐姿袖子。
- `typing/reading-hands.png`：前臂、双手与键盘/书本，位于桌面前。源坐标与身体共用 1122×1402 画布，从 y=695 起沿手臂内侧轮廓分层，去除中央衣服；头部由 focus-head-v2 的独立俯视素材切换。
- `typing/reading-focus.ora`：可编辑 OpenRaster 身体与前景双层工程。
- `inputs/*-desk-painted.png`：四场景清理旧键盘的研究稿；仅导出明确的桌面局部，其他场景像素不用生成图替换。输出 `public/inochi2d/v4/focus-desk-*.png`。
- `manifest.json`：分层坐标、原肩颈一致性及输出哈希。

生成：`python scripts/prepare-v4-focus-source.py`。再运行 `build-mewnook-v4-source-rig.py` 与 `--foreground`，分别导出身体模型和前景手部模型。正式与测试页继续共用同一身体模型。

主界面遮挡顺序为手部模型 → 桌面 → 人物身体 → 背景。手部模型在首次专注时加载，暂停后停止绘制；聊天和摸头不取消专注姿态。手机画布在桌面前延伸，保持与身体相同的源坐标，避免手部被原身体画布底部裁掉。

验证：check-focus-working.mjs 覆盖四场景与手机、真实计时按钮、阅读/打字切换、前景遮挡像素、暂停、离线缓存和加载失败回退。新姿态的视觉效果待体验后确认。

2026-10-27 修正：inputs/torso-fill-painted-v2.png 由内置 image_gen 编辑阅读研究稿得到。只取中央缺失的腰部衣料，保留原肩颈与手臂；防止椅背从两臂之间穿出。原生参数 ParamWorkLookDown 绑定头部俯视和眼球下视，专注结束返回 0。

俯视修正：ParamWorkLookDown 已改为切换独立绘画，不再缩放头部或挤压眼球；新头部源图和提示词在 ../focus-head-v2。
