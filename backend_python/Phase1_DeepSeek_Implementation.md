# 第一阶段：DeepSeek平台调通 - 详细任务清单

## 任务概览

**目标**：调通DeepSeek平台，参考豆包MVP成功经验
**预计时间**：3小时
**API密钥**：`sk-13908093890f46fb82c52a01c8dfc464`
**模型名称**：`deepseek-chat`

---

## 任务1.1：验证适配器基础功能（30分钟）

### 步骤1：创建测试脚本

创建文件：`/backend_python/test_deepseek_integration.py`

```python
#!/usr/bin/env python3
"""
DeepSeek适配器集成测试
验证DeepSeekAdapter能正常调用API
"""

import sys
import os
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import AIPlatformType


def test_deepseek_basic():
    """测试DeepSeek基础调用"""
    print("=" * 60)
    print("DeepSeek适配器基础测试")
    print("=" * 60)
    
    api_key = "sk-13908093890f46fb82c52a01c8dfc464"
    model_name = "deepseek-chat"
    
    try:
        print(f"\n1. 创建适配器...")
        print(f"   API Key: {api_key[:20]}...")
        print(f"   Model: {model_name}")
        
        adapter = AIAdapterFactory.create(
            AIPlatformType.DEEPSEEK,
            api_key=api_key,
            model_name=model_name
        )
        print("   ✅ 适配器创建成功")
        
        print(f"\n2. 测试简单prompt...")
        test_prompt = "请用一句话介绍DeepSeek"
        print(f"   Prompt: {test_prompt}")
        
        start_time = time.time()
        response = adapter.send_prompt(test_prompt, timeout=30)
        elapsed = time.time() - start_time
        
        print(f"   响应时间: {elapsed:.2f}秒")
        print(f"   成功状态: {response.success}")
        
        if response.success:
            print(f"   ✅ API调用成功")
            print(f"   内容预览: {response.content[:100]}...")
            print(f"   Token使用: {response.tokens_used}")
            print(f"   模型: {response.model}")
            return True
        else:
            print(f"   ❌ API调用失败")
            print(f"   错误: {response.error_message}")
            print(f"   错误类型: {response.error_type}")
            return False
            
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deepseek_brand_question():
    """测试品牌问题（模拟真实场景）"""
    print("\n" + "=" * 60)
    print("DeepSeek品牌问题测试")
    print("=" * 60)
    
    api_key = "sk-13908093890f46fb82c52a01c8dfc464"
    model_name = "deepseek-chat"
    
    try:
        adapter = AIAdapterFactory.create(
            AIPlatformType.DEEPSEEK,
            api_key=api_key,
            model_name=model_name
        )
        
        # 模拟真实品牌问题
        test_questions = [
            "元若曦养生茶怎么样？",
            "养生堂品牌介绍",
            "固生堂靠谱吗？"
        ]
        
        results = []
        for i, question in enumerate(test_questions, 1):
            print(f"\n   问题{i}: {question}")
            start_time = time.time()
            response = adapter.send_prompt(question, timeout=30)
            elapsed = time.time() - start_time
            
            results.append({
                'question': question,
                'success': response.success,
                'latency': elapsed,
                'content_length': len(response.content) if response.content else 0
            })
            
            if response.success:
                print(f"   ✅ 成功 ({elapsed:.2f}s, {len(response.content)}字符)")
            else:
                print(f"   ❌ 失败: {response.error_message}")
        
        # 统计结果
        success_count = sum(1 for r in results if r['success'])
        avg_latency = sum(r['latency'] for r in results) / len(results)
        
        print(f"\n   统计: {success_count}/{len(results)} 成功")
        print(f"   平均响应时间: {avg_latency:.2f}秒")
        
        return success_count == len(results)
        
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deepseek_performance():
    """测试DeepSeek性能（连续调用）"""
    print("\n" + "=" * 60)
    print("DeepSeek性能测试")
    print("=" * 60)
    
    api_key = "sk-13908093890f46fb82c52a01c8dfc464"
    model_name = "deepseek-chat"
    
    try:
        adapter = AIAdapterFactory.create(
            AIPlatformType.DEEPSEEK,
            api_key=api_key,
            model_name=model_name
        )
        
        latencies = []
        test_prompt = "你好"
        
        print(f"\n   连续调用10次...")
        for i in range(10):
            start_time = time.time()
            response = adapter.send_prompt(test_prompt, timeout=30)
            elapsed = time.time() - start_time
            latencies.append(elapsed)
            
            status = "✅" if response.success else "❌"
            print(f"   {status} 调用{i+1}: {elapsed:.2f}s")
            
            if not response.success:
                print(f"      错误: {response.error_message}")
        
        # 计算统计值
        latencies.sort()
        p50 = latencies[len(latencies)//2]
        p95 = latencies[int(len(latencies)*0.95)]
        avg = sum(latencies) / len(latencies)
        
        print(f"\n   性能统计:")
        print(f"   - 平均响应时间: {avg:.2f}秒")
        print(f"   - P50响应时间: {p50:.2f}秒")
        print(f"   - P95响应时间: {p95:.2f}秒")
        print(f"   - 最小响应时间: {min(latencies):.2f}秒")
        print(f"   - 最大响应时间: {max(latencies):.2f}秒")
        
        # 建议超时时间
        suggested_timeout = int(p95 * 1.5)
        print(f"\n   建议超时时间: {suggested_timeout}秒")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("DeepSeek平台集成测试")
    print("=" * 60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API密钥: sk-13908093890f46fb82c52a01c8dfc464")
    print(f"模型: deepseek-chat")
    
    results = []
    
    # 运行测试
    results.append(("基础调用", test_deepseek_basic()))
    results.append(("品牌问题", test_deepseek_brand_question()))
    results.append(("性能测试", test_deepseek_performance()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！DeepSeek平台已调通。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查上述详情。")
        return 1


if __name__ == "__main__":
    exit(main())
```

