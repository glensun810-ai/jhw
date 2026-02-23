🛡️ GEO 品牌诊断系统核心 API 规范 (v2.0)
1. 系统架构概述
本系统已升级为矩阵化诊断架构。其核心逻辑不再是单点问答，而是通过 TestCaseGenerator 产生 $[N \times M]$ 的测试矩阵（N个品牌，M个模型）。
三层流水线逻辑：
1. 感知层 (Adapter): 调用不同 AI 模型的 Provider。
2. 认知层 (Intelligence): 运行 evaluator.py (评分) 和 competitive_analyzer.py (竞争分析)。
3. 决策层 (Reporting): 汇总数据并生成归因报告。

2. 核心接口说明
🟢 POST /api/perform-brand-test
功能描述：提交品牌列表和模型列表，初始化自动化测试用例。
请求载荷 (Payload) 规范
字段	类型	必填	说明
brand_list	Array[String]	是	需要诊断的品牌名称列表
selectedModels	Array[String]	是	模型 ID 列表（如 ["doubao", "qwen"]）
custom_question	String	是	诊断的具体问题或场景描述
注意：前端若发送对象数组 [{id:'doubao', name:'豆包'}]，后端必须在入口处通过 AIAdapterFactory 的 ALIAS_MAP 进行平滑化处理。
错误码定义
* 400 (Bad Request): 字段缺失、类型不匹配或模型未注册。
* 401 (Unauthorized): Token 过期或无效。
* 500 (Internal Error): 后端子模块（如竞争分析器）导入或运行崩溃。

🔵 GET /api/test/status/{execution_id}
功能描述：轮询诊断进度及获取深度分析结果。
任务阶段 (stage) 流转定义
1. init: 任务已创建。
2. ai_fetching: AI 正在获取品牌原始数据。
3. intelligence_analyzing: 正在进行质量评估与竞争对手占位分析。
4. completed: 所有深度分析已存入 detailed_results。

3. 开发约束 (Coding Standards)
1. 响应完整性：所有失败请求必须包含 error 字段。严禁只返回 400 状态码。
2. 容错性：AIAdapterFactory 必须支持中英文双向映射（如 “豆包” 映射为 “doubao”）。
3. 数据安全：任何返回的 Payload 中不得包含敏感的 API_KEY 信息。
4. 异步友好：由于诊断任务涉及多模型调用，接口应立即返回 execution_id，禁止长连接阻塞。
