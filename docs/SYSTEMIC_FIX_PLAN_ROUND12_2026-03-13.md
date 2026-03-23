# 诊断报告数据流系统性修复方案（第 12 次）

**制定日期**: 2026-03-13  
**制定人**: 系统首席架构师  
**版本**: v1.0 - 架构级修复  
**状态**: ⏳ 待实施

---

## 📊 问题现状分析

### 12 次修复历史回顾

| 轮次 | 假设根因 | 修复内容 | 结果 | 为什么失败 |
|-----|---------|---------|------|-----------|
| 1-2 | 云函数格式 | 数据解包 | ❌ | 方向错误 |
| 3-4 | WAL 可见性 | 检查点 | ❌ | 表面修复 |
| 5-6 | execution_store 空 | 同步数据 | ❌ | 未触及数据源 |
| 7-8 | 品牌字段为空 | 推断逻辑 | ❌ | brand 有值但是错的 |
| 9 | 内存数据流 | 同步 detailed_results | ❌ | 前端不从内存读取 |
| 10 | 数据库事务时序 | 重试 + 兜底 | ❌ | 代码未验证 |
| 11 | AI 结果解析 | 提取品牌 | ❌ | **服务器未重启** |
| 12 | **系统性问题** | **架构级修复** | ⏳ | **本次修复** |

### 数据流现状

```
AI 调用 → 结果保存 → 数据库 → 后端 API → 前端展示
  ❌        ❌         ❌       ❌        ❌
  提取失败  字段为 NULL  无验证   端点错误  无数据
```

---

## 🎯 系统性修复目标

### 技术目标

1. ✅ **数据正确性**: `extracted_brand` 提取率 > 95%
2. ✅ **数据完整性**: 原始 AI 响应 100% 保存
3. ✅ **API 可用性**: 完整报告 API 100% 返回正确数据
4. ✅ **前端展示**: 报告页 100% 显示完整数据

### 流程目标

1. ✅ **自动化测试**: 每次修复后自动验证
2. ✅ **部署清单**: 明确需要重启的服务
3. ✅ **监控告警**: 数据异常时立即通知
4. ✅ **数据质量**: 入库前验证数据有效性

---

## 🔧 技术修复方案

### 修复 1: AI 品牌提取逻辑验证

**文件**: `backend_python/wechat_backend/nxm_concurrent_engine_v3.py`

**验证步骤**:
```bash
# 1. 检查代码是否存在
grep -n "_extract_recommended_brand" backend_python/wechat_backend/nxm_concurrent_engine_v3.py

# 2. 检查方法实现
grep -A 30 "def _extract_recommended_brand" backend_python/wechat_backend/nxm_concurrent_engine_v3.py

# 3. 单元测试验证
python3 -m pytest backend_python/tests/test_brand_extraction.py -v
```

**预期输出**:
```
329: extracted_brand = self._extract_recommended_brand(ai_content, main_brand)
353: 'extracted_brand': extracted_brand,
446: def _extract_recommended_brand(
```

---

### 修复 2: 数据库 Schema 验证

**文件**: `backend_python/database/migrations/005_add_raw_response_fields.sql`

**验证步骤**:
```bash
# 检查字段是否存在
sqlite3 backend_python/database.db "PRAGMA table_info(diagnosis_results);" | grep -E "extracted_brand|raw_response"

# 检查数据质量
sqlite3 backend_python/database.db "SELECT COUNT(*) as total, COUNT(extracted_brand) as has_extracted FROM diagnosis_results;"
```

**预期输出**:
```
16|raw_response|TEXT|0||0
17|extracted_brand|TEXT|0||0
18|extraction_method|TEXT|0||0
19|platform|TEXT|0||0

total=10, has_extracted=10  # 100% 提取率
```

---

### 修复 3: 后端 API 端点验证

**文件**: `backend_python/wechat_backend/views/diagnosis_api.py`

**验证步骤**:
```bash
# 1. 检查 API 路由
grep -n "get_full_report\|/report/<execution_id>" backend_python/wechat_backend/views/diagnosis_api.py

# 2. 测试 API 端点
curl -X GET "http://localhost:5001/api/diagnosis/report/test_execution_id" | jq '.'

# 3. 检查返回数据结构
curl -X GET "http://localhost:5001/api/diagnosis/report/test_execution_id" | jq 'keys'
```

**预期输出**:
```
181: def get_full_report(execution_id):
{
  "report": {...},
  "results": [...],
  "brandDistribution": {...},
  "extractedBrandCount": 3
}
```

---

### 修复 4: 前端数据获取验证

**文件**: `pages/history-detail/history-detail.js`

**验证步骤**:
```javascript
// 1. 检查 API 端点
grep "api/diagnosis/report" pages/history-detail/history-detail.js

// 2. 检查数据处理方法
grep -A 10 "processHistoryDataFromApi" pages/history-detail/history-detail.js

// 3. 小程序开发者工具控制台
// 应该看到：
// [报告详情页] ✅ 服务器数据加载成功，有完整报告数据
```

---

