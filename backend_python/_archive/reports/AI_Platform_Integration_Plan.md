# AI平台接入实施计划

## 目标

参考豆包MVP的成功经验，按顺序调通以下三个AI平台：
1. **DeepSeek** (已完成基础适配，需验证调通)
2. **通义千问 (Qwen)** (已完成基础适配，需验证调通)
3. **智谱AI (Zhipu)** (已完成基础适配，需验证调通)

## 当前状态

### 已配置的API密钥（.env文件）
```bash
DEEPSEEK_API_KEY=sk-13908093890f46fb82c52a01c8dfc464
QWEN_API_KEY=sk-5261a4dfdf964a5c9a6364128cc4c653
ZHIPU_API_KEY=504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh
```

### 已实现的适配器
- ✅ DeepSeekAdapter (`deepseek_adapter.py`)
- ✅ QwenAdapter (`qwen_adapter.py`)
- ✅ ZhipuAdapter (`zhipu_adapter.py`)
- ✅ DoubaoAdapter (`doubao_adapter.py`) - MVP已成功

### 工厂模式注册
所有适配器已在 `AIAdapterFactory` 中注册，支持通过平台名称创建实例。

## 实施步骤

---

## 第一阶段：DeepSeek平台调通

### 1.1 验证适配器基础功能（30分钟）

**目标**：验证DeepSeekAdapter能正常调用API并返回结果

**执行步骤**：
1. 创建独立测试脚本 `test_deepseek_integration.py`
2. 测试直接调用适配器（不经过Flask）
3. 验证API密钥有效性
4. 测试简单prompt调用
5. 记录响应时间和成功率

**成功标准**：
- 能成功获取API响应
- 响应内容符合预期
- 无超时或连接错误

**参考代码**：
```python
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import AIPlatformType

adapter = AIAdapterFactory.create(
    AIPlatformType.DEEPSEEK, 
    api_key="sk-13908093890f46fb82c52a01c8dfc464",
    model_name="deepseek-chat"
)
response = adapter.send_prompt("介绍一下DeepSeek", timeout=30)
assert response.success == True
```

### 1.2 创建MVP风格的DeepSeek测试接口（45分钟）

**目标**：参考豆包MVP接口，创建DeepSeek专用测试接口

**执行步骤**：
1. 在 `views.py` 中新增 `/api/mvp/deepseek-test` 接口
2. 复制 `mvp_brand_test` 的实现模式
3. 修改平台类型为 DeepSeek
4. 调整超时时间为30秒
5. 添加AI响应日志记录

**关键修改点**：
```python
@wechat_bp.route('/api/mvp/deepseek-test', methods=['POST'])
def mvp_deepseek_test():
    # 参考 mvp_brand_test 实现
    # 修改：AIAdapterFactory.create(AIPlatformType.DEEPSEEK, ...)
    # 修改：timeout=30（DeepSeek响应较快）
```

### 1.3 前端测试验证（30分钟）

**目标**：通过前端界面调用DeepSeek接口

**执行步骤**：
1. 在前端添加DeepSeek测试页面（或复用现有MVP页面）
2. 修改API调用地址为 `/api/mvp/deepseek-test`
3. 选择DeepSeek平台
4. 提交测试请求
5. 验证结果返回和展示

**成功标准**：
- 前端能正常发起请求
- 后端返回execution_id
- 能查询到进度和结果
- 结果展示正常

### 1.4 性能测试与优化（30分钟）

**目标**：确定DeepSeek的最佳超时时间和并发策略

**执行步骤**：
1. 连续调用10次，记录响应时间
2. 计算P50、P95延迟
3. 根据延迟数据调整timeout参数
4. 测试并发调用（如有需要）

**预期结果**：
- DeepSeek响应时间应在5-15秒
- 超时设置建议：30秒

### 1.5 集成到主程序（45分钟）

**目标**：将DeepSeek集成到主程序的品牌测试流程

**执行步骤**：
1. 修改 `scheduler.py` 中的模型映射
2. 添加DeepSeek的timeout配置
3. 测试多平台并发（豆包 + DeepSeek）
4. 验证结果聚合正常

