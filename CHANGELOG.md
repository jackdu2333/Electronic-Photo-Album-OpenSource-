# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-03-16

### Added
- ✨ **配置模块化**: 新增 `config.py` 配置管理模块，所有硬编码参数转为环境变量
- ✨ **Docker 支持**: 新增 `Dockerfile` 和 `docker-compose.yml`，支持一键部署
- ✨ **天气 API 代理**: 新增 `/api/weather-config` 端点，前端不再硬编码经纬度
- ✨ **宝宝信息可配置**: 宝宝名字和生日现在通过环境变量配置
- ✨ **深海打捞参数化**: 打捞概率和年份阈值可通过环境变量调整
- 📄 **完善文档**: 新增 README、部署指南、配置说明
- 📝 **MIT 许可证**: 添加开源许可证文件
- 📦 **项目规范化**: 添加 `pyproject.toml`、`.gitignore` 完善

### Changed
- 🔄 **推荐算法配置化**: 标签权重、季节权重从代码移至配置文件
- 🔄 **压缩参数可配置**: 目标大小、最大分辨率支持环境变量调整
- 🔄 **幻灯片时长可配置**: 展示时长从硬编码转为配置项

### Fixed
- 🐛 **前端配置注入**: 修复宝宝信息在前端硬编码的问题
- 🐛 **天气坐标暴露**: 修复前端直接调用外部 API 导致的坐标暴露问题

### Removed
- ⚠️ ** breaking change**: 移除硬编码的"木木"宝宝名，需通过 `BABY_NAME` 配置
- ⚠️ **breaking change**: 移除硬编码的苏州天气坐标，需通过 `WEATHER_LAT/LON` 配置

### Migration Guide
从 v1.x 升级到 v2.0：
1. 复制 `.env.example` 为 `.env`
2. 配置 `BABY_NAME` 和 `BABY_BIRTHDAY`（如需要）
3. 配置 `WEATHER_LAT` 和 `WEATHER_LON` 为你所在位置的坐标
4. 修改 `ADMIN_USERS` 为你的管理员账户

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
| 2.0.0   | 2026-03-16   | 配置模块化、Docker 部署、文档完善 |
| 1.6.0   | 2026-02-06   | 宝宝年龄、深海打捞 |
| 1.5.0   | 2026-02-05   | 智能搜索、新图标 |
| 1.0.0   | 2025-xx-xx   | 初始发布 |

---

## Upcoming Features

### v2.1.0 (Planned)
- [ ] 多租户支持
- [ ] 云存储集成（S3/OSS）
- [ ] 数据库迁移管理（Alembic）

### v2.2.0 (Planned)
- [ ] 主题/皮肤系统
- [ ] 国际化（i18n）
- [ ] 插件系统

### Future
- [ ] 官方文档站点
- [ ] Android/iOS 应用上架
- [ ] 社区贡献指南

---

[2.0.0]: https://github.com/YOUR_USERNAME/digital-photo-frame/releases/tag/v2.0.0
[1.6.0]: https://github.com/YOUR_USERNAME/digital-photo-frame/releases/tag/v1.6.0
[1.5.0]: https://github.com/YOUR_USERNAME/digital-photo-frame/releases/tag/v1.5.0
[1.0.0]: https://github.com/YOUR_USERNAME/digital-photo-frame/releases/tag/v1.0.0
