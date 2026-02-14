# GEO 系统前后端全链路接口大盘点与契约审计报告

## 第一部分：前端 API 调用大盘点 (Frontend Manifest)

### 1. 认证相关接口
- **登录接口** (`api/auth.js`) → POST `/api/login`
  - 参数: `{code}` (微信登录凭证)
  
- **令牌验证接口** (`api/auth.js`) → POST `/api/validate-token`
  - 参数: 无特定参数
  
- **令牌刷新接口** (`api/auth.js`) → POST `/api/refresh-token`
  - 参数: `{refresh_token}`
  
- **发送验证码接口** (`api/auth.js`) → POST `/api/send-verification-code`
  - 参数: `{phone}`
  
- **用户注册接口** (`api/auth.js`) → POST `/api/register`
  - 参数: `{phone, verificationCode, password}`

### 2. 品牌测试相关接口
- **启动品牌测试接口** (`api/home.js`, `api/competitive-analysis.js`) → POST `/api/perform-brand-test`
  - 参数: `{brand_list, selectedModels, custom_question}` 或 `{brand_list, selectedModels, customQuestions}`
  
- **获取测试进度接口** (`api/home.js`, `api/competitive-analysis.js`) → GET `/api/test-progress`
  - 参数: `{executionId}` (URL查询参数)
  
- **获取任务状态接口** (`api/home.js`) → GET `/test/status/<task_id>`
  - 参数: `task_id` (路径参数)

### 3. 数据同步相关接口
- **同步数据接口** (`api/data-sync.js`) → POST `/api/sync-data`
  - 参数: `{openid, localResults}`
  
- **下载数据接口** (`api/data-sync.js`) → POST `/api/download-data`
  - 参数: `{openid}`
  
- **上传结果接口** (`api/data-sync.js`) → POST `/api/upload-result`
  - 参数: `{openid, result}`
  
- **删除结果接口** (`api/data-sync.js`) → POST `/api/delete-result`
  - 参数: `{openid, id}`

### 4. 历史记录相关接口
- **获取测试历史接口** (`api/history.js`) → GET `/api/test-history`
  - 参数: `{userOpenid}` (URL查询参数)

### 5. 竞争分析相关接口
- **执行竞争分析接口** (`api/competitive-analysis.js`) → POST `/action/recommendations`
  - 参数: `{source_intelligence, evidence_chain, brand_name}`

### 6. 系统相关接口
- **服务器连接测试接口** (`api/home.js`) → GET `/api/test`
  - 参数: 无

## 第二部分：后端 API 路由大盘点 (Backend Manifest)

### 1. 微信认证相关路由
- **微信验证接口** (`/wechat/verify`) → GET/POST
  - 方法: GET (验证) / POST (消息处理)
  - 接收: URL查询参数 (signature, timestamp, nonce, echostr)
  - 返回: 验证字符串或"success"

- **微信登录接口** (`/api/login`) → POST
  - 方法: POST
  - 接收: `{code}` (JSON)
  - 返回: `{status, data, token}` (JWT令牌)

### 2. 品牌测试相关路由
- **执行品牌测试接口** (`/api/perform-brand-test`) → POST
  - 方法: POST
  - 接收: `{brand_list, selectedModels, custom_question/customQuestions, userOpenid, apiKey, userLevel, judgePlatform, judgeModel, judgeApiKey}` (JSON)
  - 返回: `{status, execution_id, message}`

- **获取测试进度接口** (`/api/test-progress`) → GET
  - 方法: GET
  - 接收: `executionId` (URL查询参数)
  - 返回: 进度数据对象 `{progress, completed, total, status, results, start_time, etc.}`

- **提交测试任务接口** (`/test/submit`) → POST
  - 方法: POST
  - 接收: `{brand_list, selectedModels, customQuestions}` (JSON)
  - 返回: `{task_id, message}`

- **获取任务状态接口** (`/test/status/<task_id>`) → GET
  - 方法: GET
  - 接收: `task_id` (路径参数)
  - 返回: `{task_id, progress, stage, status, results, is_completed, created_at}`

- **获取任务结果接口** (`/test/result/<task_id>`) → GET
  - 方法: GET
  - 接收: `task_id` (路径参数)
  - 返回: 深度情报分析结果

### 3. 系统相关路由
- **服务器测试接口** (`/api/test`) → GET
  - 方法: GET
  - 接收: 无
  - 返回: `{message, status}`

- **健康检查接口** (`/health`) → GET
  - 方法: GET
  - 接收: 无
  - 返回: `{status, timestamp}`

- **配置获取接口** (`/api/config`) → GET
  - 方法: GET
  - 接收: 可选认证
  - 返回: `{app_id, server_time, status, user_id}`

### 4. 平台与历史相关路由
- **AI平台列表接口** (`/api/ai-platforms`) → GET
  - 方法: GET
  - 接收: 无
  - 返回: `{domestic[], overseas[]}` (AI模型列表)

