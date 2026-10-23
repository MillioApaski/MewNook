# v4 修复清单

本轮修复已接入独立测试页 `/inochi2d-test/smoke`，默认 v4。最新实验模型为 `MewNook-v4-review.inx?rig=source-art-20261020`。同一模型现已接入正式房间，运行资源为 `/inochi2d/v4/MewNook.inx`。

- [x] 1. 修复前发断线、黑边和重复眉毛。
- [x] 2. 拆分前发、侧发、后发、发卡、呆毛、丝带及细发组，补齐当前动作范围的隐藏搭接，复核耳根、胸前、裙边遮挡。
- [x] 3. 精修眼白和原虹膜遮罩，清除固定眼白上的旧虹膜残影。
- [x] 4. 使用原画睫毛和完整闭眼补画生成九级眼睑开合，保留圆形虹膜，由眼睑遮挡。
- [x] 5. 拆分左右原画眉毛，独立绑定；面部底稿不再保留重复眉毛。
- [x] 6. 使用完整口腔补画，拆分上下唇、内腔、舌面及高光，生成九级连续口型；恢复下缘。
- [x] 7. 完成双膝靠拢、双腿不交叉的坐姿；拆出躯干、衣服、手、静态左右腿、椅子与原猫尾。
- [x] 8. 完成 58 个运行时部件、头部父子关系和网格绑定；头部、前发、侧后发、耳朵、尾巴、眉毛、呼吸在实际 WebGL2 中验证。
- [x] 9. 聊天驱动单个口型参数，困倦复用同一眼睑参数，不再叠一套眼皮或嘴。
- [x] 10. 摸头联动头部转动/轻抬、头发、猫耳、眼睑与眉毛。
- [x] 11. 验证四种动作、动作结束、连续切换和复位后，再接入独立测试页；修复开发和预览环境的无扩展名路由。

## 验证证据

- `assets/inochi/v4/validation/source-runtime/report.json`：实际 Chromium/WebGL2，13 个动作参数的画面变化；左右眼和嘴的 17 个中间位置；四个动作复位差异均为 0，连续切换后的复位差异为 0；无页面错误。
- `assets/inochi/v4/validation/standalone-runtime-report.json`：生产构建的规范路由、默认 v4、按钮触发、局部变化和动作结束/手动复位检查。
- `tests/inochiActions.test.mjs`、`tests/parameterOpacity.test.mjs`：时间线、单一眼睑/口型控制及透明度兼容层。全项目 17 项单元测试通过。
- `npm run prepare:inochi`：原上游运行时完整性校验通过；兼容层独立放在 `inochi_source_bridge.js`，不会被资源准备脚本覆盖。
- `npm run build`：类型检查和生产构建通过。

## 源工程与复现

| 工程 | 内容 |
| --- | --- |
| `face-source-v6/MewNook-v4-blink-source.ora` | 原睫毛、闭眼补画及眼睑关键帧 |
| `face-source-v7/MewNook-v4-mouth-brows-source.ora` | 完整口腔材质、原微笑和左右眉毛 |
| `scene-source-v1/MewNook-v4-upright-assembly.ora` | 33 个可编辑原画部件及正坐姿整身组合 |

先安装 Pillow、NumPy、OpenCV；若需重建源工程，依次执行 `prepare-v4-blink-source.py`、`prepare-v4-mouth-brows.py`、`prepare-v4-upright-scene.py`。普通构建只需 `python scripts/build-mewnook-v4-source-rig.py`，从入库 PNG/manifest 生成模型，不调用生成服务。

源坐标保持 1122×1402；可见原画部件来自原立绘，补画用于被遮挡区域、表情与新坐姿。当前小幅动作已检查，左右腿为静态坐姿层。本轮不包含大幅转头、手臂新动作或 Inochi Creator 原生工程；OpenRaster 与 PNG 保留可编辑源素材。视觉观感仍以测试页供用户审阅为准。

## 正式页面接入

- 默认使用已验收的新模型，旧安装只迁移一次，随后保留用户选择。
- 正式房间复用独立测试页的原画动作时间线和透明度适配器。
- 角色按可见容器适配大小；手机端居中取景。
- `scripts/check-room-source.mjs` 验证首次默认、旧设置迁移、聊天闭嘴、摸头/复位、夜间眼睑、关闭后刷新、重新启用及静态回退，并保存四种场景和小屏截图。

困倦确认稿已于 2026-10-22 接入：新增原口腔材质整理的微小开口部件与 ParamDrowsyMouth，现为 58 部件、25 参数；源工程见 sleepy-source-v1。

闭眼肤色接缝修正：运行时九级眼睑使用 `face-source-v8`，保留原画睫毛并修正眼周皮肤衔接。`scripts/prepare-v4-blink-source.py` 现在导出此版本；v6 留作原画工作检查点，口型工程仍保留原素材引用。
