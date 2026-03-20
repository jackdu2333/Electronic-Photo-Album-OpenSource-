# 2026-03-20 项目进展回顾与后续规划

## 今日完成

### 1. 云服务器升级与数据保留

- 确认线上不是 Docker 部署，而是宝塔 `Python 项目管理器 + Nginx`。
- 旧项目目录确认：
  - `/www/wwwroot/photo_frame`
- 新版本目录确认：
  - `/www/wwwroot/photo_frame_v2`
- 已完成线上完整备份：
  - `photos.db`
  - `photo_metadata.json`
  - `messages.json`
  - `static/photos`
  - `.env`
  - 备份包位于旧项目 `backup/` 目录
- 已确认旧照片主目录为：
  - `/www/wwwroot/photo_frame/static/photos`
- 新版本已成功接管旧数据，并能识别约 `494` 张照片。

### 2. Python 运行环境

- 线上服务器原本只有 Python 3.8，不满足升级版项目要求。
- 已在阿里云 Linux 3 上安装 Python 3.11。
- 新版本运行环境已迁移到 Python 3.11 系列虚拟环境。

### 3. 线上关键问题排查与修复

#### 静态资源认证问题

- 问题：
  - `/static/photos/...` 被认证层错误拦截，导致图片请求被重定向到 `/login`。
- 影响：
  - 首页和后台照片不显示
  - 大量图片请求被重定向后会拖慢甚至卡住服务
- 已处理：
  - 云端已临时修复
  - 本地源码已正式修复到 [auth.py](/Users/jackdu/.newmax/workspace/Electronic-Photo-Album-OpenSource-/auth.py)

#### 新旧照片目录衔接问题

- 问题：
  - 新项目 `static/photos` 目录为空，而真实照片还在旧项目目录中
- 已处理：
  - 云端新项目 `photo_frame_v2/static/photos` 已改为指向旧照片目录的软链接

#### 启动/托管冲突问题

- 问题：
  - 宝塔托管、手动重启、端口残留之间存在冲突，导致过几次 `504 Gateway Time-out`
  - `gunicorn` 能启动，但会被重复重启或异常退出
- 结论：
  - 当前更像是进程托管层问题，不是主应用核心逻辑崩溃
- 当前状态：
  - 手动恢复服务后已可用

### 4. 登录页重设计

- 登录页已从“朴素表单页”升级为更有产品感的入口页面。
- 已完成：
  - 文案与登录行为统一
  - 桌面端视觉提升
  - 手机端适配修复
- 关键文件：
  - [templates/login.html](/Users/jackdu/.newmax/workspace/Electronic-Photo-Album-OpenSource-/templates/login.html)

### 5. 首页样式系统

- 已在首页加入隐藏式样式切换器。
- 交互方式：
  - 左上角唤出
  - 可切换 3 套首页样式
  - 选择结果保存到 `localStorage`

#### 当前三套样式

- 样式一：
  - 经典分栏布局
  - 稳定、通用、适合各种比例照片
- 样式二：
  - 沉浸全屏相框风
  - 当前设为默认样式
- 样式三：
  - 画廊展签风
  - 更偏审美展示

### 6. 首页样式已做的打磨

- 已针对低亮度长期播放场景优化：
  - 提高暗部对比度
  - 强化低亮度下文字可读性
  - 保持照片主图完整显示
- 已统一遵循：
  - 模糊背景铺满
  - 前景原图 `contain`
  - 尽量不裁坏横图/竖图

### 7. 首页已发现并处理的问题

#### 左侧信息区留白过大

- 问题：
  - 天气与留言区之间空白过大，视觉重心不稳
- 已处理：
  - 左侧结构拆分为 `info-top` 与 `info-bottom`
  - 留言区重新贴底布局

#### 样式二信息面板圆角/越界问题

- 问题：
  - 顶部圆角正常，底部形态异常
  - 信息板有越出底框的现象
- 已处理：
  - 为样式二面板明确高度、圆角与 `overflow: hidden`

