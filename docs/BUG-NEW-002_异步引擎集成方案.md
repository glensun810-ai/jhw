# BUG-NEW-002: 异步执行引擎集成方案

**优先级**: 🔴 高
**预计工时**: 4 小时
**性能提升**: 60%

---

## 方案选择

### 方案 A: 完全重构（不推荐）
- 重写整个 nxm_execution_engine.py
- 改为纯异步实现
- **风险**: 高，可能引入新 Bug
- **工时**: 8+ 小时

### 方案 B: 渐进式集成（推荐）✅
- 保留现有代码结构
- 添加异步执行选项
- 逐步迁移
- **风险**: 低
- **工时**: 4 小时

**选择**: 方案 B（渐进式集成）

---

## 实施步骤

### 步骤 1: 添加异步执行模块导入

在 `nxm_execution_engine.py` 顶部添加：
```python
# BUG-NEW-002 修复：异步执行引擎
from wechat_backend.performance.async_execution_engine import execute_async
import asyncio
```

### 步骤 2: 创建异步执行包装函数

添加新函数：
```python
async def execute_nxm_test_async(
    execution_id: str,
    main_brand: str,
    competitor_brands: List[str],
    selected_models: List[Dict[str, Any]],
    raw_questions: List[str],
    user_id: str,
    user_level: str,
    execution_store: Dict[str, Any],
    timeout_seconds: int = 300
) -> Dict[str, Any]:
    """
    异步执行 NxM 测试（BUG-NEW-002 修复）
    """
    # 使用异步引擎执行
    results = await execute_async(
        questions=raw_questions,
        models=[m['name'] for m in selected_models],
        execute_func=call_ai_api_wrapper,
        max_concurrent=3,
        execution_id=execution_id,
        main_brand=main_brand,
        competitor_brands=competitor_brands,
        execution_store=execution_store
    )
    
    return {
        'success': True,
        'execution_id': execution_id,
        'results': results,
        'formula': f'{len(raw_questions)}问题 × {len(selected_models)}模型 = {len(raw_questions)*len(selected_models)}次请求 (异步执行)'
    }
```

### 步骤 3: 创建 AI 调用包装函数

```python
def call_ai_api_wrapper(
    question: str,
    model_name: str,
    execution_id: str,
    main_brand: str,
    competitor_brands: List[str],
    execution_store: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """
    AI 调用包装函数（适配异步引擎）
    """
    from config import Config
    
    # 创建 AI 客户端
    client = AIAdapterFactory.create(model_name)
    api_key = Config.get_api_key(model_name)
    
    if not api_key:
        raise ValueError(f"模型 {model_name} API Key 未配置")
    
    # 构建提示词
    prompt = GEO_PROMPT_TEMPLATE.format(
        brand_name=main_brand,
        competitors=', '.join(competitor_brands) if competitor_brands else '无',
        question=question
    )
    
    # 调用 AI（带重试）
    max_retries = 2
    retry_count = 0
    response = None
    geo_data = None
    
    while retry_count <= max_retries:
        try:
            response = client.generate_response(
                prompt=prompt,
                api_key=api_key
            )
            
            geo_data, parse_error = parse_geo_with_validation(
                response,
                execution_id,
                0,  # q_idx
                model_name
            )
            
            if not parse_error and not geo_data.get('_error'):
                break
                
        except Exception as e:
            api_logger.error(f"AI 调用失败：{model_name}: {e}")
            retry_count += 1
    
    # 返回结果
    return {
        'brand': main_brand,
        'question': question,
        'model': model_name,
        'response': response,
        'geo_data': geo_data or {'_error': 'AI 调用或解析失败'},
        'timestamp': datetime.now().isoformat(),
        '_failed': not geo_data or geo_data.get('_error')
    }
```

### 步骤 4: 修改主函数支持异步

```python
def execute_nxm_test(...):
    """
    执行 NxM 测试（支持同步和异步）
    """
    # 检查是否启用异步执行
    use_async = os.getenv('USE_ASYNC_EXECUTION', 'false').lower() == 'true'
    
    if use_async:
        # 使用异步执行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(execute_nxm_test_async(
                execution_id=execution_id,
                main_brand=main_brand,
                competitor_brands=competitor_brands,
                selected_models=selected_models,
                raw_questions=raw_questions,
                user_id=user_id,
                user_level=user_level,
                execution_store=execution_store,
                timeout_seconds=timeout_seconds
            ))
            return result
        finally:
            loop.close()
    else:
        # 使用现有同步执行（向后兼容）
        # ... 现有代码 ...
```

### 步骤 5: 添加环境变量配置

在 `.env` 中添加：
```bash
# 异步执行开关
USE_ASYNC_EXECUTION=true
ASYNC_MAX_CONCURRENT=3
```

---

## 测试验证

### 单元测试
```python
def test_async_execution():
    """测试异步执行"""
    result = execute_nxm_test(
        execution_id='test-123',
        main_brand='华为',
        competitor_brands=['小米', '特斯拉'],
        selected_models=[{'name': 'doubao'}],
        raw_questions=['问题 1'],
        user_id='user-123',
        user_level='premium',
        execution_store={}
    )
    
    assert result['success'] == True
    assert len(result['results']) > 0
```

### 性能测试
```python
import time

# 同步执行
start = time.time()
execute_nxm_test(..., use_async=False)
sync_time = time.time() - start

# 异步执行
start = time.time()
execute_nxm_test(..., use_async=True)
async_time = time.time() - start

print(f"同步执行：{sync_time:.2f}秒")
print(f"异步执行：{async_time:.2f}秒")
print(f"性能提升：{sync_time/async_time:.1f}x")
```

---

## 回滚方案

如果异步执行出现问题，可以立即回滚：

```bash
# 方法 1: 关闭异步执行
echo "USE_ASYNC_EXECUTION=false" >> .env

# 方法 2: Git 回滚
git checkout HEAD~1 -- backend_python/wechat_backend/nxm_execution_engine.py
```

---

## 预计效果

| 指标 | 同步执行 | 异步执行 | 改进 |
|-----|---------|---------|------|
| 3 问题×1 模型 | 15 秒 | 6 秒 | -60% |
| 3 问题×3 模型 | 45 秒 | 12 秒 | -73% |
| 并发数 | 1 | 3 | +200% |
| 资源利用 | 30% | 90% | +200% |

---

**实施时间**: 4 小时
**风险等级**: 低（渐进式，可回滚）
**性能提升**: 60-70%

**下一步**: 开始实施上述方案！
