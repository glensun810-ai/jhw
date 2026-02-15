# 第三阶段：智谱AI(Zhipu)平台调通 - 任务清单

## 任务概览

**目标**：调通智谱AI平台
**预计时间**：2.5小时
**API密钥**：`504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh`
**模型名称**：`glm-4`
**API端点**：`https://open.bigmodel.cn/api/paas/v4`

---

## 任务3.1：验证适配器基础功能（30分钟）

### 创建测试脚本

文件：`/backend_python/test_zhipu_integration.py`

```python
#!/usr/bin/env python3
"""智谱AI适配器集成测试"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.base_adapter import AIPlatformType


def test_zhipu_basic():
    """测试Zhipu基础调用"""
    print("=" * 60)
    print("智谱AI适配器基础测试")
    print("=" * 60)
    
    api_key = "504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh"
    model_name = "glm-4"
    
    try:
        print(f"\n1. 创建适配器...")
        adapter = AIAdapterFactory.create(
            AIPlatformType.ZHIPU,
            api_key=api_key,
            model_name=model_name
        )
        print("   ✅ 适配器创建成功")
        
        print(f"\n2. 测试简单prompt...")
        test_prompt = "请用一句话介绍智谱AI"
        print(f"   Prompt: {test_prompt}")
        
        start_time = time.time()
        response = adapter.send_prompt(test_prompt, timeout=30)
        elapsed = time.time() - start_time
        
        print(f"   响应时间: {elapsed:.2f}秒")
        print(f"   成功状态: {response.success}")
        
        if response.success:
            print(f"   ✅ API调用成功")
            print(f"   内容预览: {response.content[:100]}...")
            return True
        else:
            print(f"   ❌ API调用失败: {response.error_message}")
            return False
            
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_zhipu_brand_questions():
    """测试品牌问题"""
    print("\n" + "=" * 60)
    print("智谱AI品牌问题测试")
    print("=" * 60)
    
    api_key = "504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh"
    model_name = "glm-4"
    
    try:
        adapter = AIAdapterFactory.create(
            AIPlatformType.ZHIPU,
            api_key=api_key,
            model_name=model_name
        )
        
        test_questions = [
            "元若曦养生茶怎么样？",
            "养生堂品牌介绍",
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n   问题{i}: {question}")
            start_time = time.time()
            response = adapter.send_prompt(question, timeout=30)
            elapsed = time.time() - start_time
            
            status = "✅" if response.success else "❌"
            print(f"   {status} {elapsed:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
        return False


def main():
    print("\n智谱AI平台集成测试")
    print(f"API密钥: 504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh")
    print(f"模型: glm-4")
    
    results = []
    results.append(("基础调用", test_zhipu_basic()))
    results.append(("品牌问题", test_zhipu_brand_questions()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {status} - {name}")
    
    return 0 if all(r[1] for r in results) else 1


if __name__ == "__main__":
    exit(main())
```

### 执行测试

```bash
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python test_zhipu_integration.py
```

---

## 任务3.2：创建MVP风格的Zhipu测试接口（45分钟）

### 在views.py中添加接口

创建 `/api/mvp/zhipu-test`：

```python
@wechat_bp.route('/api/mvp/zhipu-test', methods=['POST'])
@require_auth_optional
@rate_limit(limit=3, window=60, per='endpoint')
@monitored_endpoint('/api/mvp/zhipu-test', require_auth=False, validate_inputs=True)
def mvp_zhipu_test():
    """
    智谱AI平台MVP测试接口
    """
    data = request.get_json(force=True)
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    try:
        brand_list = data.get('brand_list', [])
        questions = data.get('customQuestions', [])
        
        if not brand_list or not questions:
            return jsonify({'error': 'brand_list and customQuestions are required'}), 400
        
        main_brand = brand_list[0]
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
        
        api_logger.info(f"[Zhipu MVP] Starting test for {main_brand}")
        
        # 顺序执行
        results = []
        for idx, question in enumerate(questions):
            # ... 类似DeepSeek实现
            # 修改：AIAdapterFactory.create(AIPlatformType.ZHIPU, ...)
            # 修改：timeout=45
            pass
        
        return jsonify({
            'execution_id': execution_id,
            'status': 'completed',
            'results': results
        })
        
    except Exception as e:
        api_logger.error(f"[Zhipu MVP] Test failed: {str(e)}")
        return jsonify({'error': str(e)}), 500
```

---

## 任务3.3：前端测试验证（30分钟）

### 创建前端测试页面

创建：`/pages/mvp-zhipu/index.js`

- API地址：`/api/mvp/zhipu-test`
- 平台名称："智谱AI"

---

## 任务3.4：性能测试与优化（30分钟）

### 预期性能

- 平均响应时间：10-20秒
- 建议超时：45秒

### 配置更新

```bash
export ZHIPU_TIMEOUT=45
```

---

## 任务3.5：集成到主程序（45分钟）

### 修改scheduler

```python
MODEL_NAME_MAP.update({
    'zhipu': 'glm-4',
    '智谱': 'glm-4',
    '智谱AI': 'glm-4',
})

TIMEOUT_CONFIG.update({
    'zhipu': 45,
})
```

---

## Zhipu阶段验收清单

- [ ] 任务3.1：适配器基础功能验证通过
- [ ] 任务3.2：MVP接口创建成功
- [ ] 任务3.3：前端测试验证通过
- [ ] 任务3.4：性能测试完成
- [ ] 任务3.5：主程序集成完成

**智谱AI平台调通完成！**
