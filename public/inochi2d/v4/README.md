# 正式房间角色资源

`MewNook.inx` 与已验收的原画拆层实验模型一致，由 `scripts/build-mewnook-v4-source-rig.py` 生成。正式页面默认启用此模型，旧安装首次升级时迁移到新版本；之后保留用户的关闭、缩放及模型选择。

运行库复用 `/inochi2d-test/runtime/inochi_source_bridge.js`，动作复用同一套原画参数控制。运行资源失败后依次回退旧模型及静态立绘。可编辑 PNG/OpenRaster 源工程位于仓库 `assets/inochi/v4`，不发布至 public。
