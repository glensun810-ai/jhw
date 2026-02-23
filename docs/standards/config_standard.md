# 配置管理规范

**版本**: v1.0  
**生效日期**: 2026-02-23  
**状态**: ✅ 已实施

---

## 一、总则

### 1.1 目的

规范项目配置文件的管理，确保配置一致性、安全性和可维护性。

### 1.2 适用范围

适用于所有项目成员和所有环境（开发、测试、生产）。

### 1.3 核心原则

1. **唯一配置源**: 根目录 `.env` 是唯一配置源
2. **禁止复制**: 不要复制 `.env` 文件到其他目录
3. **符号链接**: 如需兼容，使用符号链接而非复制
4. **版本控制**: `.env` 已添加到 `.gitignore`，不要提交

---

## 二、配置文件结构

### 2.1 文件位置

```
PythonProject/
├── .env                           # 主配置（唯一配置源）
├── .env.example                   # 示例配置（提交）
└── backup/
    └── .env.backup                # 备份配置
```

### 2.2 符号链接

```bash
# 后端目录
backend_python/.env -> ../.env

# 脚本目录（如需）
scripts/.env -> ../.env
```

### 2.3 配置分类

```bash
# AI 平台 API Keys
ARK_API_KEY=xxx
DEEPSEEK_API_KEY=xxx

# 豆包多模型配置
DOUBAO_MODEL_PRIORITY_1=xxx
DOUBAO_AUTO_SELECT_MODEL=true

# 微信小程序配置
WECHAT_APP_ID=xxx
WECHAT_APP_SECRET=xxx

# 服务器配置
DEBUG=true
SECRET_KEY=xxx

# 数据库配置
DATABASE_PATH=database.db

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

---

## 三、配置加载规范

### 3.1 Python 后端

**标准加载方式**:
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

**配置读取**:
```python
import os

# 可选配置（有默认值）
debug = os.environ.get('DEBUG', 'false')

# 必需配置（无默认值）
api_key = os.environ.get('ARK_API_KEY')
if not api_key:
    raise ValueError("缺少必需的配置：ARK_API_KEY")
```

**使用配置类**:
```python
from config.settings import Config

# 获取 API Key
api_key = Config.get_api_key('doubao')

# 获取优先级模型
models = Config.get_doubao_priority_models()
```

### 3.2 JavaScript 前端

**标准加载方式**:
```javascript
// 从 utils/config.js 统一读取
const { API_ENDPOINTS, ENV_CONFIG } = require('./config');

// 获取 API 地址
const baseUrl = ENV_CONFIG.develop.baseURL;
```

---

## 四、配置管理流程

### 4.1 新增配置项

**流程**:
1. 在 `.env.example` 中添加示例
2. 在 `config/settings.py` 中添加读取逻辑
3. 更新本文档
4. 通知团队成员

**示例**:
```bash
# .env.example
# 新增 AI 平台
NEW_AI_API_KEY=your-api-key

# config/settings.py
NEW_AI_API_KEY = os.environ.get('NEW_AI_API_KEY', '')
```

### 4.2 修改配置

**流程**:
1. 编辑根目录 `.env`
2. 验证配置（运行测试）
3. 重启服务
4. 记录变更

**命令**:
```bash
# 编辑配置
vim .env

# 验证配置
python3 scripts/test_doubao.py

# 重启服务
pkill -f "python.*run.py"
cd backend_python && python3 run.py
```

### 4.3 配置备份

**定期备份**:
```bash
# 手动备份
cp .env backup/.env.backup.$(date +%Y%m%d)