### 步骤2：执行测试

```bash
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python test_deepseek_integration.py
```

### 预期输出

```
============================================================
DeepSeek平台集成测试
============================================================
测试时间: 2026-02-15 02:00:00
API密钥: sk-13908093890f46fb82c52a01c8dfc464
模型: deepseek-chat

============================================================
DeepSeek适配器基础测试
============================================================

1. 创建适配器...
   API Key: sk-13908093890f46fb82c5...
   Model: deepseek-chat
   ✅ 适配器创建成功

2. 测试简单prompt...
   Prompt: 请用一句话介绍DeepSeek
   响应时间: 3.52秒
   成功状态: True
   ✅ API调用成功
   内容预览: DeepSeek是杭州深度求索人工智能基础技术研究有限公司开发的AI助手...
   Token使用: 156
   模型: deepseek-chat
```

### 验收标准
- [ ] 适配器能正常创建
- [ ] API调用成功
- [ ] 响应内容符合预期
- [ ] 响应时间在合理范围（< 15秒）

---

## 任务1.2：创建MVP风格的DeepSeek测试接口（45分钟）

### 步骤1：在views.py中添加接口

在 `/backend_python/wechat_backend/views.py` 中添加：

```python
@wechat_bp.route('/api/mvp/deepseek-test', methods=['POST'])
@require_auth_optional
@rate_limit(limit=3, window=60, per='endpoint')
@monitored_endpoint('/api/mvp/deepseek-test', require_auth=False, validate_inputs=True)
def mvp_deepseek_test():
    """
    DeepSeek平台MVP测试接口
    参考豆包MVP实现，顺序执行确保拿到结果
    """
    data = request.get_json(force=True)
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    try:
        # 提取参数
        brand_list = data.get('brand_list', [])
        questions = data.get('customQuestions', [])
        
        if not brand_list or not questions:
            return jsonify({'error': 'brand_list and customQuestions are required'}), 400
        
        main_brand = brand_list[0]
        
        # 生成执行ID
        execution_id = str(uuid.uuid4())
        
        # 初始化状态
        execution_store[execution_id] = {
            'progress': 0,
            'completed': 0,
            'total': len(questions),
            'status': 'processing',
            'stage': 'ai_testing',
            'results': [],
            'start_time': datetime.now().isoformat()
        }
        
        api_logger.info(f"[DeepSeek MVP] Starting brand test for {main_brand} with {len(questions)} questions")
        
        # 顺序执行每个问题
        results = []
        for idx, question in enumerate(questions):
            try:
                # 更新进度
                progress = int((idx / len(questions)) * 100)
                execution_store[execution_id].update({
                    'progress': progress,
                    'completed': idx,
                    'status': f'Processing question {idx + 1}/{len(questions)}'
                })
                
                # 替换品牌占位符
                actual_question = question.replace('{brandName}', main_brand)
                if len(brand_list) > 1:
                    actual_question = actual_question.replace('{competitorBrand}', brand_list[1])
                
                api_logger.info(f"[DeepSeek MVP] Q{idx + 1}: {actual_question[:50]}...")
                
                # 调用DeepSeek API
                from .ai_adapters.factory import AIAdapterFactory
                from .ai_adapters.base_adapter import AIPlatformType
                
                # 获取DeepSeek配置
                from .config_manager import config_manager
                api_key = config_manager.get_api_key('deepseek')
                model_id = os.getenv('DEEPSEEK_MODEL_ID') or config_manager.get_platform_model('deepseek') or 'deepseek-chat'
                
                api_logger.info(f"[DeepSeek MVP] Using model_id: {model_id}")
                
                if not api_key:
                    raise ValueError("DeepSeek API密钥未配置")
                
                # 创建适配器并调用
                adapter = AIAdapterFactory.create(AIPlatformType.DEEPSEEK, api_key, model_id)
                
                start_time = time.time()
                ai_response = adapter.send_prompt(actual_question, timeout=30)  # DeepSeek响应快，30秒足够
                latency = time.time() - start_time
                
                # 导入AI响应记录器
                from utils.ai_response_logger_v2 import log_ai_response
                
                if ai_response.success:
                    result_item = {
                        'question': actual_question,
                        'response': ai_response.content,
                        'platform': 'DeepSeek',
                        'model': model_id,
                        'latency': round(latency * 1000),
                        'success': True,
                        'timestamp': datetime.now().isoformat()
                    }
                    api_logger.info(f"[DeepSeek MVP] Q{idx + 1} success in {latency:.2f}s")
                    
                    # 记录AI响应
                    try:
                        log_ai_response(
                            question=actual_question,
                            response=ai_response.content,
                            platform='DeepSeek',
                            model=model_id,
                            brand=main_brand,
                            competitor=brand_list[1] if len(brand_list) > 1 else None,
                            latency_ms=round(latency * 1000),
                            success=True,
                            execution_id=execution_id,
                            metadata={'source': 'deepseek_mvp_test'}
                        )
                    except Exception as log_error:
                        api_logger.warning(f"[DeepSeek MVP] 记录失败: {log_error}")
                else:
                    result_item = {
                        'question': actual_question,
                        'response': f'API调用失败: {ai_response.error_message}',
                        'platform': 'DeepSeek',
                        'model': model_id,
                        'latency': round(latency * 1000),
                        'success': False,
                        'error': ai_response.error_message,
                        'timestamp': datetime.now().isoformat()
                    }
                    api_logger.warning(f"[DeepSeek MVP] Q{idx + 1} failed: {ai_response.error_message}")
                
                results.append(result_item)
                execution_store[execution_id]['results'].append(result_item)
                
            except Exception as e:
                api_logger.error(f"[DeepSeek MVP] Q{idx + 1} exception: {str(e)}")
                results.append({
                    'question': actual_question if 'actual_question' in locals() else question,
                    'response': f'处理异常: {str(e)}',
                    'platform': 'DeepSeek',
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # 完成
        execution_store[execution_id].update({
            'progress': 100,
            'completed': len(questions),
            'status': 'completed',
            'stage': 'completed',
            'end_time': datetime.now().isoformat()
        })
        
        api_logger.info(f"[DeepSeek MVP] Test completed for {main_brand}")
        
        return jsonify({
            'execution_id': execution_id,
            'status': 'completed',
            'results': results,
            'total_questions': len(questions),
            'success_count': sum(1 for r in results if r.get('success'))
        })
        
    except Exception as e:
        api_logger.error(f"[DeepSeek MVP] Test failed: {str(e)}")
        return jsonify({'error': str(e)}), 500
```

