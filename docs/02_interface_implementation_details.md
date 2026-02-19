# GEO 系统接口实现详解

> 基于源代码分析
> 分析时间：2026-02-14

---

## 一、前端架构详解

### 1. 统一配置管理

**文件位置**：`utils/config.js`

#### API 端点配置 (API_ENDPOINTS)

```javascript
const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/api/login',
    VALIDATE_TOKEN: '/api/validate-token',  // Needs backend implementation
    REFRESH_TOKEN: '/api/refresh-token',   // Needs backend implementation
    SEND_VERIFICATION_CODE: '/api/send-verification-code',  // Needs backend implementation
    REGISTER: '/api/register'               // Needs backend implementation
  },
  USER: {
    PROFILE: '/api/user/profile',          // Needs backend implementation
    UPDATE: '/api/user/update'             // Needs backend implementation
  },
  SYNC: {
    DATA: '/api/sync-data',                // Needs backend implementation
    DOWNLOAD: '/api/download-data',        // Needs backend implementation
    UPLOAD_RESULT: '/api/upload-result',   // Needs backend implementation
    DELETE_RESULT: '/api/delete-result'    // Needs backend implementation
  },
  HISTORY: {
    LIST: '/api/test-history'
  },
  BRAND: {
    TEST: '/api/perform-brand-test',
    PROGRESS: '/api/test-progress',
    STATUS: '/test/status'
  },
  COMPETITIVE: {
    ANALYSIS: '/action/recommendations'
  },
  SYSTEM: {
    TEST_CONNECTION: '/api/test'
  }
};
```

#### 环境配置 (ENV_CONFIG)

| 环境 | baseURL | 超时时间 | 说明 |
|------|---------|---------|------|
| develop | `http://127.0.0.1:5000` | 30秒 | 开发环境，支持模拟器调试 |
| trial | `https://staging.api.yourdomain.com` | 20秒 | 体验版环境 |
| release | `https://api.yourdomain.com` | 15秒 | 正式生产环境 |

#### 动态配置特性

- 支持从本地存储覆盖基础URL（`custom_base_url`）
- 自动检测小程序运行环境（`wx.getAccountInfoSync()`）

---

### 2. 请求工具封装

**文件位置**：`utils/request.js`

#### 核心功能

| 功能 | 说明 |
|------|------|
| 基础请求 | 基于 `wx.request` 封装，支持 GET/POST/PUT/DELETE |
| 自动认证 | 从本地存储获取 `userToken`，自动添加 `Authorization: Bearer ${token}` |
| 401处理 | 自动清理用户信息并跳转登录页 |
| 存储清理 | AI诊断大数据包导致存储溢出时自动清理 |
| 调试日志 | 支持 `DEBUG_AI_CODE` 标记的详细日志输出 |

#### 请求拦截器逻辑

```javascript
// 自动添加token
const token = wx.getStorageSync('userToken');
if (token) {
  requestParams.header.Authorization = `Bearer ${token}`;
}
```

#### 错误处理机制

1. **401 未授权**：清空缓存 → 跳转登录页
2. **400 错误**：打印后端返回的 `error` 和 `details`
3. **存储溢出**：递归清理保存的文件和本地存储
4. **网络错误**：显示 Toast 提示

#### 存储清理策略

```javascript
// 专门处理AI诊断大数据包的递归清理
clearStorageRecursive() {
  // 1. 递归删除保存的文件
  // 2. 清理本地存储
}
```

---

### 3. API 模块分层

#### 认证模块 (`api/auth.js`)

| 函数 | 路径 | 说明 |
|------|------|------|
| `userLogin(loginData)` | POST `/api/login` | 微信登录 |
| `validateToken()` | POST `/api/validate-token` | 验证JWT令牌 |
| `refreshToken(refreshToken)` | POST `/api/refresh-token` | 刷新令牌 |
| `sendVerificationCode(data)` | POST `/api/send-verification-code` | 发送手机验证码 |
| `registerUser(data)` | POST `/api/register` | 用户注册 |

#### 首页模块 (`api/home.js`)

| 函数 | 路径 | 说明 |
|------|------|------|
| `checkServerConnectionApi()` | GET `/api/test` | 检查服务器连接 |
| `startBrandTestApi(data)` | POST `/api/perform-brand-test` | 启动品牌测试 |
| `getTestProgressApi(executionId)` | GET `/api/test-progress?executionId=` | 获取测试进度 |
| `getTaskStatusApi(executionId)` | GET `/test/status/{executionId}` | 获取任务详细状态 |

#### 竞争分析模块 (`api/competitive-analysis.js`)

| 函数 | 路径 | 说明 |
|------|------|------|
| `performBrandTest(data)` | POST `/api/perform-brand-test` | 执行品牌测试 |
| `getTestProgress(params)` | GET `/api/test-progress` | 获取测试进度 |
| `performCompetitiveAnalysis(data)` | POST `/action/recommendations` | 执行竞争分析 |

---

## 二、后端架构详解

### 1. 应用入口

**文件位置**：`backend_python/main.py`

