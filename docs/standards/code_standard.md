# 代码规范

**版本**: v1.0  
**生效日期**: 2026-02-23  
**状态**: ✅ 已实施

---

## 一、总则

### 1.1 目的

规范项目代码风格，提高代码可读性、可维护性和一致性。

### 1.2 适用范围

适用于所有项目成员和所有代码（Python、JavaScript）。

### 1.3 核心原则

1. **清晰**: 代码应该清晰易懂
2. **简洁**: 避免不必要的复杂性
3. **一致**: 保持风格一致
4. **可测试**: 代码应该易于测试

---

## 二、Python 代码规范

### 2.1 命名规范

**模块/文件**:
```python
# 小写字母 + 下划线
config.py
ai_adapter.py
doubao_priority_adapter.py
```

**类**:
```python
# 大驼峰命名
class AIClient:
    pass

class DoubaoAdapter(AIClient):
    pass
```

**函数/方法**:
```python
# 小写字母 + 下划线
def get_api_key(platform):
    pass

def send_prompt(self, prompt, **kwargs):
    pass
```

**变量**:
```python
# 小写字母 + 下划线
api_key = "xxx"
model_name = "doubao"
```

**常量**:
```python
# 大写字母 + 下划线
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
```

### 2.2 导入规范

**标准顺序**:
```python
# 1. 标准库
import os
import sys
from pathlib import Path

# 2. 第三方库
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# 3. 项目内部导入（从近到远）
from .models import User
from ..services import diagnosis_service
from config.settings import Config
```

**导入位置**:
```python
# ✅ 推荐：文件顶部
import os
import sys

def main():
    pass

# ❌ 不推荐：函数内部
def main():
    import os  # 不要这样做
    pass
```

### 2.3 代码格式

**缩进**:
```python
# 使用 4 个空格
def hello():
    print("Hello")  # 4 空格缩进
    if True:
        print("World")  # 8 空格缩进
```

**空行**:
```python
# 类之间：2 个空行
class A:
    pass


class B:
    pass

# 方法之间：1 个空行
def method1():
    pass

def method2():
    pass
```

**行长度**:
```python
# 最大 79 字符
long_string = "This is a very long string that should be broken into multiple lines"  # ❌

# 使用括号换行
long_string = (
    "This is a very long string that should be "
    "broken into multiple lines"
)  # ✅
```

### 2.4 注释规范

**文档字符串**:
```python
def get_api_key(platform: str) -> str:
    """
    获取平台 API Key

    Args:
        platform: 平台名称

    Returns:
        API 密钥或空字符串
    """
    pass
```

**行内注释**:
```python
# ✅ 推荐：解释为什么
if not api_key:
    # API Key 缺失，使用默认值
    api_key = DEFAULT_KEY

# ❌ 不推荐：解释是什么
api_key = DEFAULT_KEY  # 设置 API Key
```

### 2.5 异常处理

**推荐**:
```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"操作失败：{e}")
    raise
except Exception as e:
    logger.error(f"未知错误：{e}")
    raise
```

**不推荐**:
```python
try:
    result = risky_operation()
except:  # ❌ 不要捕获所有异常
    pass
```

---

## 三、JavaScript 代码规范

### 3.1 命名规范

**文件**:
```javascript
// 小写字母 + 连字符或下划线
brand-test-service.js
config.js
```

**类**:
```javascript
// 大驼峰命名
class AIClient {
    constructor() {}
}
```

**函数**:
```javascript
// 小驼峰命名
function getApiKey(platform) {}
const sendPrompt = (prompt) => {}
```

**变量**:
```javascript
// 小驼峰命名
const apiKey = "xxx";
let modelName = "doubao";
```

**常量**:
```javascript
// 大写字母 + 下划线
const MAX_RETRIES = 3;
const DEFAULT_TIMEOUT = 30000;
```

### 3.2 导入/导出规范

**CommonJS**:
```javascript
// 导入
const { get, post } = require('../utils/request');
const { API_ENDPOINTS } = require('../utils/config');

// 导出
module.exports = {
    checkServerConnectionApi,
    startBrandTestApi,
};
```

**ES6 Modules** (如使用):
```javascript
// 导入
import { get, post } from '../utils/request';
import { API_ENDPOINTS } from '../utils/config';

// 导出
export default {
    checkServerConnectionApi,
    startBrandTestApi,
};
```

### 3.3 代码格式

**缩进**:
```javascript
// 使用 2 个空格
function hello() {
  console.log("Hello");  // 2 空格缩进
  if (true) {
    console.log("World");  // 4 空格缩进
  }
}
```

**空行**:
```javascript
// 函数之间：1 个空行
function method1() {
  pass;
}

function method2() {
  pass;
}
```