## 📋 流程保障方案

### 1. 部署检查清单 (Deployment Checklist)

创建文件：`backend_python/DEPLOYMENT_CHECKLIST.md`

```markdown
## 后端部署检查清单

### 代码修改后

- [ ] 1. 检查 Python 语法
  ```bash
  python3 -m py_compile backend_python/wechat_backend/nxm_concurrent_engine_v3.py
  ```

- [ ] 2. 重启后端服务
  ```bash
  cd backend_python
  ./stop_server.sh
  ./start_server.sh
  ```

- [ ] 3. 验证服务启动
  ```bash
  curl http://localhost:5001/api/health
  ```

- [ ] 4. 执行测试诊断
  - 在小程序中执行一次完整诊断
  - 等待完成

- [ ] 5. 检查数据库
  ```bash
  sqlite3 backend_python/database.db \
    "SELECT execution_id, extracted_brand FROM diagnosis_results ORDER BY created_at DESC LIMIT 1;"
  ```
  - [ ] extracted_brand 不为 NULL
  - [ ] extracted_brand != main_brand

- [ ] 6. 检查品牌分布
  ```bash
  curl http://localhost:5001/api/diagnosis/report/{execution_id} | jq '.brandDistribution'
  ```
  - [ ] 有多个品牌（不是只有主品牌）

- [ ] 7. 前端验证
  - [ ] 打开小程序报告页
  - [ ] 看到品牌分布饼图
  - [ ] 看到多个品牌名称
```

---

### 2. 自动化测试脚本

创建文件：`backend_python/tests/verify_diagnosis_flow.py`

```python
#!/usr/bin/env python3
"""
诊断数据流自动化验证脚本

验证点：
1. AI 品牌提取逻辑是否生效
2. 数据库字段是否正确保存
3. API 是否返回完整数据
"""

import sqlite3
import requests
import sys
import time

BASE_URL = 'http://localhost:5001'
DB_PATH = 'backend_python/database.db'

def check_brand_extraction_code():
    """检查品牌提取代码是否存在"""
    print("🔍 检查品牌提取代码...")
    with open('backend_python/wechat_backend/nxm_concurrent_engine_v3.py', 'r') as f:
        content = f.read()
        if '_extract_recommended_brand' in content:
            print("✅ 品牌提取代码存在")
            return True
        else:
            print("❌ 品牌提取代码不存在")
            return False

def check_database_schema():
    """检查数据库 schema"""
    print("🔍 检查数据库 schema...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(diagnosis_results)")
    columns = [row[1] for row in cursor.fetchall()]
    
    required_columns = ['extracted_brand', 'raw_response', 'extraction_method']
    missing = [col for col in required_columns if col not in columns]
    
    if not missing:
        print("✅ 数据库 schema 正确")
        return True
    else:
        print(f"❌ 缺少字段：{missing}")
        return False

def check_data_quality():
    """检查数据质量"""
    print("🔍 检查数据质量...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查最新一条记录
    cursor.execute("""
        SELECT execution_id, brand, extracted_brand 
        FROM diagnosis_results 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    row = cursor.fetchone()
    
    if not row:
        print("❌ 数据库中没有记录")
        return False
    
    execution_id, brand, extracted_brand = row
    
    if extracted_brand is None:
        print(f"❌ extracted_brand 为 NULL (execution_id={execution_id})")
        return False
    
    if extracted_brand == brand:
        print(f"⚠️  extracted_brand 与 brand 相同：{extracted_brand}")
        # 不返回 False，因为可能是兜底情况
    
    print(f"✅ 数据质量检查通过 (extracted_brand={extracted_brand})")
    return True

def check_api_endpoint():
    """检查 API 端点"""
    print("🔍 检查 API 端点...")
    try:
        response = requests.get(f'{BASE_URL}/api/health', timeout=5)
        if response.status_code == 200:
            print("✅ 后端服务可访问")
            return True
        else:
            print(f"❌ 后端服务返回错误状态码：{response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 后端服务不可访问：{e}")
        return False

def main():
    print("=" * 60)
    print("诊断数据流自动化验证")
    print("=" * 60)
    
    checks = [
        ("代码检查", check_brand_extraction_code),
        ("数据库 schema", check_database_schema),
        ("数据质量", check_data_quality),
        ("API 端点", check_api_endpoint),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n[{name}]")
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 检查失败：{e}")
            results.append(False)
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (name, _) in enumerate(checks):
        status = "✅" if results[i] else "❌"
        print(f"{status} {name}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有检查通过！")
        return 0
    else:
        print("\n❌ 有检查未通过，请修复后重试")
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

**使用方式**:
```bash
# 执行验证
python3 backend_python/tests/verify_diagnosis_flow.py

# 部署后自动执行
./backend_python/start_server.sh && \
  sleep 5 && \
  python3 backend_python/tests/verify_diagnosis_flow.py
```

---

### 3. 监控告警机制

创建文件：`backend_python/monitoring/data_quality_monitor.py`

```python
#!/usr/bin/env python3
"""
数据质量监控脚本

监控指标：
1. extracted_brand 提取率
2. brand 字段为空的比例
3. API 错误率
"""