**DeepSeek阶段交付物**：
- ✅ DeepSeekAdapter测试通过
- ✅ `/api/mvp/deepseek-test` 接口可用
- ✅ 前端可正常调用
- ✅ 性能参数确定
- ✅ 主程序集成完成

---

## 第二阶段：通义千问(Qwen)平台调通

### 2.1 验证适配器基础功能（30分钟）

**目标**：验证QwenAdapter能正常调用API

**执行步骤**：
1. 创建测试脚本 `test_qwen_integration.py`
2. 测试API密钥有效性
3. 测试简单prompt调用
4. 验证响应格式

**参考代码**：
```python
adapter = AIAdapterFactory.create(
    AIPlatformType.QWEN,
    api_key="sk-5261a4dfdf964a5c9a6364128cc4c653",
    model_name="qwen-max"
)
response = adapter.send_prompt("介绍一下通义千问", timeout=30)
```

### 2.2 创建MVP风格的Qwen测试接口（45分钟）

**目标**：创建Qwen专用测试接口

**执行步骤**：
1. 新增 `/api/mvp/qwen-test` 接口
2. 复制MVP实现模式
3. 修改平台类型为 Qwen
4. 设置超时时间

**注意点**：
- Qwen的API端点：`https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation`
- 请求格式与DeepSeek不同，需验证payload正确性

### 2.3 前端测试验证（30分钟）

**目标**：前端调用Qwen接口

**执行步骤**：
1. 添加Qwen测试页面
2. 选择"通义千问"平台
3. 提交测试
4. 验证结果

### 2.4 性能测试与优化（30分钟）

**目标**：确定Qwen的最佳参数

**执行步骤**：
1. 连续调用测试
2. 记录响应时间
3. 调整timeout参数

**预期结果**：
- Qwen响应时间：10-20秒
- 超时设置建议：30-45秒

### 2.5 集成到主程序（45分钟）

**目标**：Qwen集成到主流程

**执行步骤**：
1. 修改scheduler模型映射
2. 添加Qwen timeout配置
3. 测试多平台并发

**Qwen阶段交付物**：
- ✅ QwenAdapter测试通过
- ✅ `/api/mvp/qwen-test` 接口可用
- ✅ 前端可正常调用
- ✅ 主程序集成完成

---

## 第三阶段：智谱AI(Zhipu)平台调通

### 3.1 验证适配器基础功能（30分钟）

**目标**：验证ZhipuAdapter能正常调用API

**执行步骤**：
1. 创建测试脚本 `test_zhipu_integration.py`
2. 测试API密钥
3. 测试prompt调用

**参考代码**：
```python
adapter = AIAdapterFactory.create(
    AIPlatformType.ZHIPU,
    api_key="504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh",
    model_name="glm-4"
)
response = adapter.send_prompt("介绍一下智谱AI", timeout=30)
```

### 3.2 创建MVP风格的Zhipu测试接口（45分钟）

**目标**：创建Zhipu专用测试接口

**执行步骤**：
1. 新增 `/api/mvp/zhipu-test` 接口
2. 复制MVP实现模式
3. 修改平台类型为 Zhipu

**注意点**：
- Zhipu的API端点：`https://open.bigmodel.cn/api/paas/v4`
- 需要验证认证头格式

### 3.3 前端测试验证（30分钟）

**目标**：前端调用Zhipu接口

### 3.4 性能测试与优化（30分钟）

**预期结果**：
- Zhipu响应时间：10-20秒
- 超时设置建议：30-45秒

### 3.5 集成到主程序（45分钟）

**Zhipu阶段交付物**：
- ✅ ZhipuAdapter测试通过
- ✅ `/api/mvp/zhipu-test` 接口可用
- ✅ 前端可正常调用
- ✅ 主程序集成完成

---

## 第四阶段：统一整合与优化

### 4.1 多平台并发测试（60分钟）

**目标**：验证多平台同时调用的稳定性

**执行步骤**：
1. 修改主程序支持多平台选择
2. 测试同时调用豆包 + DeepSeek + Qwen + Zhipu
3. 验证结果聚合逻辑
4. 测试超时和异常处理

### 4.2 统一AI响应日志（30分钟）

**目标**：所有平台的响应都记录到统一日志文件

**执行步骤**：
1. 确保所有适配器调用 `log_ai_response_v2`
2. 验证日志文件 `ai_responses.jsonl` 格式正确
3. 测试日志轮转和清理

