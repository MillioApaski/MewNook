# MewNook 🐾

**A cozy, local-first anime companion workspace.** 和小猫一起专注、听雨、整理日程。

MewNook 是一个可安装的 PWA，目标是在浏览器中提供沉浸式陪伴工作空间。当前版本是可交互的第一阶段原型，**没有账户、没有强制 AI 服务，也不需要付费后端**。

## 已实现（第一阶段）

- 🌱 番茄钟：专注、短休息、长休息、自定义时长、暂停、继续、刷新后恢复、会话记录。
- 📋 日程与任务：按天查看、创建、完成、删除、关联当前专注任务、重要标记。
- 📊 统计：当天专注时长、七日柱状图、历史专注记录。
- 🐈 猫娘原型：根据专注/休息/夜晚切换表情与姿势的 **原创 SVG 占位角色**。
- 🌦️ 虚拟房间：随浏览器当地时间自动切换昼夜，并按 Open-Meteo 天气模拟雨景；支持手动切换。
- 🎧 声音：浏览器本地合成雨声、风声、柔和底噪，可以分别调整音量；选择本地音频播放。
- 💬 AI：没配置时使用离线预设台词；支持 OpenAI 兼容 API Base URL + Model + 用户自带 Key (BYOK)。
- 💾 本地保存、导入/导出 JSON 备份，PWA 安装及 Cloudflare Workers Static Assets 配置。

**角色图片说明：** 之前生成的六格图片是带场景的预览图，不适合直接叠加。现阶段使用 SVG 角色占位，待六张统一且透明背景的立绘制作完成后替换。尚未接入 Live2D。

## 本地开发

需要 Node.js 22+。

```bash
npm install
npm run dev
```

本地打开 Vite 输出的地址。生产构建：

```bash
npm run build
npm run preview
```

## Cloudflare Workers 部署

无需 AI Gateway、D1 或 R2。前端通过 Workers Static Assets 提供服务。

```bash
npm install
npx wrangler login
npm run deploy
```

或者在 Cloudflare 的 Workers 项目中连接此 GitHub 仓库，设置构建命令 `npm run build` 和输出目录 `dist`（以 Cloudflare 当前的 Git 集成界面为准）。部署脚本和 Worker 静态资源设置见 `wrangler.jsonc`。

> Cloudflare 账户、GitHub 自动部署授权和自定义域名必须由仓库所有者配置；仓库提交本身不等于线上已经部署。

## AI 配置及安全

进入 **设置 → 自定义 AI API**：

- Base URL：如 `https://api.example.com/v1`
- 模型：服务商给出的实际模型 ID
- API Key：仅保存到浏览器 `sessionStorage`，不进入备份、D1、Worker Secrets 或 Git 仓库

浏览器直接调用用户填写的 API，**服务商必须允许浏览器跨域 (CORS)**；目前不提供代理。限制为 HTTPS URL，仅允许回环地址使用 HTTP。请勿填写不可信的 API 域名。打开开发者工具或安装恶意扩展仍有机会泄漏前端密钥，敏感 Key 最好创建权限和额度受限的专用凭据。

对话默认本地保存在 `localStorage`，在聊天中避免输入不希望长期留在浏览器的数据。API 服务商会收到本次调用的聊天内容。

## 数据、媒体与限制

- 任务、设置、统计、对话历史：浏览器本地 `localStorage`；不会跨设备同步，清理网站数据可能造成丢失。
- 音乐文件：用户通过文件选择器在当前会话播放，不上传云端，也不会在刷新后自动重新打开。
- 环境音：由 Web Audio API 在本地实时合成，属于原型音效，不是授权音轨。
- 天气：使用 [Open-Meteo](https://open-meteo.com/)，需遵守其非商业使用及署名条件。
- 番茄钟：基于绝对时间计算，减少后台节流引起的误差；**浏览器关闭后不会持续发送系统通知**。
- PWA：具备静态离线缓存，但 AI 与实时天气必须联网。桌面悬浮窗需要后续独立桌面应用。
- 尚无账户、D1 云同步、第三方在线音乐接入、语音 TTS、正式立绘资产和 Live2D。

计划请见 [docs/ROADMAP.md](docs/ROADMAP.md)。

## AI 生成声明

本项目代码与文档主要由 OpenAI ChatGPT 辅助生成与维护，**本次使用模型为 GPT-6 Sol**。请在公开部署前审查代码、依赖及素材授权。