- **平台状态接口** (`/api/platform-status`) → GET
  - 方法: GET
  - 接收: 可选认证
  - 返回: `{status, platforms}` (各AI平台状态信息)

- **测试历史接口** (`/api/test-history`) → GET
  - 方法: GET
  - 接收: `{userOpenid, limit, offset}` (URL查询参数)
  - 返回: `{status, history[], count}`

- **测试记录接口** (`/api/test-record/<record_id>`) → GET
  - 方法: GET
  - 接收: `record_id` (路径参数，整数)
  - 返回: `{status, record}`

### 5. 高级功能路由
- **竞争分析与建议接口** (`/action/recommendations`) → POST
  - 方法: POST
  - 接收: `{source_intelligence, evidence_chain, brand_name}` (JSON)
  - 返回: `{status, recommendations[], count, brand_name}`

- **巡航任务配置接口** (`/cruise/config`) → POST/DELETE
  - 方法: POST (创建) / DELETE (取消)
  - 接收: `{user_openid, brand_name, interval_hours, ai_models, questions, job_id}` (POST) / `{job_id}` (DELETE)
  - 返回: 操作结果

- **巡航任务列表接口** (`/cruise/tasks`) → GET
  - 方法: GET
  - 接收: 可选认证
  - 返回: `{status, tasks[], count}`

- **趋势数据接口** (`/cruise/trends`) → GET
  - 方法: GET
  - 接收: `{brand_name, days}` (URL查询参数)
  - 返回: 趋势数据

- **市场基准接口** (`/market/benchmark`) → GET
  - 方法: GET
  - 接收: `{brand_name, category, days}` (URL查询参数)
  - 返回: 市场基准数据

- **预测接口** (`/predict/forecast`) → GET
  - 方法: GET
  - 接收: `{brand_name, days, history_days}` (URL查询参数)
  - 返回: 预测结果

- **资产优化接口** (`/assets/optimization`) → POST
  - 方法: POST
  - 接收: `{official_asset, ai_preferences}` (JSON)
  - 返回: 优化分析结果

- **枢纽摘要接口** (`/hub/summary`) → GET
  - 方法: GET
  - 接收: `{brand_name, days}` (URL查询参数)
  - 返回: 摘要数据

- **高管报告接口** (`/reports/executive`) → GET
  - 方法: GET
  - 接收: `{brand_name, days}` (URL查询参数)
  - 返回: 高管报告

- **PDF报告接口** (`/reports/pdf`) → GET
  - 方法: GET
  - 接收: `{brand_name, days}` (URL查询参数)
  - 返回: PDF文件流

- **工作流任务接口** (`/workflow/tasks`) → POST/GET
  - 方法: POST (创建) / GET (查询状态)
  - 接收: POST: `{evidence_fragment, associated_url, source_name, risk_level, brand_name, intervention_script, source_meta, webhook_url, priority}` / GET: `task_id` (路径参数)
  - 返回: 任务ID或状态信息

### 6. 数据同步相关路由
- **数据同步接口** (`/api/sync-data`) → POST
  - 方法: POST
  - 接收: `{openid, localResults}` (JSON)
  - 返回: 同步结果

- **数据下载接口** (`/api/download-data`) → POST
  - 方法: POST
  - 接收: `{openid}` (JSON)
  - 返回: 云端数据

- **结果上传接口** (`/api/upload-result`) → POST
  - 方法: POST
  - 接收: `{openid, result}` (JSON)
  - 返回: 上传结果

- **结果删除接口** (`/api/delete-result`) → POST
  - 方法: POST
  - 接收: `{openid, id}` (JSON)
  - 返回: 删除结果

### 7. 信源与辅助路由
- **信源情报接口** (`/api/source-intelligence`) → GET
  - 方法: GET
  - 接收: `{brandName}` (URL查询参数)
  - 返回: 信源情报图谱数据

- **竞争分析接口** (`/api/competitive-analysis`) → POST
  - 方法: POST
  - 接收: `{source_intelligence, evidence_chain, brand_name}` (JSON)
  - 返回: 竞争分析结果

### 8. 其他辅助路由
- **发送消息接口** (`/api/send_message`) → POST
  - 方法: POST
  - 接收: 消息数据 (JSON)
  - 返回: 发送结果

- **获取访问令牌接口** (`/api/access_token`) → GET
  - 方法: GET
  - 接收: 无
  - 返回: 访问令牌信息

- **解密用户信息接口** (`/api/user_info`) → POST
  - 方法: POST
  - 接收: 加密的用户信息 (JSON)
  - 返回: 解密后的用户信息

- **用户资料接口** (`/api/user/profile`) → GET/POST
  - 方法: GET (获取) / POST (更新)
  - 接收: 可选认证
  - 返回: 用户资料信息