**行长度**:
```javascript
// 最大 100 字符
const longString = "This is a very long string that should be broken into multiple lines";  // ❌

// 使用模板字符串
const longString = `
  This is a very long string that should be
  broken into multiple lines
`;  // ✅
```

### 3.4 注释规范

**JSDoc**:
```javascript
/**
 * 获取平台 API Key
 *
 * @param {string} platform - 平台名称
 * @returns {string} API 密钥或空字符串
 */
function getApiKey(platform) {
  return "";
}
```

**行内注释**:
```javascript
// ✅ 推荐：解释为什么
if (!apiKey) {
  // API Key 缺失，使用默认值
  apiKey = DEFAULT_KEY;
}

// ❌ 不推荐：解释是什么
apiKey = DEFAULT_KEY;  // 设置 API Key
```

### 3.5 异步处理

**Promise**:
```javascript
// ✅ 推荐：使用 async/await
async function fetchData() {
  try {
    const response = await fetch(url);
    const data = await response.json();
    return data;
  } catch (error) {
    logger.error(`获取失败：${error}`);
    throw error;
  }
}

// ❌ 不推荐：Promise 链
function fetchData() {
  return fetch(url)
    .then(response => response.json())
    .catch(error => {
      logger.error(`获取失败：${error}`);
      throw error;
    });
}
```

---

## 四、测试规范

### 4.1 测试文件命名

**Python**:
```python
test_doubao_adapter.py
test_config.py
```

**JavaScript**:
```javascript
test-brandTestService.js
test-config.js
```

### 4.2 测试结构

**Python**:
```python
def test_get_api_key():
    """测试获取 API Key"""
    # Arrange
    platform = "doubao"
    
    # Act
    result = Config.get_api_key(platform)
    
    # Assert
    assert result is not None
    assert isinstance(result, str)
```

**JavaScript**:
```javascript
test('应该获取 API Key', () => {
  // Arrange
  const platform = 'doubao';
  
  // Act
  const result = Config.getApiKey(platform);
  
  // Assert
  expect(result).toBeDefined();
  expect(typeof result).toBe('string');
});
```

### 4.3 测试覆盖率

**目标**:
- 核心模块：>85%
- 适配器模块：>90%
- 工具模块：>80%

**运行测试**:
```bash
# Python
pytest --cov=src tests/

# JavaScript
node tests/run-tests.js
```

---

## 五、代码审查清单

### 5.1 通用检查

- [ ] 命名清晰且一致
- [ ] 代码格式正确
- [ ] 注释充分且准确
- [ ] 异常处理适当
- [ ] 测试覆盖充分

### 5.2 Python 检查

- [ ] 遵循 PEP 8
- [ ] 使用类型提示
- [ ] 文档字符串完整
- [ ] 导入顺序正确

### 5.3 JavaScript 检查

- [ ] 使用 ES6+ 特性
- [ ] 避免全局变量
- [ ] 使用 const/let
- [ ] 异步处理正确

---

## 六、最佳实践

### 6.1 DRY 原则 (Don't Repeat Yourself)

**推荐**:
```python
def get_platform_config(platform):
    """获取平台配置"""
    config_map = {
        'doubao': DOUBAO_CONFIG,
        'deepseek': DEEPSEEK_CONFIG,
    }
    return config_map.get(platform)
```

**不推荐**:
```python
if platform == 'doubao':
    config = DOUBAO_CONFIG
elif platform == 'deepseek':
    config = DEEPSEEK_CONFIG
```

### 6.2 单一职责原则

**推荐**:
```python
class DoubaoAdapter:
    """豆包 AI 适配器"""
    
    def send_prompt(self, prompt):
        """发送提示词"""
        pass
    
    def parse_response(self, response):
        """解析响应"""
        pass
```

**不推荐**:
```python
class DoubaoAdapter:
    """豆包 AI 适配器（做所有事情）"""
    
    def process(self, prompt):
        # 发送、解析、保存、日志... 所有逻辑都在这里
        pass
```

### 6.3 错误处理

**推荐**:
```python
try:
    result = api_call()
except APIError as e:
    logger.error(f"API 错误：{e}")
    raise
except Exception as e:
    logger.error(f"未知错误：{e}")
    raise
```

**不推荐**:
```python
result = api_call()  # 无错误处理
```

---

## 七、附录

### 7.1 相关文档

- [配置规范](./config_standard.md)
- [架构文档](../architecture/README.md)
- [部署指南](../deployment.md)

### 7.2 参考标准

- **Python**: PEP 8, PEP 257
- **JavaScript**: Airbnb JavaScript Style Guide
- **测试**: pytest, Jest

---

**文档生成时间**: 2026-02-23 15:30  
**维护人**: 首席全栈工程师 (AI)  
**审核状态**: ✅ 已通过
