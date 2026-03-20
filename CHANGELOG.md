# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- 📄 新增 `docs/2026-03-20-progress-summary.md` 项目进展回顾

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
