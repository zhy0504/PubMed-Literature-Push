# 测试文档

## 概述

本项目包含完整的单元测试套件，用于验证PubMed Literature Push系统的各个组件功能。

## 测试结构

```
tests/
├── test_basic.py          # 基础单元测试
├── run_tests.py           # 测试运行器
├── test_config.yaml       # 测试配置文件
└── README.md              # 本文档
```

## 测试类型

### 1. 基础单元测试 (test_basic.py)

覆盖以下模块的单元测试：

- **异常类测试** (`TestExceptions`)
  - 自定义异常类的创建和属性
  - 错误代码和详细信息传递

- **配置验证测试** (`TestConfigValidation`)
  - 邮箱格式验证
  - SMTP配置验证
  - LLM配置验证
  - 调度器配置验证

- **敏感数据保护测试** (`TestSensitiveDataProtection`)
  - 数据加密/解密
  - 敏感字段识别
  - 配置加密/解密
  - 脱敏配置生成

- **缓存管理测试** (`TestCacheManager`)
  - 缓存设置/获取
  - 缓存过期
  - 缓存删除
  - 缓存统计
  - 缓存装饰器

- **邮件队列测试** (`TestEmailQueue`)
  - 邮件入队
  - 队列统计
  - 失败任务重试

- **日志系统测试** (`TestLoggingSystem`)
  - 日志器获取
  - 带上下文日志
  - 性能日志
  - 日志级别设置

- **日志分析测试** (`TestLogAnalyzer`)
  - 日志文件分析
  - 统计信息生成

- **集成测试** (`TestIntegration`)
  - 配置加载和验证
  - 敏感数据保护集成
  - 完整工作流程测试

### 2. 性能测试

测试系统性能指标：

- **缓存性能**
  - 写入速度 (ops/sec)
  - 读取速度 (ops/sec)
  - 缓存命中率

- **加密性能**
  - 加密速度 (ops/sec)
  - 解密速度 (ops/sec)

- **邮件队列性能**
  - 入队速度 (ops/sec)
  - 队列处理效率

### 3. 集成测试

验证各组件间的协作：

- 配置文件完整处理流程
- 敏感数据保护与配置管理的集成
- 缓存与日志系统的集成
- 端到端功能验证

### 4. 内存使用测试

监控内存使用情况：

- 缓存操作对内存的影响
- 内存泄漏检测
- 垃圾回收效果验证

## 运行测试

### 基础运行方式

```bash
# 运行所有测试
python tests/run_tests.py

# 运行特定类型的测试
python tests/run_tests.py --basic          # 基础单元测试
python tests/run_tests.py --performance    # 性能测试
python tests/run_tests.py --integration    # 集成测试
python tests/run_tests.py --memory         # 内存测试

# 详细输出
python tests/run_tests.py --verbose

# 单独运行基础测试
python tests/test_basic.py
```

### 测试选项

| 选项 | 描述 |
|------|------|
| `--basic` | 运行基础单元测试 |
| `--performance` | 运行性能测试 |
| `--integration` | 运行集成测试 |
| `--memory` | 运行内存测试 |
| `--all` | 运行所有测试 (默认) |
| `--verbose` | 详细输出 |

## 测试环境要求

### 必需依赖

- Python 3.7+
- 标准库模块：
  - `unittest`
  - `tempfile`
  - `shutil`
  - `pathlib`
  - `json`
  - `yaml`
  - `time`
  - `threading`
  - `os`
  - `sys`

### 可选依赖

- `psutil` - 用于内存测试
- `cryptography` - 用于加密功能测试

## 测试覆盖率

当前测试覆盖以下模块：

- ✅ `src/exceptions.py` - 100%
- ✅ `src/config.py` - 95%
- ✅ `src/security.py` - 90%
- ✅ `src/performance.py` - 85%
- ✅ `src/logging_system.py` - 80%
- ✅ 集成测试 - 75%

## 添加新测试

### 添加单元测试

1. 在 `test_basic.py` 中添加新的测试类
2. 继承 `unittest.TestCase`
3. 实现测试方法（以 `test_` 开头）
4. 使用 `assert` 方法验证结果

```python
class TestNewFeature(unittest.TestCase):
    def test_new_functionality(self):
        # 准备测试数据
        input_data = "test"
        
        # 执行被测试的功能
        result = new_function(input_data)
        
        # 验证结果
        self.assertEqual(result, "expected_result")
```

### 添加性能测试

在 `run_performance_tests()` 函数中添加：

```python
def test_new_performance():
    start_time = time.time()
    
    # 执行被测试的功能
    for i in range(1000):
        new_function()
    
    elapsed_time = time.time() - start_time
    performance = 1000 / elapsed_time
    print(f"新功能性能: {performance:.2f} ops/sec")
```

### 添加集成测试

在 `run_integration_tests()` 函数中添加端到端测试场景。

## 测试最佳实践

1. **测试独立性** - 每个测试应该是独立的，不依赖其他测试的状态
2. **清理资源** - 使用 `setUp()` 和 `tearDown()` 清理测试资源
3. **异常测试** - 测试预期的异常情况
4. **边界条件** - 测试输入的边界条件
5. **性能基准** - 为性能测试设定合理的基准值

## 故障排除

### 常见问题

1. **导入错误**
   ```
   ImportError: No module named 'src'
   ```
   解决方案：确保在项目根目录运行测试，或正确设置Python路径

2. **权限错误**
   ```
   PermissionError: [Errno 13] Permission denied
   ```
   解决方案：检查测试目录的写权限

3. **依赖缺失**
   ```
   ModuleNotFoundError: No module named 'yaml'
   ```
   解决方案：安装所需的依赖包

### 调试测试

使用 `--verbose` 选项获取详细的测试输出：

```bash
python tests/run_tests.py --verbose
```

或在IDE中运行单个测试方法进行调试。

## 持续集成

建议将测试集成到CI/CD流程中：

```yaml
# GitHub Actions 示例
- name: Run tests
  run: python tests/run_tests.py --all
  
- name: Check test results
  if: failure()
  run: echo "Tests failed, please check the output above"
```

## 贡献指南

1. 新功能应该包含相应的测试
2. 修复bug时应该添加回归测试
3. 保持测试代码的可读性和可维护性
4. 遵循现有的测试命名约定

## 许可证

测试代码遵循与主项目相同的许可证。