### 4.3 性能监控集成（30分钟）

**目标**：所有平台接入性能监控

**执行步骤**：
1. 验证metrics收集正常
2. 检查告警阈值设置
3. 测试告警通知

### 4.4 文档更新（30分钟）

**目标**：更新接口文档和配置说明

**执行步骤**：
1. 更新API文档，添加新平台说明
2. 更新配置指南
3. 更新部署文档

---

## 实施时间表

| 阶段 | 任务 | 预计时间 | 累计时间 |
|------|------|----------|----------|
| **DeepSeek** | 适配器验证 | 30min | 30min |
| | MVP接口 | 45min | 1h15min |
| | 前端测试 | 30min | 1h45min |
| | 性能测试 | 30min | 2h15min |
| | 主程序集成 | 45min | 3h |
| **Qwen** | 适配器验证 | 30min | 3h30min |
| | MVP接口 | 45min | 4h15min |
| | 前端测试 | 30min | 4h45min |
| | 性能测试 | 30min | 5h15min |
| | 主程序集成 | 45min | 6h |
| **Zhipu** | 适配器验证 | 30min | 6h30min |
| | MVP接口 | 45min | 7h15min |
| | 前端测试 | 30min | 7h45min |
| | 性能测试 | 30min | 8h15min |
| | 主程序集成 | 45min | 9h |
| **整合** | 多平台并发 | 60min | 10h |
| | 日志统一 | 30min | 10h30min |
| | 监控集成 | 30min | 11h |
| | 文档更新 | 30min | 11h30min |

**总计：约11.5小时**

---

## 风险与应对

### 风险1：API密钥无效或额度不足
**应对**：
- 提前验证密钥有效性
- 准备备用密钥
- 监控API调用配额

### 风险2：API响应格式变化
**应对**：
- 添加响应格式验证
- 增加错误处理逻辑
- 记录原始响应用于调试

### 风险3：网络超时或不稳定
**应对**：
- 设置合理的超时时间
- 实现重试机制
- 添加断路器保护

### 风险4：前端403错误未解决
**应对**：
- 优先解决403问题
- 使用测试脚本绕过前端验证
- 本地curl/postman测试

---

## 验收标准

### 功能验收
- [ ] DeepSeek平台可正常调用并返回结果
- [ ] Qwen平台可正常调用并返回结果
- [ ] Zhipu平台可正常调用并返回结果
- [ ] 多平台并发调用正常
- [ ] 结果聚合和展示正常

### 性能验收
- [ ] DeepSeek平均响应时间 < 15秒
- [ ] Qwen平均响应时间 < 20秒
- [ ] Zhipu平均响应时间 < 20秒
- [ ] 多平台并发无超时

### 质量验收
- [ ] AI响应日志记录完整
- [ ] 错误处理完善
- [ ] 监控指标正常
- [ ] 文档更新完成

---

## 附录：关键代码参考

### 豆包MVP成功经验
```python
# 1. 获取配置
api_key = config_manager.get_api_key('doubao')
model_id = os.getenv('DOUBAO_MODEL_ID') or config_manager.get_platform_model('doubao')

# 2. 创建适配器
adapter = AIAdapterFactory.create(AIPlatformType.DOUBAO, api_key, model_id)

# 3. 调用API（顺序执行，确保拿到结果）
ai_response = adapter.send_prompt(actual_question, timeout=90)

# 4. 记录日志
log_ai_response(
    question=actual_question,
    response=ai_response.content,
    platform='豆包',
    model=model_id,
    ...
)
```

### 模型名称映射
```python
# factory.py 中的 MODEL_NAME_MAP
"DeepSeek": "deepseek",
"通义千问": "qwen",
"智谱AI": "zhipu",
"智谱": "zhipu",
```

### 超时配置建议
```python
TIMEOUT_CONFIG = {
    'deepseek': 30,   # 响应较快
    'qwen': 45,       # 中等响应时间
    'zhipu': 45,      # 中等响应时间
    'doubao': 90,     # 响应较慢
}
```

---

**计划制定时间**: 2026-02-15
**计划版本**: 1.0
**制定依据**: 豆包MVP成功经验 + 现有适配器实现
