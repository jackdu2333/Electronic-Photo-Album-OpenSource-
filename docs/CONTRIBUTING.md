# 贡献指南

首先，感谢你愿意为 Digital Photo Frame 项目做出贡献！

本项目欢迎各种形式的贡献，包括但不限于：
- 🐛 Bug 报告与修复
- ✨ 新功能建议与实现
- 📄 文档改进与翻译
- 🎨 UI/UX 优化
- 🧪 测试用例编写
- 💬 问题解答与社区帮助

---

## 快速开始

### 1. Fork 仓库

点击 GitHub 页面右上角的 "Fork" 按钮，将仓库复制到你自己的账户下。

### 2. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/digital-photo-frame.git
cd digital-photo-frame
```

### 3. 添加上游仓库

```bash
git remote add upstream https://github.com/ORIGINAL_USERNAME/digital-photo-frame.git
git fetch upstream
```

### 4. 创建分支

```bash
# 保持与主分支同步
git checkout main
git merge upstream/main

# 创建特性分支
git checkout -b feature/amazing-feature
```

---

## 开发环境设置

### 1. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### 2. 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 3. 运行应用

```bash
python app.py
```

---

## 代码规范

### Python 代码风格

本项目使用以下工具进行代码格式化：

```bash
# 格式化代码
black .

# 代码检查
ruff check .

# 运行测试
pytest
```

### 代码风格指南

1. **命名规范**:
   - 变量和函数：小写 + 下划线（`snake_case`）
   - 类名：大写开头（`CamelCase`）
   - 常量：全大写 + 下划线（`UPPER_CASE`）

2. **注释**:
   - 使用中文注释
   - 函数需要 docstring
   - 复杂逻辑需要解释原因

3. **代码结构**:
   - 函数不超过 50 行
   - 单行不超过 100 字符
   - 避免过深的嵌套（不超过 3 层）

### 示例

```python
def get_seasonal_weight(photo_month: int, current_month: int) -> float:
    """
    计算照片的季节权重

    Args:
        photo_month: 照片拍摄月份 (1-12)
        current_month: 当前月份 (1-12)

    Returns:
        权重值 (float)
    """
    if photo_month is None:
        return config.SEASONAL_WEIGHT_NONE
    if photo_month == current_month:
        return config.SEASONAL_WEIGHT_CURRENT
    return config.SEASONAL_WEIGHT_OTHER
```

---

## 提交规范

### Commit Message 格式

本项目遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Type 类型

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 重构（既不是新功能也不是 Bug 修复）
- `test`: 测试相关
- `chore`: 构建、配置、工具等非代码变更

### 示例

```bash
# 新功能
git commit -m "feat(config): 添加深海打捞概率配置项"

# Bug 修复
git commit -m "fix(weather): 修复天气 API 超时问题"

# 文档更新
git commit -m "docs(readme): 更新快速开始章节"

# 重构
git commit -m "refactor(core): 提取推荐算法到独立模块"
```

---

## Pull Request 流程

### 1. 确保代码通过测试

```bash
pytest
```

### 2. 确保代码格式化

```bash
black .
ruff check .
```

### 3. 提交 PR

1. Push 到你的分支：
   ```bash
   git push origin feature/amazing-feature
   ```

2. 在 GitHub 上创建 Pull Request

3. 填写 PR 描述：
   - 说明变更内容
   - 说明变更原因
   - 添加相关 Issue 链接（如有）
   - 添加截图或录屏（如适用）

### 4. Code Review

- 耐心等待维护者 review
- 根据反馈进行修改
- 保持友好的沟通

---

## 测试指南

### 单元测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_config.py

# 查看覆盖率
pytest --cov=app --cov-report=html
```

### 手动测试

1. **照片上传测试**:
   - 测试不同格式（JPG, PNG, HEIC）
   - 测试大文件上传
   - 测试重复上传

2. **推荐算法测试**:
   - 验证季节权重生效
   - 验证深海打捞触发
   - 验证标签权重

3. **UI 测试**:
   - 测试响应式布局
   - 测试遥控器操作
   - 测试留言功能

---

## 文档贡献

### 文档结构

```
docs/
├── README.md              # 主文档
├── deployment.md          # 部署指南
├── configuration.md       # 配置说明
└── CONTRIBUTING.md        # 贡献指南（本文档）
```

### 文档规范

1. 使用 Markdown 格式
2. 代码块标注语言类型
3. 命令标注操作系统
4. 配置项说明包含：
   - 类型
   - 默认值
   - 说明
   - 示例

---

## 问题报告

### Bug 报告

请在 Issue 中包含以下信息：

1. **环境信息**:
   - 操作系统及版本
   - Python 版本
   - 部署方式（Docker/本地）

2. **问题描述**:
   - 预期行为
   - 实际行为
   - 复现步骤

3. **日志信息**:
   ```bash
   # Docker
   docker-compose logs

   # 本地
   cat logs/app.log
   ```

### 功能建议

请在 Issue 中包含：

1. **功能描述**: 清晰描述建议的功能
2. **使用场景**: 说明功能的使用场景
3. **实现思路**: 如有，提供实现思路
4. **替代方案**: 是否考虑过其他方案

---

## 社区行为准则

### 我们的承诺

为了营造一个开放和友好的环境，我们承诺：

- ✅ 使用友好和包容的语言
- ✅ 尊重不同的观点和经验
- ✅ ✅ 优雅地接受建设性批评
- ❌ 不对他人进行人身攻击
- ❌ 发表不适当或冒犯性的言论

### 适用范围

本行为准则适用于：
- GitHub Issue 和 Pull Request
- 项目相关的讨论区
- 项目相关的社交媒体

---

## 常见问题

### Q: 如何开始第一次贡献？
A: 查看 GitHub Issues 中标记为 `good first issue` 的问题，这些都是适合新手的任务。

### Q: 提交 PR 后多久会被 review？
A: 通常在 1-3 个工作日内，请耐心等待。

### Q: 如何联系维护者？
A: 可以通过 GitHub Issue 或邮件联系（如有公开）。

### Q: 可以提交商业功能吗？
A: 欢迎提交，但需要说明功能目的，并确保符合 MIT 许可证。

---

## 致谢

感谢所有为这个项目做出贡献的人！

本贡献指南参考了多个优秀开源项目的模板。

---

**Happy Coding! 🎉**
