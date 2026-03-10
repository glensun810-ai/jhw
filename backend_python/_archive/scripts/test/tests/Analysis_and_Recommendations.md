# GEO系统接口测试问题分析与建议方案

## 一、已知问题分析

### 1.1 403 Forbidden 错误

#### 问题描述
在测试过程中发现，多个 `/api/*` 路径的接口返回 **403 Forbidden** 错误，包括：
- `GET /api/test`
- `POST /api/perform-brand-test`
- `GET /api/test-progress`
- 其他 `/api/*` 接口

#### 根因分析

**可能原因1：CORS配置问题**
```python
# 当前CORS配置在 app.py 中
CORS(app, 
     supports_credentials=True, 
     resources={
         r"/api/*": {
             "origins": "*",
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "X-WX-OpenID", "X-OpenID", "X-Wechat-OpenID", "X-Requested-With"],
             "expose_headers": ["Content-Type", "X-Request-ID"],
             "supports_credentials": True
         }
     })
```

**问题点**：
1. CORS配置顺序可能影响效果
2. OPTIONS预检请求可能未被正确处理
3. 微信小程序的请求头可能不完全匹配

**可能原因2：装饰器拦截**
- `@monitored_endpoint` 装饰器中的输入验证
- `@rate_limit` 限流装饰器
- `@require_auth_optional` 认证装饰器

**可能原因3：Flask蓝图注册问题**
- 蓝图注册顺序
- URL前缀冲突

#### 建议方案

**方案1：修复CORS配置**
```python
# 在 app.py 中，确保CORS在蓝图注册之前配置
from flask_cors import CORS

app = Flask(__name__)

# 1. 先配置CORS
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["*"],
        "supports_credentials": True
    }
})

# 2. 再注册蓝图
from wechat_backend.views import wechat_bp
app.register_blueprint(wechat_bp)
```

**方案2：在视图函数中处理OPTIONS**
```python
@wechat_bp.route('/api/perform-brand-test', methods=['POST', 'OPTIONS'])
def perform_brand_test():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    # ... 正常处理逻辑
```

**方案3：临时禁用问题装饰器**
```python
# 在 views.py 中临时禁用可能导致问题的装饰器
@wechat_bp.route('/api/perform-brand-test', methods=['POST', 'OPTIONS'])
# @rate_limit(limit=5, window=60, per='endpoint')  # 临时禁用
# @monitored_endpoint('/api/perform-brand-test', require_auth=False, validate_inputs=True)  # 临时禁用
def perform_brand_test():
    # ... 正常处理逻辑
```

### 1.2 字段兼容性问题

#### 问题描述
前端传递的参数格式与后端期望的格式存在差异：

| 前端字段 | 后端字段 | 状态 |
|---------|---------|------|
| `customQuestions` (数组) | `custom_question` (字符串) | 需兼容 |
| `selectedModels` (对象数组) | 需解析提取name | 已处理 |
| `userOpenid` | `userOpenid` | 一致 |

#### 建议方案

**方案1：后端增强兼容性**
```python
# 在 perform_brand_test 中增加字段兼容处理
custom_questions = []
if 'custom_question' in data:
    custom_questions = [data['custom_question']]
elif 'customQuestions' in data:
    custom_questions = data['customQuestions']
```

**方案2：前端统一字段格式**
- 统一使用 `custom_question` 字符串格式
- `selectedModels` 传递简化后的格式

### 1.3 超时与性能问题

#### 问题描述
- 品牌测试接口响应时间过长（豆包API平均45秒）
- 可能导致前端超时
- 用户体验不佳

#### 建议方案

**方案1：异步处理 + 轮询**
```python
# 当前已实现异步处理
def perform_brand_test():
    execution_id = str(uuid.uuid4())
    # 启动后台线程执行任务
    Thread(target=run_async_test, args=(execution_id, ...)).start()
    # 立即返回execution_id
    return jsonify({"status": "success", "execution_id": execution_id})
```

**方案2：优化AI调用超时**
```python
# 针对不同平台设置不同超时
if platform_name == 'doubao':
    api_timeout = 90  # 豆包需要更长超时
else:
    api_timeout = 60
```

**方案3：增加进度反馈**
- 细化进度阶段（抓取中、分析中、评分中）
- 增加阶段性结果返回

### 1.4 认证与授权问题

#### 问题描述
- 部分接口认证要求不明确
- 可选认证装饰器可能存在问题

#### 建议方案

**方案1：明确接口认证要求**
```python
# 公开接口（无需认证）
@wechat_bp.route('/api/test', methods=['GET'])
@rate_limit(limit=50, window=60, per='ip')
def test_api():
    pass

# 需要认证接口
@wechat_bp.route('/api/test-history', methods=['GET'])
@require_auth  # 强制认证
@rate_limit(limit=20, window=60, per='ip')
def get_test_history():
    pass

# 可选认证接口
@wechat_bp.route('/api/perform-brand-test', methods=['POST'])
@require_auth_optional  # 可选认证
@rate_limit(limit=5, window=60, per='ip')
def perform_brand_test():
    pass
```

## 二、测试覆盖建议

### 2.1 需要补充的测试场景

#### 1. 边界值测试
- 品牌名称最大长度（100字符）
- 问题数量上限
- 并发请求数上限

#### 2. 异常场景测试
- 网络中断恢复
- AI平台API不可用
- 数据库连接失败

#### 3. 性能测试
- 并发用户测试（10/50/100用户）
- 长时间运行稳定性
- 内存泄漏检测

