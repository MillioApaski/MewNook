# 正式房间角色资源

`MewNook.inx` 与已验收的原画拆层实验模型一致，由 `scripts/build-mewnook-v4-source-rig.py` 生成。正式页面默认启用此模型，旧安装首次升级时迁移到新版本；之后保留用户的关闭、缩放及模型选择。

运行库复用 `/inochi2d-test/runtime/inochi_source_bridge.js`，动作复用同一套原画参数控制。运行资源失败后依次回退旧模型及静态立绘。可编辑 PNG/OpenRaster 源工程位于仓库 `assets/inochi/v4`，不发布至 public。

当前资源版本：`source-art-20261024-headpat`。固定脸底与开口内独立眼睑来自已合并修复，增加触摸专用 `ParamHeadPat` 绑定。正式与测试模型字节一致；摸头、聊天和困倦共用动作模块与复位逻辑。

专注版本：`source-art-20261028-focus-head`。身体模型增加阅读/打字背层；`MewNook-hands.inx` 为桌面前方的独立手部模型，首次专注时加载。四场景的 `focus-desk-*.png` 仅清理旧键盘局部。身体模型继续与测试页字节一致，输入与 ORA 工程见 focus-source-v1。

修正：前景仅含沿轮廓分离的前臂/手/道具，中央衣服留在桌后；身体不再混入原坐姿袖子。新增 ParamWorkLookDown：头部向下俯转、虹膜向下、眼睑收窄；暂停复位，专注时聊天不取消下视。

2026-10-28：撤掉整头纵向压缩和虹膜形变，改用 focus-head-v2 的独立俯视绘画，保留头脸比例；专注头部的眼睑、说话补画独立，只用可见性包络切换新旧头部。
