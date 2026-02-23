# AI 品牌诊断系统

**版本**: v3.0  
**更新日期**: 2026-02-23  
**状态**: ✅ 生产就绪

---

## 一、项目简介

基于微信小程序的 AI 品牌诊断系统，提供多平台 AI 模型调用、品牌分析、竞争情报等功能。

### 核心功能

- 🤖 **多 AI 平台支持**: 豆包、DeepSeek、通义千问、ChatGPT 等
- 📊 **品牌分析**: 多维度品牌评分和趋势分析
- 🔍 **竞争情报**: 竞品对比和拦截风险分析
- 📈 **实时进度**: 诊断进度实时推送
- 📱 **小程序**: 微信小程序前端

---

## 二、快速开始

### 2.1 环境要求

- Python 3.14+
- Node.js 14+
- 微信开发者工具 2.0+
- SQLite3

### 2.2 安装步骤

**1. 克隆项目**:
```bash
git clone <repo-url>
cd PythonProject
```

**2. 配置环境**:
```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 填入真实配置
vim .env
```

**3. 安装依赖**:
```bash
# 后端依赖
cd backend_python
pip3 install -r requirements.txt

# 前端依赖（微信小程序无需安装）
```

**4. 启动服务**:
```bash
# 后端服务
cd backend_python
python3 run.py

# 前端服务
# 使用微信开发者工具打开项目
```

**5. 验证安装**:
```bash
# 测试后端 API
curl http://127.0.0.1:5000/api/test

# 测试豆包 API
python3 scripts/test_doubao.py
```

---

## 三、项目结构

```
PythonProject/
├── .env                           # 主配置文件
├── .env.example                   # 示例配置
├── docs/                          # 文档中心
│   ├── architecture/              # 架构文档
│   ├── standards/                 # 规范文档
│   └── reports/                   # 报告归档
├── scripts/                       # 项目级脚本
│   ├── cleanup.sh                 # 清理脚本
│   └── test_doubao.py             # 豆包测试
├── backend_python/                # 后端代码
│   ├── config/                    # 配置管理
│   ├── src/                       # 源代码（新结构）
│   └── wechat_backend/            # 后端主模块
├── pages/                         # 小程序前端
├── services/                      # 前端服务
├── utils/                         # 前端工具
└── tests/                         # 测试
```

---

## 四、核心功能

### 4.1 品牌诊断

**流程**:
```
用户输入 → 前端验证 → API 调用 → 后端处理 → 
AI 调用 → 结果聚合 → 返回前端 → 展示结果
```

**使用示例**:
```javascript
// 前端调用
const { startBrandTestApi } = require('./api/home');

const result = await startBrandTestApi({
  brand_list: ['品牌 A'],
  selectedModels: [{ name: 'doubao', checked: true }],
  custom_question: '介绍一下品牌 A'
});
```

### 4.2 多模型优先级

**配置**:
```bash
# .env
DOUBAO_MODEL_PRIORITY_1=doubao-seed-1-8-251228
DOUBAO_MODEL_PRIORITY_2=doubao-seed-2-0-mini-260215
DOUBAO_AUTO_SELECT_MODEL=true
```

**功能**:
- 自动选择最高优先级可用模型
- 故障自动转移到下一个优先级
- 支持最多 10 个优先级模型

### 4.3 进度推送

**轮询机制**:
```javascript
// 前端轮询
const pollingController = createPollingController(
  executionId,
  (status) => {
    console.log(`进度：${status.progress}%`);
  },
  (result) => {
    console.log('诊断完成');
  }
);

pollingController.start(800, true);  // 800ms 间隔，立即执行
```

---

## 五、配置管理

### 5.1 核心配置

```bash
# AI 平台 API Keys
ARK_API_KEY=your-doubao-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key

# 豆包多模型配置
DOUBAO_MODEL_PRIORITY_1=doubao-seed-1-8-251228
DOUBAO_AUTO_SELECT_MODEL=true

# 微信小程序配置
WECHAT_APP_ID=your-app-id
WECHAT_APP_SECRET=your-app-secret

# 服务器配置
DEBUG=true
SECRET_KEY=your-secret-key
```

### 5.2 配置规范

详见：[配置管理规范](docs/standards/config_standard.md)

---

## 六、开发指南

### 6.1 代码规范

详见：[代码规范](docs/standards/code_standard.md)

### 6.2 架构文档

详见：[架构文档](docs/architecture/README.md)

### 6.3 测试

**运行测试**:
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

### 6.4 清理

**清理临时文件**:
```bash
./scripts/cleanup.sh
```

---

## 七、部署

### 7.1 开发环境

```bash
# 启动后端
cd backend_python
python3 run.py

# 前端使用微信开发者工具
```

### 7.2 生产环境

**要求**:
- 使用生产 API Key
- 关闭 DEBUG 模式
- 配置 HTTPS
- 设置防火墙

**部署步骤**:
```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2. 配置环境变量
export FLASK_ENV=production
export PORT=5000

# 3. 启动服务（使用 systemd 或 supervisor）
systemctl start ai-brand-diagnosis
```

---

## 八、故障排查

### 8.1 常见问题

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

**问题 2**: API 调用失败

**症状**:
```
API 调用失败：401 Unauthorized
```

**解决**:
```bash
# 检查 API Key 配置
grep ARK_API_KEY .env

# 验证配置
python3 scripts/test_doubao.py
```

**问题 3**: 导入错误

**症状**:
```
ImportError: cannot import name 'xxx'
```

**解决**:
```bash
# 清理编译文件
./scripts/cleanup.sh

# 重新安装依赖
pip3 install -r requirements.txt
```

### 8.2 日志查看

```bash
# 查看实时日志
tail -f logs/app.log

# 查看错误日志
grep ERROR logs/app.log

# 清理旧日志
find logs -name "*.log" -mtime +7 -delete
```

---

## 九、版本历史

| 版本 | 日期 | 说明 |
|-----|------|------|
| v3.0 | 2026-02-23 | 架构重构，新目录结构 |
| v2.6 | 2026-02-23 | 配置统一管理，豆包多模型优先级 |
| v2.0 | 2026-02-20 | 模块化重构 |
| v1.0 | 2026-02-15 | 初始版本 |

---

## 十、相关资源

### 10.1 文档

- [架构文档](docs/architecture/README.md)
- [配置规范](docs/standards/config_standard.md)
- [代码规范](docs/standards/code_standard.md)
- [部署指南](docs/deployment.md)

### 10.2 外部链接

- [微信小程序文档](https://developers.weixin.qq.com/miniprogram/dev/framework/)
- [Flask 文档](https://flask.palletsprojects.com/)
- [豆包 API 文档](https://www.volcengine.com/docs/82379)

---

## 十一、贡献指南

### 11.1 提交流程

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 11.2 代码审查

- 遵循代码规范
- 添加单元测试
- 更新文档
- 通过 CI/CD

---

## 十二、许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 十三、联系方式

- 项目地址：`<repo-url>`
- 问题反馈：`<issue-tracker>`
- 团队邮箱：`<team-email>`

---

**最后更新**: 2026-02-23  
**维护团队**: AI 品牌诊断系统团队