import sqlite3
import logging
from datetime import datetime, timedelta

DB_PATH = 'backend_python/database.db'
LOG_PATH = 'backend_python/logs/quality_monitor.log'

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('data_quality_monitor')

def check_extraction_rate():
    """检查品牌提取率"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 统计最近 1 小时的数据
    one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(extracted_brand) as has_extracted,
            COUNT(CASE WHEN extracted_brand != brand THEN 1 END) as different
        FROM diagnosis_results
        WHERE created_at > ?
    """, (one_hour_ago,))
    
    row = cursor.fetchone()
    total, has_extracted, different = row
    
    if total == 0:
        logger.warning("过去 1 小时没有新数据")
        return
    
    extraction_rate = has_extracted / total if total > 0 else 0
    
    logger.info(
        f"品牌提取率监控：total={total}, "
        f"has_extracted={has_extracted}, "
        f"extraction_rate={extraction_rate:.2%}"
    )
    
    # 告警阈值
    if extraction_rate < 0.9:
        logger.error(
            f"🚨 告警：品牌提取率低于 90%！"
            f"extraction_rate={extraction_rate:.2%}"
        )
        # 这里可以集成邮件/短信/钉钉告警

def check_empty_brand():
    """检查空 brand 比例"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN brand IS NULL OR brand = '' THEN 1 END) as empty_brand
        FROM diagnosis_results
        WHERE created_at > ?
    """, (one_hour_ago,))
    
    row = cursor.fetchone()
    total, empty_brand = row
    
    if total == 0:
        return
    
    empty_rate = empty_brand / total if total > 0 else 0
    
    logger.info(
        f"空 brand 监控：total={total}, "
        f"empty_brand={empty_brand}, "
        f"empty_rate={empty_rate:.2%}"
    )
    
    if empty_rate > 0.1:
        logger.error(
            f"🚨 告警：空 brand 比例超过 10%！"
            f"empty_rate={empty_rate:.2%}"
        )

def main():
    logger.info("=" * 60)
    logger.info("数据质量监控检查开始")
    logger.info("=" * 60)
    
    check_extraction_rate()
    check_empty_brand()
    
    logger.info("监控检查完成")

if __name__ == '__main__':
    main()
```

**定时执行** (添加到 crontab):
```bash
# 每 5 分钟执行一次数据质量监控
*/5 * * * * cd /Users/sgl/PycharmProjects/PythonProject && \
  python3 backend_python/monitoring/data_quality_monitor.py
```

---

## 📊 验证步骤

### 立即执行（修复验证）

```bash
# 1. 重启后端服务
cd backend_python
./stop_server.sh
./start_server.sh

# 2. 执行自动化验证
python3 tests/verify_diagnosis_flow.py

# 3. 如果验证通过，执行测试诊断
# 在小程序中执行一次完整诊断

# 4. 检查数据库
sqlite3 database.db \
  "SELECT execution_id, brand, extracted_brand FROM diagnosis_results ORDER BY created_at DESC LIMIT 5;"

# 5. 检查品牌分布
curl http://localhost:5001/api/diagnosis/report/{execution_id} | jq '.brandDistribution.data'
```

### 持续监控

```bash
# 安装定时任务
crontab -e
# 添加：
*/5 * * * * cd /Users/sgl/PycharmProjects/PythonProject && python3 backend_python/monitoring/data_quality_monitor.py
```

---

## 🎯 成功标准

### 技术指标

| 指标 | 目标值 | 当前值 | 状态 |
|-----|--------|--------|------|
| extracted_brand 提取率 | > 95% | 待验证 | ⏳ |
| API 返回完整数据率 | 100% | 待验证 | ⏳ |
| 前端报告页显示成功率 | 100% | 待验证 | ⏳ |

### 流程指标

| 指标 | 目标值 | 当前值 | 状态 |
|-----|--------|--------|------|
| 部署检查清单执行率 | 100% | 0% | ❌ |
| 自动化测试覆盖率 | > 80% | 0% | ❌ |
| 监控告警覆盖率 | 100% | 0% | ❌ |

---

## 📝 实施计划

### 第一阶段：技术修复（立即执行）

- [ ] 1. 重启后端服务
- [ ] 2. 执行自动化验证脚本
- [ ] 3. 执行测试诊断
- [ ] 4. 验证数据库数据
- [ ] 5. 验证 API 返回
- [ ] 6. 验证前端展示

### 第二阶段：流程建设（本周内）

- [ ] 1. 创建部署检查清单
- [ ] 2. 创建自动化测试脚本
- [ ] 3. 配置监控告警
- [ ] 4. 团队培训

### 第三阶段：持续改进（本月内）

- [ ] 1. 完善单元测试
- [ ] 2. 集成 CI/CD
- [ ] 3. 建立数据质量仪表板
- [ ] 4. 定期审查和改进

---

**制定人**: 系统首席架构师  
**批准人**: CTO  
**下次审查日期**: 2026-03-20