### 步骤2：重启Flask服务

```bash
pkill -f "python run.py"
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python run.py
```

### 步骤3：验证接口

```bash
curl -X POST http://127.0.0.1:5001/api/mvp/deepseek-test \
  -H "Content-Type: application/json" \
  -d '{
    "brand_list": ["测试品牌"],
    "customQuestions": ["测试品牌怎么样？"]
  }'
```

### 验收标准
- [ ] 接口能正常接收请求
- [ ] 能返回execution_id
- [ ] 能查询到进度和结果
- [ ] AI响应被正确记录

---

## 任务1.3：前端测试验证（30分钟）

### 步骤1：创建前端测试页面

创建文件：`/pages/mvp-deepseek/index.js`

参考 `mvp-index` 的实现，修改：
- API地址改为 `/api/mvp/deepseek-test`
- 平台选择改为"DeepSeek"

### 步骤2：添加页面配置

在 `app.json` 中添加：
```json
{
  "pages": [
    "pages/mvp-deepseek/index",
    ...
  ]
}
```

### 步骤3：测试调用

1. 打开小程序开发工具
2. 进入DeepSeek测试页面
3. 输入品牌名称和问题
4. 提交测试
5. 验证结果返回

### 验收标准
- [ ] 前端能正常发起请求
- [ ] 能显示进度
- [ ] 能展示结果
- [ ] 无403错误

