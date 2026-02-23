# 项目架构文档

**版本**: v3.0  
**更新日期**: 2026-02-23  
**状态**: ✅ 已更新

---

## 一、项目概述

### 1.1 项目简介

本项目是一个基于微信小程序的 AI 品牌诊断系统，提供多平台 AI 模型调用、品牌分析、竞争情报等功能。

### 1.2 技术栈

**后端**:
- Python 3.14+
- Flask 2.3+
- 多 AI 平台适配器（豆包、DeepSeek、通义千问等）

**前端**:
- 微信小程序
- 原生 JavaScript

**数据库**:
- SQLite3

---

## 二、目录结构

### 2.1 项目根目录

```
PythonProject/
├── .env                           # 主配置文件（唯一配置源）
├── .env.example                   # 示例配置
├── .gitignore                     # Git 忽略规则
├── README.md                      # 项目总览
├── docs/                          # 文档中心
│   ├── architecture/              # 架构文档
│   ├── api/                       # API 文档
│   ├── config/                    # 配置文档
│   ├── reports/                   # 报告归档
│   └── standards/                 # 规范文档
├── scripts/                       # 项目级脚本
│   ├── cleanup.sh                 # 清理脚本
│   └── test_doubao.py             # 豆包测试脚本
├── backend_python/                # 后端代码
├── pages/                         # 小程序前端
├── services/                      # 前端服务
├── utils/                         # 前端工具
└── tests/                         # 前端测试
```

### 2.2 后端目录结构

```
backend_python/
├── .env -> ../.env                # 符号链接（指向根目录）
├── run.py                         # 启动入口
├── requirements.txt               # 依赖管理
├── config/                        # 配置管理
│   ├── __init__.py
│   └── settings.py                # 配置设置
├── src/                           # 源代码（新结构）
│   ├── adapters/                  # AI 适配器
│   │   ├── __init__.py
│   │   ├── doubao_adapter.py
│   │   ├── doubao_priority_adapter.py
│   │   └── ...
│   ├── api/                       # API 路由（待迁移）
│   ├── services/                  # 业务服务（待迁移）
│   ├── models/                    # 数据模型（待迁移）
│   └── utils/                     # 内部工具（待迁移）
├── tests/                         # 测试目录
│   ├── test_adapters/
│   ├── test_api/
│   └── test_services/
└── wechat_backend/                # 旧结构（向后兼容）
    ├── ai_adapters/               # AI 适配器（旧）
    └── views/                     # 视图文件
```

### 2.3 前端目录结构

```
pages/
├── index/                         # 首页
│   ├── index.js
│   ├── index.wxml
│   ├── index.wxss
│   └── index.json
├── results/                       # 结果页
└── ...

services/                          # 前端服务
utils/                             # 前端工具
components/                        # 组件
tests/                             # 前端测试
```

---

## 三、配置管理

### 3.1 配置文件位置

**唯一配置源**: 项目根目录 `.env`

```bash
# 根目录
.env                              # 主配置（真实配置，不提交）
.env.example                      # 示例配置（提交）

# 其他目录使用符号链接
backend_python/.env -> ../.env
```

### 3.2 配置加载

**Python 后端**:
```python
from pathlib import Path
from dotenv import load_dotenv

# 获取项目根目录
root_dir = Path(__file__).parent.parent.parent
env_file = root_dir / '.env'

# 加载配置
if env_file.exists():
    load_dotenv(env_file)
```

**JavaScript 前端**:
```javascript
// 从 utils/config.js 统一读取
const { API_ENDPOINTS, ENV_CONFIG } = require('./config');
```

### 3.3 核心配置项

```bash
# AI 平台 API Keys
ARK_API_KEY=your-doubao-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key
QWEN_API_KEY=your-qwen-api-key

# 豆包多模型优先级
DOUBAO_MODEL_PRIORITY_1=doubao-seed-1-8-251228
DOUBAO_MODEL_PRIORITY_2=doubao-seed-2-0-mini-260215
DOUBAO_AUTO_SELECT_MODEL=true

# 微信小程序配置
WECHAT_APP_ID=your-app-id
WECHAT_APP_SECRET=your-app-secret

# 服务器配置
DEBUG=true
SECRET_KEY=your-secret-key
```

---

## 四、核心模块