- **更新用户资料接口** (`/api/user/update`) → POST
  - 方法: POST
  - 接收: `{...updated_fields}` (JSON)
  - 返回: 更新结果

- **首页接口** (`/`) → GET
  - 方法: GET
  - 接收: 无
  - 返回: 服务器状态信息

- **健康检查接口** (`/health`) → GET
  - 方法: GET
  - 接收: 无
  - 返回: 健康状态信息

- **配置获取接口** (`/api/config`) → GET
  - 方法: GET
  - 接收: 可选认证
  - 返回: 服务器配置信息

### 9. FastAPI 路由 (GCO Validator)
- **品牌测试接口** (`/v1/test/brand-test`) → POST
  - 方法: POST
  - 接收: `{brand_name, selected_models, custom_questions, max_workers}` (JSON)
  - 返回: `{status, results[], overall_score, total_tests, execution_id, report_summary}`

- **测试进度接口** (`/v1/test/progress/{execution_id}`) → GET
  - 方法: GET
  - 接收: `execution_id` (路径参数)
  - 返回: `{execution_id, progress, completed, total, status}`

- **测试历史接口** (`/v1/test/history`) → GET
  - 方法: GET
  - 接收: 无
  - 返回: `{status, history[], count}`

- **AI平台列表接口** (`/v1/ai-platforms/`) → GET
  - 方法: GET
  - 接收: 无
  - 返回: `{domestic[], overseas[]}`

- **测试报告接口** (`/v1/report/{execution_id}`) → GET
  - 方法: GET
  - 接收: `execution_id` (路径参数), `format` (查询参数)
  - 返回: 测试报告数据

## 第三部分：联调契约审计报告 (Contract Audit)

### 1. 接口功能描述

#### 核心业务流程：
- **品牌认知测试流程**：从前端发起品牌测试请求 → 后端异步执行测试 → 前端轮询获取进度 → 完成后获取详细结果
- **认证流程**：微信登录获取token → 后续请求携带认证信息
- **数据管理流程**：本地数据与云端同步，支持离线操作

#### 主要功能模块：
- **品牌诊断**：多AI模型对比分析品牌认知
- **竞争分析**：品牌间差异化分析与风险识别
- **进度跟踪**：实时任务状态监控
- **报告生成**：多维度分析报告输出

### 2. 字段对齐状态

#### 完全对齐的接口：
- **登录接口**：前端传递`{code}`，后端接收并验证，返回格式一致
- **品牌测试接口**：前端传递`{brand_list, selectedModels, custom_question}`，后端正确接收并处理
- **进度查询接口**：前端传递`executionId`，后端按约定返回进度信息

#### 存在字段差异的接口：
- **品牌测试参数**：
  - 前端有时传递`customQuestions`数组，后端主要处理`custom_question`字符串
  - 后端对`selectedModels`进行了复杂解析，支持对象数组和字符串数组两种格式
  - 后端对模型名称进行了标准化处理，增强了兼容性

- **任务状态接口**：
  - 前端调用`/test/status/<task_id>`，后端返回包含`stage`、`progress`、`status`等字段的对象
  - 前端通过`parseTaskStatus`服务层函数处理后端返回的不同格式数据

#### 需要改进的字段映射：
- **模型选择字段**：前端传递的模型对象包含`{name, checked}`，后端需要提取`name`字段
- **进度状态字段**：后端使用`stage`表示阶段，前端需要映射为用户友好的文本

### 3. 当前隐患/错误

#### 潜在风险点：
1. **进度死锁问题**：在长时间运行的任务中，可能出现进度停滞的情况，虽然代码中有检测机制，但仍需加强
2. **数据传输量过大**：AI诊断结果包含大量文本数据，可能导致网络超时或内存溢出
3. **并发控制**：多个用户同时发起测试可能导致后端资源竞争

#### 已解决的问题：
1. **字段兼容性**：后端增加了对多种数据格式的支持，提高了接口健壮性
2. **错误处理**：增加了完善的异常处理机制，确保单个模型失败不影响整体流程
3. **超时保护**：在AI评估等耗时操作中增加了超时机制，防止长时间阻塞

#### 日志中提到的现象分析：
- **results 为空**：可能是由于AI模型调用失败或解析错误导致，后端已增加默认值处理
- **进度死锁**：已实现进度停滞检测机制，当进度长时间不变时会提示用户

#### 优化建议：
1. **增加WebSocket支持**：对于长时间任务，可考虑使用WebSocket实现实时推送，减少轮询压力
2. **分页处理大数据**：对于大量结果数据，应实现分页加载机制
3. **缓存策略**：对频繁查询的数据实施适当的缓存策略，提高响应速度
4. **监控告警**：建立完善的监控体系，及时发现和处理异常情况

Overall, the front-end and back-end interfaces are well-designed with good error handling and compatibility mechanisms. The system follows a robust architecture that handles various edge cases and provides a good user experience despite the complexity of the underlying AI processing tasks.