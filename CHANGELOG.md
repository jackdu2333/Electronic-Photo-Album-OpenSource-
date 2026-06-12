# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.1.0] - 2026-06-02

### Security

- 🔒 **修复 SSL 证书验证**：`_fetch_json()` 和天气 API 生产环境恢复默认证书链，消除 MITM 风险
- 🔒 **修复 XSS 漏洞**：前端日期叠加层和文件预览从 `innerHTML` 改为 `textContent` + DOM API
- 🔒 **修复模板注入**：`CURRENT_USER` 使用 `|tojson` 过滤器替代字符串拼接
- 🔒 **修复时序攻击**：明文密码回退使用 `hmac.compare_digest` 常量时间比较
- 🔒 **修复存储型 XSS**：留言 sender/content 入库前 `html.escape()` 转义
- 🔒 **SECRET_KEY 安全**：docker-compose 移除不安全默认值，缺少时启动失败

### Performance

- ⚡ **推荐算法优化**：单次推荐从最多 3 次全量 DB 查询降至 1 次
- ⚡ **元数据缓存**：`_merge_note_fields` 添加 mtime 检查，文件未变时跳过 JSON 解析
- ⚡ **图片压缩优化**：移除 `smart_compress` 重复 resize，节省峰值内存
- ⚡ **事务保护**：深海打捞 SELECT + UPDATE 包在 `BEGIN IMMEDIATE` 事务内

### Architecture

- 🏗️ **线程安全**：`PhotoMetadataService._metadata` 添加 RLock 保护并发读写
- 🏗️ **双写一致性**：`add_photo()` 改为先写 DB 再写内存，避免不一致
- 🏗️ **异常精确化**：Migration 异常从 `except Exception` 改为 `sqlite3.OperationalError`
- 🏗️ **公开 API**：`_getexif()` 替换为 Pillow 公开 `getexif()`

### Frontend

- 🎨 **定时器清理**：所有 `setInterval` 返回值存入变量，支持后续清除
- 🎨 **消息轮询退避**：留言轮询改为指数退避（30s → 300s），减少网络异常时带宽浪费
- 🎨 **命名空间保护**：Android TV 函数改为 `window.PhotoFrame.*`，保留向后兼容
- 🎨 **冗余代码清理**：移除重复 MutationObserver 和无意义条件分支
- 🎨 **图片加载兜底**：前景图添加 `onerror`，加载失败 3 秒后跳下一张
- 🎨 **语言属性修正**：`lang="en"` → `lang="zh-CN"`

### Deployment

- 🐳 **新增 .dockerignore**：排除 .git/.env/__pycache__/tests，减少镜像体积
- 🐳 **Gunicorn 可配置化**：workers/threads/timeout 支持环境变量覆盖
- 🐳 **Compose V2**：移除过时 `version: '3.8'` 声明
- 🐳 **SHA256**：锁文件名哈希从 SHA1 升级为 SHA256

### Fixed

- 🐛 排序 key 混合类型：`images` API 使用 `(date or '0000-00-00', url)` 元组排序
- 🐛 DB timeout 逻辑：`max()` 改为直接使用传入值

---

## [2.0.1] - 2026-03-23

### Added

- ✨ 新增统一样式菜单，整合 `style7` 到 `style16` 的独立主题入口
- ✨ 新增策展类视图：瀑布流、全景卷轴、拍立得墙、艺术画廊
- ✨ 新增照片便签字段 `note_title` / `note_body` 的 API 与前端展示
- ✨ 新增每日一言多源回退接口
- ✨ 新增拍立得墙便签编辑的自动保存与手动保存双通道

### Changed

- 🔄 样式菜单改为分组排序、自动隐藏、连续展示编号
- 🔄 style16 艺术画廊优先显示便签标题与正文，并优化信息层级
- 🔄 多图样式改为分批/按需加载，适配大相册与大屏持续展示
- 🔄 拍立得墙默认便签改为温度型内置文案池

### Fixed

- 🐛 修复多个样式缺失拍摄时间、便签字段与“记忆打捞”提示的问题
- 🐛 修复 style15 便签编辑缺失 CSRF、保存栏偶发消失、预览图空白的问题
- 🐛 修复 style16 标签重复显示的问题
- 🐛 修复部分主题切换、切图按钮与菜单互通体验不一致的问题

---

## [2.0.0] - 2026-03-20

### Added

**UI/UX 升级**：
- ✨ **多主题 UI 系统**: 新增 6 套主题风格
  - `style-1`: 经典分栏布局（稳定、通用）
  - `style-2`: 沉浸全屏相框风（默认）
  - `style-3`: 画廊展签风（审美展示）
  - `style-4`: Floating Glass 浮空玻璃卡片
  - `style-5`: Edge accent 边缘风格
  - `style-6`: Poster 海报风格
- ✨ **环境色自适应主题**: 从照片提取主色调动态应用到 UI 面板
- ✨ **隐藏式样式切换器**: 左上角 hotspot 触发，选择保存至 localStorage
- ✨ **登录页重设计**: 产品感入口页面，桌面端/移动端视觉提升

**核心功能**：
- ✨ **智能推荐算法 V2.0**: 双轨制分发
- ✨ **宝宝年龄计算**: 自动计算拍照时的年龄
- ✨ **照片预加载机制**: 提前 1.5 秒预加载下一张
- ✨ **强制展示模式**: 支持单张照片 10 分钟优先展示