### 4.1 AI 适配器模块

**位置**: `src/adapters/`

**功能**: 提供多个 AI 平台的统一接口

**主要类**:
- `AIClient` - 基础适配器
- `DoubaoAdapter` - 豆包适配器
- `DoubaoPriorityAdapter` - 豆包优先级适配器（支持多模型自动选择）
- `DeepSeekAdapter` - DeepSeek 适配器
- `AIAdapterFactory` - 适配器工厂

**使用示例**:
```python
from src.adapters import AIAdapterFactory

# 创建适配器
adapter = AIAdapterFactory.create('doubao', api_key)

# 发送请求
response = adapter.send_prompt(prompt="你好")
```

### 4.2 配置模块

**位置**: `config/`

**功能**: 统一管理项目配置

**主要类**:
- `Config` - 配置类
- `get_config()` - 获取配置（可选）
- `get_required_config()` - 获取配置（必需）

**使用示例**:
```python
from config.settings import Config

# 获取 API Key
api_key = Config.get_api_key('doubao')

# 获取优先级模型
models = Config.get_doubao_priority_models()
```

### 4.3 视图模块

**位置**: `wechat_backend/views/`（旧结构）

**功能**: 提供 API 路由

**主要路由**:
- `/api/perform-brand-test` - 品牌诊断
- `/api/test-progress` - 进度查询
- `/test/status/<id>` - 状态查询

---

## 五、数据流

### 5.1 品牌诊断流程

```
用户输入
    ↓
前端验证 (pages/index/index.js)
    ↓
API 调用 (api/home.js)
    ↓
后端路由 (wechat_backend/views/diagnosis_views.py)
    ↓
NxM 执行引擎 (wechat_backend/nxm_execution_engine.py)
    ↓
AI 适配器 (src/adapters/)
    ↓
AI 平台 API
    ↓
结果聚合
    ↓
返回前端
    ↓
展示结果 (pages/results/results.js)
```

### 5.2 配置加载流程

```
应用启动
    ↓
run.py 加载 .env
    ↓
load_dotenv()
    ↓
环境变量设置
    ↓
Config 类读取
    ↓
应用使用配置
```

---

## 六、测试策略

### 6.1 测试目录

```
tests/
├── test_adapters/                 # 适配器测试
├── test_api/                      # API 测试
└── test_services/                 # 服务测试
```

### 6.2 测试脚本

**项目级测试**:
- `scripts/test_doubao.py` - 豆包综合测试

**后端测试**:
- `tests/test_*.py` - 各种功能测试

**前端测试**:
- `tests/test-*.js` - 前端单元测试

### 6.3 运行测试

```bash
# 豆包测试
python3 scripts/test_doubao.py

# 后端测试
cd backend_python
python3 -m pytest tests/

# 前端测试
cd tests
node run-tests.js
```

---

## 七、部署指南

### 7.1 环境准备

```bash
# 安装依赖
cd backend_python
pip3 install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入真实配置
```

### 7.2 启动服务

```bash
# 后端服务
cd backend_python
python3 run.py

# 前端服务
# 使用微信开发者工具打开项目
```

### 7.3 健康检查

```bash
# 测试后端 API
curl http://127.0.0.1:5000/api/test

# 测试豆包 API
python3 scripts/test_doubao.py
```

---

## 八、维护指南

### 8.1 清理脚本

```bash
# 清理临时文件和编译文件
./scripts/cleanup.sh
```

### 8.2 日志管理

```bash
# 查看日志
tail -f logs/app.log

# 清理旧日志（7 天前）
find logs -name "*.log" -mtime +7 -delete
```

### 8.3 备份策略

```bash
# 备份配置文件
cp .env backup/.env.backup

# 备份代码
git commit -am "备份：xxx"
```

---

## 九、版本历史

| 版本 | 日期 | 说明 |
|-----|------|------|
| v3.0 | 2026-02-23 | 架构重构，新目录结构 |
| v2.6 | 2026-02-23 | 配置统一管理 |
| v2.0 | 2026-02-20 | 模块化重构 |
| v1.0 | 2026-02-15 | 初始版本 |

---

**文档生成时间**: 2026-02-23 15:00  
**维护人**: 首席全栈工程师 (AI)  
**审核状态**: ✅ 已通过