---

## 任务1.4：性能测试与优化（30分钟）

### 步骤1：记录性能数据

使用任务1.1中的性能测试脚本，记录：
- 平均响应时间
- P50/P95延迟
- 成功率

### 步骤2：确定超时参数

根据性能数据，确定DeepSeek的最佳超时时间：

```python
# 建议配置
DEEPSEEK_TIMEOUT = 30  # 秒
```

### 步骤3：更新配置

在 `config_manager.py` 或环境变量中设置：
```bash
export DEEPSEEK_TIMEOUT=30
```

### 验收标准
- [ ] 平均响应时间 < 15秒
- [ ] P95响应时间 < 30秒
- [ ] 成功率 > 95%

---

## 任务1.5：集成到主程序（45分钟）

### 步骤1：修改scheduler模型映射

在 `scheduler.py` 中添加DeepSeek支持：

```python
MODEL_NAME_MAP = {
    'deepseek': 'deepseek-chat',
    'DeepSeek': 'deepseek-chat',
}

TIMEOUT_CONFIG = {
    'deepseek': 30,
}
```

### 步骤2：测试多平台并发

测试同时调用豆包 + DeepSeek：

```python
selected_models = [
    {'name': '豆包', 'checked': True},
    {'name': 'DeepSeek', 'checked': True}
]
```

### 步骤3：验证结果聚合

确保两个平台的结果都能正确聚合到最终结果中。

### 验收标准
- [ ] 主程序能调用DeepSeek
- [ ] 多平台并发正常
- [ ] 结果聚合正确

---

## DeepSeek阶段验收清单

- [ ] 任务1.1：适配器基础功能验证通过
- [ ] 任务1.2：MVP接口创建成功
- [ ] 任务1.3：前端测试验证通过
- [ ] 任务1.4：性能测试完成，参数确定
- [ ] 任务1.5：主程序集成完成

**DeepSeek平台调通完成！**

---

## 问题排查指南

### 问题1：API调用返回401
**可能原因**：API密钥无效
**解决方案**：
1. 检查密钥是否正确
2. 在DeepSeek官网验证密钥状态
3. 检查密钥是否有调用额度

### 问题2：响应时间过长
**可能原因**：网络问题或模型负载高
**解决方案**：
1. 增加超时时间
2. 检查网络连接
3. 尝试更换模型版本

### 问题3：返回内容为空
**可能原因**：prompt被过滤或模型限制
**解决方案**：
1. 检查prompt内容
2. 调整temperature参数
3. 查看API错误日志

---

**开始执行时间**: {{start_time}}
**预计完成时间**: {{end_time}}
