# GEO 系统前后端接口测试计划

## 测试目标

根据《2026-02-14_GEO_System_Interface_Audit_Report.md》接口审计报告，对GEO系统所有前后端接口进行全面测试，验证接口功能、性能、安全性和兼容性。

## 测试范围

### 1. 认证相关接口
- POST `/api/login` - 微信登录
- POST `/api/validate-token` - 令牌验证
- POST `/api/refresh-token` - 令牌刷新
- POST `/api/send-verification-code` - 发送验证码
- POST `/api/register` - 用户注册

### 2. 品牌测试核心接口
- POST `/api/perform-brand-test` - 启动品牌测试
- GET `/api/test-progress` - 获取测试进度
- GET `/test/status/<task_id>` - 获取任务状态
- GET `/test/result/<task_id>` - 获取任务结果
- POST `/test/submit` - 提交测试任务

### 3. 数据同步接口
- POST `/api/sync-data` - 同步数据
- POST `/api/download-data` - 下载数据
- POST `/api/upload-result` - 上传结果
- POST `/api/delete-result` - 删除结果

### 4. 历史记录接口
- GET `/api/test-history` - 获取测试历史
- GET `/api/test-record/<record_id>` - 获取测试记录

### 5. 平台与配置接口
- GET `/api/ai-platforms` - AI平台列表
- GET `/api/platform-status` - 平台状态
- GET `/api/config` - 配置获取

### 6. 系统基础接口
- GET `/` - 首页/服务状态
- GET `/health` - 健康检查
- GET `/api/test` - 服务器连接测试

### 7. 高级功能接口
- POST `/action/recommendations` - 竞争分析与建议
- POST `/cruise/config` - 巡航任务配置
- GET `/cruise/tasks` - 巡航任务列表
- GET `/cruise/trends` - 趋势数据
- GET `/market/benchmark` - 市场基准
- GET `/predict/forecast` - 预测接口
- POST `/assets/optimization` - 资产优化
- GET `/hub/summary` - 枢纽摘要
- GET `/reports/executive` - 高管报告
- GET `/reports/pdf` - PDF报告
- POST/GET `/workflow/tasks` - 工作流任务

### 8. 信源与辅助接口
- GET `/api/source-intelligence` - 信源情报
- POST `/api/competitive-analysis` - 竞争分析
- POST `/api/send_message` - 发送消息
- GET `/api/access_token` - 获取访问令牌
- POST `/api/user_info` - 解密用户信息
- GET/POST `/api/user/profile` - 用户资料
- POST `/api/user/update` - 更新用户资料

### 9. FastAPI路由(GCO Validator)
- POST `/v1/test/brand-test` - 品牌测试
- GET `/v1/test/progress/{execution_id}` - 测试进度
- GET `/v1/test/history` - 测试历史
- GET `/v1/ai-platforms/` - AI平台列表
- GET `/v1/report/{execution_id}` - 测试报告

## 测试环境

### 后端服务
- 基础URL: `http://127.0.0.1:5000`
- Flask端口: 5000
- 健康检查端点: `/health`

### 前端配置
- 微信小程序开发环境
- 调试模式开启
- 网络请求超时: 30秒

## 测试执行顺序

### 第一阶段：基础连通性测试（优先级：P0）
1. 服务启动验证
2. 健康检查接口
3. 首页/基础状态接口
4. 服务器连接测试接口

### 第二阶段：认证接口测试（优先级：P0）
1. 微信登录接口
2. 令牌验证接口
3. 令牌刷新接口

### 第三阶段：核心业务流程测试（优先级：P0）
1. 品牌测试完整流程
2. 进度查询与轮询
3. 结果获取

### 第四阶段：数据管理接口测试（优先级：P1）
1. 数据同步
2. 历史记录查询
3. 结果上传/下载/删除

### 第五阶段：平台与配置接口测试（优先级：P1）
1. AI平台列表
2. 平台状态
3. 配置获取

### 第六阶段：高级功能接口测试（优先级：P2）
1. 竞争分析
2. 巡航任务
3. 报告生成

### 第七阶段：安全与性能测试（优先级：P1）
1. CORS配置验证
2. 限流机制
3. 认证保护
4. 输入验证

## 测试用例设计原则

### 1. 功能测试
- 正常场景：使用有效参数调用接口
- 异常场景：使用无效/缺失参数调用接口
- 边界场景：测试参数边界值

### 2. 性能测试
- 响应时间：记录每个接口的响应时间
- 并发测试：多请求同时发送
- 超时处理：测试超时场景

### 3. 安全测试
- 认证绕过：未认证访问受保护接口
- 输入注入：SQL注入、XSS测试
- 越权访问：访问其他用户数据

### 4. 兼容性测试
- 数据格式：JSON格式兼容性
- 字段缺失：处理缺失字段
- 类型兼容：不同数据类型处理

## 测试报告输出

每个接口测试完成后，记录以下信息：
1. 接口名称和路径
2. 测试时间
3. 请求参数
4. 响应状态码
5. 响应数据（脱敏后）
6. 响应时间
7. 测试结果（通过/失败）
8. 问题描述（如有）
9. 建议方案（如有）

## 测试工具

- Python requests库：HTTP请求
- pytest：测试框架
- unittest：单元测试
- time模块：性能计时

## 风险与注意事项

1. **数据安全**：测试过程中产生的真实数据需要脱敏处理
2. **服务稳定性**：测试可能导致服务负载增加，需监控
3. **外部依赖**：AI平台API调用可能失败，需有降级方案
4. **时间限制**：部分测试（如品牌测试）耗时较长，设置合理超时

## 测试时间表

| 阶段 | 预计时间 | 优先级 |
|------|---------|--------|
| 基础连通性 | 30分钟 | P0 |
| 认证接口 | 45分钟 | P0 |
| 核心业务流程 | 2小时 | P0 |
| 数据管理 | 1小时 | P1 |
| 平台与配置 | 30分钟 | P1 |
| 高级功能 | 1.5小时 | P2 |
| 安全与性能 | 1小时 | P1 |
| **总计** | **~7小时** | - |