# 自动备份（cron）
0 2 * * * cp /path/to/.env /path/to/backup/.env.backup.$(date +\%Y\%m\%d)
```

---

## 五、安全规范

### 5.1 敏感信息

**禁止提交**:
- API Keys
- 数据库密码
- 密钥
- Token

**允许提交**:
- 示例配置（`.env.example`）
- 配置模板
- 默认值（非敏感）

### 5.2 访问控制

**开发环境**:
- 仅限项目组成员
- 使用开发 API Key
- 限制访问 IP

**生产环境**:
- 仅限运维人员
- 使用生产 API Key
- 严格访问控制

### 5.3 密钥轮换

**周期**: 每 90 天

**流程**:
1. 生成新密钥
2. 更新 `.env`
3. 验证功能
4. 废弃旧密钥

---

## 六、故障排查

### 6.1 常见问题

**问题 1**: 配置加载失败

**症状**:
```
⚠️  未找到配置文件：/path/to/.env
```

**解决**:
```bash
# 检查文件是否存在
ls -la .env

# 检查符号链接
ls -la backend_python/.env

# 重新创建符号链接
cd backend_python
ln -s ../.env .env
```

**问题 2**: 配置项缺失

**症状**:
```
ValueError: 缺少必需的配置：ARK_API_KEY
```

**解决**:
```bash
# 编辑 .env
vim .env

# 添加缺失配置
ARK_API_KEY=your-api-key

# 重启服务
```

**问题 3**: 配置不一致

**症状**:
- 开发环境正常，生产环境失败
- 不同成员环境行为不一致

**解决**:
```bash
# 统一配置源
rm backend_python/.env
cd backend_python
ln -s ../.env .env

# 同步配置
cp .env.example .env
# 编辑填入真实配置
```

### 6.2 调试工具

**查看当前配置**:
```python
import os
print("ARK_API_KEY:", os.environ.get('ARK_API_KEY', '未设置')[:10] + '...')
```

**验证配置加载**:
```bash
python3 -c "from config.settings import Config; print(Config.get_api_key('doubao'))"
```

---

## 七、最佳实践

### 7.1 配置组织

**推荐**:
```bash
# 按功能分组
# AI 平台
ARK_API_KEY=xxx
DEEPSEEK_API_KEY=xxx

# 数据库
DATABASE_PATH=database.db

# 日志
LOG_LEVEL=INFO
```

**不推荐**:
```bash
# 杂乱无章
KEY1=xxx
DB=xxx
API=xxx
```

### 7.2 配置命名

**推荐**:
```bash
# 使用大写字母和下划线
ARK_API_KEY
DATABASE_PATH
```

**不推荐**:
```bash
# 小写或混合
arkApiKey
databasePath
```

### 7.3 默认值

**推荐**:
```python
# 提供合理的默认值
DEBUG = os.environ.get('DEBUG', 'false')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
```

**不推荐**:
```python
# 无默认值
DEBUG = os.environ.get('DEBUG')
```

---

## 八、附录

### 8.1 配置模板

```bash
# =============================================================================
# AI 平台 API Keys
# =============================================================================
ARK_API_KEY=your-doubao-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key
QWEN_API_KEY=your-qwen-api-key

# =============================================================================
# 豆包多模型配置
# =============================================================================
DOUBAO_MODEL_PRIORITY_1=doubao-seed-1-8-251228
DOUBAO_MODEL_PRIORITY_2=doubao-seed-2-0-mini-260215
DOUBAO_AUTO_SELECT_MODEL=true

# =============================================================================
# 微信小程序配置
# =============================================================================
WECHAT_APP_ID=your-app-id
WECHAT_APP_SECRET=your-app-secret

# =============================================================================
# 服务器配置
# =============================================================================
DEBUG=true
SECRET_KEY=your-secret-key
PORT=5000

# =============================================================================
# 数据库配置
# =============================================================================
DATABASE_PATH=database.db

# =============================================================================
# 日志配置
# =============================================================================
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### 8.2 相关文档

- [架构文档](../architecture/README.md)
- [代码规范](./code_standard.md)
- [部署指南](../deployment.md)

---

**文档生成时间**: 2026-02-23 15:15  
**维护人**: 首席全栈工程师 (AI)  
**审核状态**: ✅ 已通过