**认证与安全**：
- ✨ **密码 PBKDF2-SHA256 哈希加密**
- ✨ **登录失败锁定**: 5 次失败锁定 5 分钟
- ✨ **Session 管理**: 24 小时自动过期
- ✨ **密码强度验证**

**部署与运维**：
- ✨ **宝塔面板部署指南**: 新增 `docs/Baota-deployment.md`
- ✨ **SQLite busy timeout 可配置**
- ✨ **天气 API SSL 验证修复**

**文档**：
- 📄 新增 `docs/auth.md` 认证配置说明
- 📄 新增 `docs/Baota-deployment.md` 宝塔部署指南

### Changed

**优化**：
- 🔄 留言区滚动定位逻辑：只在接近底部时自动吸附
- 🔄 样式二横图展示：增加左侧安全边距
- 🔄 低亮度场景优化：提高暗部对比度，强化文字可读性
- 🔄 移动端适配：横屏/竖屏独立优化规则

**架构改进**：
- 🔄 推荐算法配置化
- 🔄 压缩参数可配置
- 🔄 幻灯片时长可配置
- 🔄 深海打捞参数化

### Fixed

**UI 修复**：
- 🐛 样式二信息面板圆角/越界问题
- 🐛 样式二横图被左侧信息区遮挡
- 🐛 留言栏无法上下滑动
- 🐛 左侧信息区留白过大

**核心修复**：
- 🐛 静态资源认证问题：`/static/photos/` 路径白名单
- 🐛 前端配置注入
- 🐛 天气坐标暴露
- 🐛 深海打捞 CSS 缺失

### Removed

**Breaking Changes**：
- ⚠️ 移除硬编码的宝宝名，需通过 `BABY_NAME` 配置
- ⚠️ 移除硬编码的苏州天气坐标，需通过 `WEATHER_LAT/LON` 配置

---

### Migration Guide

从 v1.x 升级到 v2.0：

1. **备份数据**（重要！）
   ```bash
   cp photos.db photos.db.backup
   cp photo_metadata.json photo_metadata.json.backup
   cp messages.json messages.json.backup
   cp -r static/photos static/photos.backup
   ```

2. **更新代码**
   ```bash
   git pull
   ```

3. **安装新依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **更新环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env，确保新增以下变量：
   # - SQLITE_BUSY_TIMEOUT_MS=10000
   # - SLIDE_DURATION_SECONDS=300
   # - DEEP_SEA_PROBABILITY=0.05
   ```

5. **重启服务**
   ```bash
   # Docker
   docker-compose restart

   # 宝塔/本地
   systemctl restart photo_frame
   ```

**注意事项**：
- ⚠️ 不要覆盖 `.env` 文件中的密码配置
- ⚠️ 不要覆盖 `photos.db` 等数据文件
- ⚠️ 首次启动会自动升级数据库结构

---

## [1.6.0] - 2026-02-06

### Added
- ✨ 宝宝年龄显示功能
- ✨ 深海打捞彩蛋功能（老照片随机展示）
- ✨ 多用户个性化问候语

### Changed
- 🔄 优化前端照片推荐算法至 V2.0（双轨制分发）
- 🔄 引入 SQLite 进行照片元数据持久化

---

## [1.5.0] - 2026-02-05

### Added
- ✨ 照片管理页面智能搜索功能
- ✨ Android App 图标更新

### Changed
- 🔄 优化前端照片排序逻辑

---

## [1.0.0] - 2025-xx-xx

### Added
- 🎉 初始版本发布
- ✨ 基础照片幻灯片展示
- ✨ 留言板功能
- ✨ 后台管理功能
- ✨ Android 客户端

---

## Version History

| Version | Release Date | Key Features |
|---------|--------------|--------------|
| 2.0.0   | 2026-03-20   | 多主题 UI、环境色自适应、认证升级、宝塔部署 |
| 2.0.0   | 2026-03-16   | 配置模块化、Docker 部署、文档完善 |
| 1.6.0   | 2026-02-06   | 宝宝年龄、深海打捞 |
| 1.5.0   | 2026-02-05   | 智能搜索、新图标 |
| 1.0.0   | 2025-xx-xx   | 初始发布 |

---

## Upcoming Features

### v2.1.0 (计划中)
- [ ] 照片标签管理界面
- [ ] 批量操作功能
- [ ] 照片时间线视图
- [ ] 多租户支持
- [ ] 云存储集成（S3/OSS）
- [ ] 数据库迁移管理（Alembic）

### v2.2.0 (计划中)
- [ ] 主题编辑器
- [ ] 导出/分享功能
- [ ] 国际化（i18n）
- [ ] 插件系统

### v3.0.0 (长期计划)
- [ ] PostgreSQL 支持
- [ ] 分布式部署
- [ ] AI 智能标签
- [ ] 官方文档站点
- [ ] Android/iOS 应用上架

---

[2.0.0]: https://github.com/YOUR_USERNAME/digital-photo-frame/releases/tag/v2.0.0
[1.6.0]: https://github.com/YOUR_USERNAME/digital-photo-frame/releases/tag/v1.6.0
[1.5.0]: https://github.com/YOUR_USERNAME/digital-photo-frame/releases/tag/v1.5.0
[1.0.0]: https://github.com/YOUR_USERNAME/digital-photo-frame/releases/tag/v1.0.0