```python
from dotenv import load_dotenv
from wechat_backend import app

load_dotenv()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
```

- 使用 Flask 框架
- 端口 5000（与前端配置一致）
- 支持 `.env` 环境变量加载

---

### 2. 核心应用配置

**文件位置**：`backend_python/wechat_backend/app.py`

#### 安全响应头配置

```python
@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'"
    return response
```

#### CORS 配置

```python
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}})
```

#### JWT 容错处理

```python
try:
    from .security.auth import require_auth, require_auth_optional, get_current_user_id
except RuntimeError as e:
    if "PyJWT is required" in str(e):
        # 创建占位符函数，返回 500 错误
```

#### 适配器预热机制

```python
def warm_up_adapters():
    """预热所有已注册的API适配器"""
    adapters_to_warm = ['doubao', 'deepseek', 'qwen', 'chatgpt', 'gemini', 'zhipu', 'wenxin']
    # 后台线程初始化

threading.Thread(target=warm_up_adapters, daemon=True).start()
```

#### 核心端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 服务器状态信息 |
| `/health` | GET | 健康检查，返回 `{status, timestamp}` |
| `/api/config` | GET | 配置信息，返回 `{app_id, server_time, status, user_id}` |

---

### 3. 路由实现

**文件位置**：`backend_python/wechat_backend/views.py`

#### 装饰器链

| 装饰器 | 功能 | 参数 |
|--------|------|------|
| `@require_auth_optional` | 可选身份验证 | - |
| `@rate_limit` | 速率限制 | `limit`, `window`, `per` |
| `@monitored_endpoint` | 监控埋点 | `endpoint`, `require_auth`, `validate_inputs` |

#### 核心路由实现

##### 微信登录 (`/api/login`)

```python
@wechat_bp.route('/api/login', methods=['POST'])
@rate_limit(limit=10, window=60, per='ip')
@monitored_endpoint('/api/login', require_auth=False, validate_inputs=True)
def wechat_login():
    # 1. 获取微信 code
    # 2. 调用微信 auth.code2Session 接口
    # 3. 生成 JWT 令牌
    # 4. 返回 {status, data, token}
```

**流程**：
1. 验证输入 `code`（字母数字，1-50字符）
2. 请求微信接口 `https://api.weixin.qq.com/sns/jscode2session`
3. 获取 `openid` 和 `session_key`
4. 生成 JWT Token（包含角色和权限声明）
5. 返回完整会话数据

##### 品牌测试 (`/api/perform-brand-test`)

```python
@wechat_bp.route('/api/perform-brand-test', methods=['POST'])
@require_auth_optional
@rate_limit(limit=5, window=60, per='endpoint')
@monitored_endpoint('/api/perform-brand-test', require_auth=False, validate_inputs=True)
def perform_brand_test():
    # 多品牌支持 + 异步执行
```

**输入验证逻辑**：

1. **brand_list 验证**：
   - 必须存在且为 list 类型
   - 不能为空列表
   - 每个品牌必须是字符串
   - 使用 `validate_safe_text` 验证安全性

2. **selectedModels 解析**（健壮性处理）：
   ```python
   parsed_selected_models = []
   for model in selected_models:
       if isinstance(model, dict):
           # 提取 name/id/value/label 字段
           model_name = model.get('name') or model.get('id') or model.get('value') or model.get('label')
           if model_name:
               parsed_selected_models.append({'name': model_name, 'checked': model.get('checked', True)})
   ```
   - 支持对象数组和字符串数组两种格式
   - 自动提取核心标识符字段

3. **custom_question 处理**：
   - 兼容 `custom_question`（字符串）和 `customQuestions`（数组）两种参数名

##### 测试进度查询 (`/api/test-progress`)

- 从全局 `execution_store` 获取进度数据
- 返回包含 `progress`, `completed`, `total`, `status` 的对象

##### 任务状态查询 (`/test/status/<task_id>`)

- 从数据库查询任务状态
- 返回包含 `task_id`, `progress`, `stage`, `status`, `results`, `is_completed` 的完整状态

---

## 三、核心接口契约对照

| 前端调用 | 后端路由 | 关键特性 |
|---------|---------|---------|
| `userLogin({code})` | `POST /api/login` | 微信 code 换 session，返回 JWT Token |
| `startBrandTestApi({brand_list, selectedModels, customQuestions})` | `POST /api/perform-brand-test` | 异步执行，支持多品牌，字段兼容处理 |
| `getTestProgressApi(executionId)` | `GET /api/test-progress?executionId=` | 轮询进度，返回进度百分比 |
| `getTaskStatusApi(executionId)` | `GET /test/status/<task_id>` | 详细状态查询，包含 stage 和 results |
| `performCompetitiveAnalysis({source_intelligence, evidence_chain, brand_name})` | `POST /action/recommendations` | 竞争分析与建议生成 |

---

## 四、安全机制

### 1. 输入验证

| 验证器 | 用途 | 实现位置 |
|--------|------|---------|
| `InputValidator.validate_alphanumeric` | 验证字母数字 | `security/input_validation.py` |
| `validate_safe_text` | 验证安全文本 | `security/input_validation.py` |
| `sql_protector` | SQL 注入防护 | `security/sql_protection.py` |

