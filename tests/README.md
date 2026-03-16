# Tests

本目录包含项目的测试用例。

## 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_config.py

# 查看覆盖率
pytest --cov=app --cov-report=html
```

## 测试文件结构

- `test_config.py` - 配置模块测试
- `test_routes.py` - API 路由测试
- `test_recommendation.py` - 推荐算法测试
- `test_upload.py` - 上传功能测试

## 编写测试

```python
def test_example():
    """测试示例"""
    assert True
```