#### 留言栏无法上下滑动

- 问题：
  - 留言区被改版后滚动体验损坏
  - 页面刷新时会被强制拉回底部
- 已处理：
  - 恢复 `#chat-container` 正常滚动
  - 修改前端逻辑：只有接近底部时才自动贴底
- 关键文件：
  - [templates/index.html](/Users/jackdu/.newmax/workspace/Electronic-Photo-Album-OpenSource-/templates/index.html)
  - [static/script.js](/Users/jackdu/.newmax/workspace/Electronic-Photo-Album-OpenSource-/static/script.js)

#### 样式二横图被左侧信息区遮挡

- 问题：
  - 一些横图主体靠左时，容易被样式二信息面板遮住
- 已处理：
  - 样式二前景图增加左侧安全边距
  - 前景图轻微向右偏移

#### 手机端适配不足

- 问题：
  - 横屏和竖屏都不够协调
- 已处理：
  - 横屏更接近网页端布局
  - 竖屏改成上下结构
  - 样式二、样式三均补了独立移动端规则

#### 手机横屏留言输入栏过高

- 问题：
  - 输入栏遮挡底部留言
- 已处理：
  - 压薄输入栏
  - 增加留言区底部避让

## 当前本地关键改动文件

- [auth.py](/Users/jackdu/.newmax/workspace/Electronic-Photo-Album-OpenSource-/auth.py)
- [templates/login.html](/Users/jackdu/.newmax/workspace/Electronic-Photo-Album-OpenSource-/templates/login.html)
- [templates/index.html](/Users/jackdu/.newmax/workspace/Electronic-Photo-Album-OpenSource-/templates/index.html)
- [static/script.js](/Users/jackdu/.newmax/workspace/Electronic-Photo-Album-OpenSource-/static/script.js)

## 云服务器后续同步建议

如果明天继续上线最新前端结果，优先同步：

- [auth.py](/Users/jackdu/.newmax/workspace/Electronic-Photo-Album-OpenSource-/auth.py)
- [templates/login.html](/Users/jackdu/.newmax/workspace/Electronic-Photo-Album-OpenSource-/templates/login.html)
- [templates/index.html](/Users/jackdu/.newmax/workspace/Electronic-Photo-Album-OpenSource-/templates/index.html)
- [static/script.js](/Users/jackdu/.newmax/workspace/Electronic-Photo-Album-OpenSource-/static/script.js)

注意：

- 不要覆盖 `.env`
- 不要覆盖 `photos.db`
- 不要覆盖 `photo_metadata.json`
- 不要覆盖 `messages.json`
- 不要覆盖 `static/photos`
- 不要删旧项目目录

## 明日建议工作顺序

### 优先级 1：理顺线上启动方式

目标：

- 解决宝塔托管与手动启动冲突
- 避免再次出现 `504`

建议：

- 明确最终由谁托管 `gunicorn`
- 统一 `5000` 端口启动方式
- 启动成功后先验证：
  - `/health`
  - 首页访问
  - 后台访问

### 优先级 2：继续打磨首页

重点方向：

- 继续收紧样式二，作为默认样式
- 保持样式一的稳定性
- 让样式三更有质感但不牺牲可读性
- 再检查不同照片比例下的展示效果

### 优先级 3：最终云端同步

建议顺序：

1. 停止线上项目
2. 同步前端/认证相关文件
3. 启动项目
4. 验证服务是否恢复
5. 测试登录、首页、留言、后台

## 当前判断

- 项目升级路径已经走通
- 数据迁移和旧数据接管已经成功
- 核心功能基本可用
- 当前最大的剩余风险不是业务逻辑，而是线上进程托管稳定性

## 一句话总结

今天已经完成了：

- 新版本接管旧数据
- 登录页重做
- 首页样式系统搭建
- 多轮桌面/移动端视觉打磨
- 多个线上与前端真实问题修复

明天最值得优先做的是：

- 先把线上启动方式彻底理顺
- 再把最新前端改动同步到云服务器