### 2. 速率限制

```python
@rate_limit(limit=5, window=60, per='endpoint')  # 每端点每分钟5次
@rate_limit(limit=10, window=60, per='ip')       # 每IP每分钟10次
```

### 3. 认证流程

```
前端 wx.login() 获取 code
        ↓
POST /api/login {code}
        ↓
后端请求微信 auth.code2Session
        ↓
获取 openid + session_key
        ↓
生成 JWT Token
        ↓
返回 {status, data, token}
        ↓
前端存储 token
        ↓
后续请求自动携带 Authorization: Bearer {token}
```

---

## 五、数据流分析

### 品牌测试完整流程

```
┌─────────────┐     POST /api/perform-brand-test      ┌─────────────┐
│   前端小程序  │ ─────────────────────────────────────→ │   Flask后端  │
│             │     {brand_list, selectedModels,      │             │
│             │      custom_question}                  │             │
└─────────────┘                                        └─────────────┘
       ↑                                                       │
       │                                                       ↓
       │                                              ┌─────────────────┐
       │                                              │   输入验证与净化   │
       │                                              │  - brand_list验证 │
       │                                              │  - selectedModels │
       │                                              │    解析          │
       │                                              └─────────────────┘
       │                                                       │
       │                                                       ↓
       │                                              ┌─────────────────┐
       │                                              │   异步任务启动    │
       │                                              │  - 生成execution_id│
       │                                              │  - 初始化进度存储  │
       │                                              └─────────────────┘
       │                                                       │
       │         GET /api/test-progress?executionId=           │
       │←──────────────────────────────────────────────────────┘
       │              {progress, completed, total}
       │
       │              （轮询，直到 completed == total）
       │
       │         GET /test/status/<task_id>
       │←──────────────────────────────────────────────────────┐
       │              {task_id, progress, stage,               │
       │               status, results, is_completed}
       │                                                       │
       │                                              ┌─────────────────┐
       │                                              │   AI模型并行测试  │
       │                                              │  - 多平台适配器   │
       │                                              │  - 熔断器保护    │
       │                                              │  - 超时控制     │
       │                                              └─────────────────┘
       │                                                       │
       │                                              ┌─────────────────┐
       │                                              │   结果聚合与评分  │
       │                                              │  - 增强评分引擎   │
       │                                              │  - AI裁判评估   │
       │                                              └─────────────────┘
       │                                                       │
       │                                              ┌─────────────────┐
       │                                              │   深度情报分析    │
       │                                              │  - 信源情报处理   │
       │                                              │  - 竞争分析     │
       │                                              └─────────────────┘
       │                                                       │
       │         GET /test/result/<task_id>                   │
       │←──────────────────────────────────────────────────────┘
                    完整分析报告
```

---

## 六、待实现接口清单

根据代码中的注释标记 `// Needs backend implementation`：

| 接口路径 | 方法 | 功能 | 优先级 |
|---------|------|------|--------|
| `/api/validate-token` | POST | Token 验证 | 高 |
| `/api/refresh-token` | POST | Token 刷新 | 高 |
| `/api/send-verification-code` | POST | 发送手机验证码 | 中 |
| `/api/register` | POST | 用户注册 | 中 |
| `/api/user/profile` | GET/POST | 用户资料获取/更新 | 中 |
| `/api/user/update` | POST | 用户资料更新 | 中 |
| `/api/sync-data` | POST | 数据同步（上传） | 低 |
| `/api/download-data` | POST | 数据下载 | 低 |
| `/api/upload-result` | POST | 结果上传 | 低 |
| `/api/delete-result` | POST | 结果删除 | 低 |

---

## 七、关键模块依赖关系

```
views.py (路由层)
    ├── security/ (安全模块)
    │   ├── auth.py (JWT认证)
    │   ├── input_validation.py (输入验证)
    │   ├── sql_protection.py (SQL防护)
    │   └── rate_limiting.py (速率限制)
    ├── monitoring/ (监控模块)
    │   └── monitoring_decorator.py (端点监控)
    ├── ai_adapters/ (AI适配器)
    │   └── factory.py (适配器工厂)
    ├── test_engine/ (测试引擎)
    │   └── test_executor.py (测试执行器)
    ├── analytics/ (分析模块)
    │   ├── interception_analyst.py (拦截分析)
    │   ├── monetization_service.py (变现服务)
    │   └── source_intelligence_processor.py (信源情报)
    ├── models.py (数据模型)
    ├── database.py (数据库操作)
    └── logging_config.py (日志配置)
```

---

## 八、总结

本项目采用前后端分离架构：

- **前端**：微信小程序，使用统一封装的请求工具，支持多环境配置
- **后端**：Flask 框架，模块化设计，包含完整的安全、监控、AI适配器体系
- **接口契约**：设计良好，后端具备字段兼容性处理，提高了系统健壮性
- **核心流程**：品牌测试采用异步执行 + 轮询机制，支持多AI平台并行测试