#### 4. 安全测试
- 认证绕过测试
- 越权访问测试
- 敏感信息泄露检查

### 2.2 测试数据准备

```python
# 建议的测试数据集
TEST_DATASETS = {
    "valid_brands": [
        "测试品牌",
        "Brand123",
        "品牌-名称_测试",
        "A" * 100,  # 最大长度
    ],
    "invalid_brands": [
        "<script>alert('xss')</script>",
        "'; DROP TABLE users; --",
        "",  # 空字符串
        "A" * 101,  # 超过最大长度
    ],
    "valid_questions": [
        "这个品牌怎么样？",
        "What is this brand?",
        "Q" * 500,  # 最大长度
    ],
    "invalid_questions": [
        "<img src=x onerror=alert('xss')>",
        ""; DELETE FROM table; --",
        "Q" * 501,  # 超过最大长度
    ]
}
```

## 三、代码质量建议

### 3.1 错误处理增强

```python
# 当前代码
@app.route('/api/perform-brand-test', methods=['POST'])
def perform_brand_test():
    data = request.get_json()
    # ... 处理逻辑
    
# 建议改进
@app.route('/api/perform-brand-test', methods=['POST'])
def perform_brand_test():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data", "code": 400}), 400
        
        # 参数验证
        validator = BrandTestRequestValidator()
        is_valid, errors = validator.validate(data)
        if not is_valid:
            return jsonify({"error": "Validation failed", "details": errors, "code": 400}), 400
        
        # 业务逻辑
        result = process_brand_test(data)
        return jsonify({"status": "success", "data": result})
        
    except BrandTestException as e:
        logger.error(f"Brand test error: {e}")
        return jsonify({"error": str(e), "code": 500}), 500
    except Exception as e:
        logger.exception("Unexpected error in brand test")
        return jsonify({"error": "Internal server error", "code": 500}), 500
```

### 3.2 日志记录增强

```python
# 建议增加结构化日志
import structlog

logger = structlog.get_logger()

def perform_brand_test():
    logger.info(
        "brand_test_started",
        endpoint="/api/perform-brand-test",
        brand_list=data.get('brand_list'),
        models=[m.get('name') for m in data.get('selectedModels', [])],
        user_id=get_current_user_id()
    )
    
    try:
        result = process_test(data)
        logger.info(
            "brand_test_completed",
            execution_id=result['execution_id'],
            duration_ms=result['duration'],
            status="success"
        )
    except Exception as e:
        logger.error(
            "brand_test_failed",
            error=str(e),
            error_type=type(e).__name__,
            brand_list=data.get('brand_list')
        )
```

### 3.3 监控告警增强

```python
# 建议增加关键指标监控
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
brand_test_requests = Counter('brand_test_requests_total', 'Total brand test requests', ['status'])
brand_test_duration = Histogram('brand_test_duration_seconds', 'Brand test duration')
active_tests = Gauge('active_tests', 'Number of active tests')

@brand_test_duration.time()
def perform_brand_test():
    active_tests.inc()
    try:
        result = process_test(data)
        brand_test_requests.labels(status='success').inc()
        return result
    except Exception as e:
        brand_test_requests.labels(status='error').inc()
        raise
    finally:
        active_tests.dec()
```

## 四、部署与运维建议

### 4.1 环境配置检查清单

```markdown
- [ ] 环境变量配置正确（API Keys, Secrets）
- [ ] 数据库连接配置正确
- [ ] Redis/缓存服务可用
- [ ] 日志目录有写权限
- [ ] 防火墙端口开放
- [ ] CORS配置与前端域名匹配
- [ ] SSL证书配置（生产环境）
- [ ] 监控告警配置
```

### 4.2 健康检查端点

```python
@app.route('/health')
def health_check():
    checks = {
        "database": check_database(),
        "redis": check_redis(),
        "ai_platforms": check_ai_platforms(),
        "disk_space": check_disk_space(),
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return jsonify({
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }), status_code
```

## 五、优先级排序

### P0 - 立即修复（阻塞性问题）
1. **403 Forbidden错误** - 影响所有API调用
2. **CORS配置问题** - 影响前端访问

### P1 - 高优先级（重要功能）
1. **字段兼容性处理** - 影响数据正确性
2. **超时优化** - 影响用户体验
3. **认证机制完善** - 影响安全性

### P2 - 中优先级（优化改进）
1. **错误处理增强** - 提升稳定性
2. **日志记录完善** - 提升可观测性
3. **性能监控** - 提升运维能力

### P3 - 低优先级（长期规划）
1. **WebSocket实时推送** - 替代轮询
2. **缓存策略优化** - 提升性能
3. **分页加载** - 大数据量处理

## 六、测试执行建议

### 6.1 回归测试清单

每次代码变更后，执行以下测试：

```markdown
- [ ] 基础连通性测试（/health, /api/test）
- [ ] 认证流程测试（登录 -> 访问受保护接口）
- [ ] 品牌测试完整流程（提交 -> 查询进度 -> 获取结果）
- [ ] 数据同步测试（上传 -> 下载 -> 删除）
- [ ] 安全测试（SQL注入, XSS尝试）
```

### 6.2 自动化测试集成

```yaml
# .github/workflows/test.yml
name: API Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Start server
        run: python run.py &
      - name: Wait for server
        run: sleep 5
      - name: Run tests
        run: python tests/test_geo_api_comprehensive.py
```

---

**文档版本**: 1.0
**最后更新**: 2026-02-15
**编写依据**: 2026-02-14_GEO_System_Interface_Audit_Report.md
