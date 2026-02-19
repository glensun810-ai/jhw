(.venv) sgl@SunGuolongdeMacBook-Pro backend_python % find /Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters -name "*.py" -exec grep -l "utils" {} \;
/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py
/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py
/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py
/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py
(.venv) sgl@SunGuolongdeMacBook-Pro backend_python % cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python run.py
Logging initialized with level: INFO, file: logs/app.log
2026-02-15 16:22:19,496 - wechat_backend.database - INFO - database.py:17 - init_db() - Initializing database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:22:19,497 - wechat_backend.database - INFO - database.py:112 - init_db() - Database initialization completed
2026-02-15 16:22:19,498 - wechat_backend.database - INFO - models.py:125 - init_task_status_db() - Initializing task status database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:22:19,498 - wechat_backend.database - INFO - models.py:181 - init_task_status_db() - Task status database initialization completed
2026-02-15 16:22:19,517 - wechat_backend.api - INFO - factory.py:8 - <module>() - === Starting AI Adapter Imports ===
2026-02-15 16:22:19,521 - wechat_backend.api - ERROR - factory.py:15 - <module>() - Failed to import DeepSeekAdapter: attempted relative import beyond top-level package
2026-02-15 16:22:19,522 - wechat_backend.api - ERROR - factory.py:17 - <module>() - Traceback for DeepSeekAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 12, in <module>
    from .deepseek_adapter import DeepSeekAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py", line 6, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:22:19,522 - wechat_backend.api - INFO - factory.py:22 - <module>() - Successfully imported DeepSeekR1Adapter
2026-02-15 16:22:19,522 - wechat_backend.api - ERROR - factory.py:33 - <module>() - Failed to import QwenAdapter: attempted relative import beyond top-level package
2026-02-15 16:22:19,523 - wechat_backend.api - ERROR - factory.py:35 - <module>() - Traceback for QwenAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 30, in <module>
    from .qwen_adapter import QwenAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:22:19,526 - wechat_backend.api - ERROR - factory.py:42 - <module>() - Failed to import DoubaoAdapter: attempted relative import beyond top-level package
2026-02-15 16:22:19,527 - wechat_backend.api - ERROR - factory.py:44 - <module>() - Traceback for DoubaoAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 39, in <module>
    from .doubao_adapter import DoubaoAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py", line 17, in <module>
    from ...utils.debug_manager import ai_io_log, exception_log, debug_log
ImportError: attempted relative import beyond top-level package

2026-02-15 16:22:19,527 - wechat_backend.api - INFO - factory.py:49 - <module>() - Successfully imported ChatGPTAdapter
2026-02-15 16:22:19,527 - wechat_backend.api - INFO - factory.py:58 - <module>() - Successfully imported GeminiAdapter
2026-02-15 16:22:19,528 - wechat_backend.api - ERROR - factory.py:69 - <module>() - Failed to import ZhipuAdapter: attempted relative import beyond top-level package
2026-02-15 16:22:19,528 - wechat_backend.api - ERROR - factory.py:71 - <module>() - Traceback for ZhipuAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 66, in <module>
    from .zhipu_adapter import ZhipuAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:22:19,528 - wechat_backend.api - INFO - factory.py:76 - <module>() - Successfully imported ErnieBotAdapter
2026-02-15 16:22:19,528 - wechat_backend.api - INFO - factory.py:83 - <module>() - === Completed AI Adapter Imports ===
2026-02-15 16:22:19,528 - wechat_backend.api - INFO - factory.py:218 - <module>() - === Adapter Registration Debug Info ===
2026-02-15 16:22:19,528 - wechat_backend.api - INFO - factory.py:219 - <module>() - DeepSeekAdapter status: False
2026-02-15 16:22:19,528 - wechat_backend.api - INFO - factory.py:220 - <module>() - DeepSeekR1Adapter status: True
2026-02-15 16:22:19,528 - wechat_backend.api - INFO - factory.py:221 - <module>() - QwenAdapter status: False
2026-02-15 16:22:19,528 - wechat_backend.api - INFO - factory.py:222 - <module>() - DoubaoAdapter status: False
2026-02-15 16:22:19,528 - wechat_backend.api - INFO - factory.py:223 - <module>() - ChatGPTAdapter status: True
2026-02-15 16:22:19,528 - wechat_backend.api - INFO - factory.py:224 - <module>() - GeminiAdapter status: True
2026-02-15 16:22:19,529 - wechat_backend.api - INFO - factory.py:225 - <module>() - ZhipuAdapter status: False
2026-02-15 16:22:19,529 - wechat_backend.api - INFO - factory.py:226 - <module>() - ErnieBotAdapter status: True
2026-02-15 16:22:19,529 - wechat_backend.api - WARNING - factory.py:233 - <module>() - NOT registering DeepSeekAdapter - it is None or failed to import
2026-02-15 16:22:19,529 - wechat_backend.api - INFO - factory.py:236 - <module>() - Registering DeepSeekR1Adapter
2026-02-15 16:22:19,529 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for deepseekr1
2026-02-15 16:22:19,529 - wechat_backend.api - WARNING - factory.py:245 - <module>() - NOT registering QwenAdapter - it is None or failed to import
2026-02-15 16:22:19,529 - wechat_backend.api - WARNING - factory.py:251 - <module>() - NOT registering DoubaoAdapter - it is None or failed to import
2026-02-15 16:22:19,529 - wechat_backend.api - INFO - factory.py:254 - <module>() - Registering ChatGPTAdapter
2026-02-15 16:22:19,529 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for chatgpt
2026-02-15 16:22:19,529 - wechat_backend.api - INFO - factory.py:260 - <module>() - Registering GeminiAdapter
2026-02-15 16:22:19,529 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for gemini
2026-02-15 16:22:19,529 - wechat_backend.api - WARNING - factory.py:269 - <module>() - NOT registering ZhipuAdapter - it is None or failed to import
2026-02-15 16:22:19,529 - wechat_backend.api - INFO - factory.py:272 - <module>() - Registering ErnieBotAdapter
2026-02-15 16:22:19,529 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for wenxin
2026-02-15 16:22:19,529 - wechat_backend.api - INFO - factory.py:278 - <module>() - Final registered models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:22:19,529 - wechat_backend.api - INFO - factory.py:279 - <module>() - === End Adapter Registration Debug Info ===
2026-02-15 16:22:19,529 - wechat_backend.api - INFO - factory.py:282 - <module>() - Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:22:19,531 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: doubao
2026-02-15 16:22:19,531 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: deepseek
2026-02-15 16:22:19,531 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: qwen
2026-02-15 16:22:19,531 - wechat_backend.api - INFO - provider_factory.py:73 - <module>() - ProviderFactory initialized with default providers
2026-02-15 16:22:21,742 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:22:21,743 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:22:21,744 - wechat_backend.api - INFO - circuit_breaker.py:77 - __init__() - CircuitBreaker 'webhook_dispatcher' initialized: threshold=3, recovery_timeout=30s, expected_exceptions=8
[2026-02-15 16:22:21.744] [GEO-DEBUG][WORKFLOW_MANAGER] Starting background processor thread
[2026-02-15 16:22:21.744] [GEO-DEBUG][WORKFLOW_MANAGER] Starting retry processor thread
2026-02-15 16:22:21,744 - wechat_backend.api - INFO - semantic_analyzer.py:22 - __init__() - SemanticAnalyzer initialized
Building prefix dict from /Users/sgl/PycharmProjects/PythonProject/.venv/lib/python3.14/site-packages/jieba/dict.txt ...
Loading model from cache /var/folders/m8/9lzgk90s02z276bclcvcvkg40000gn/T/jieba.cache
Loading model cost 0.4286367893218994 seconds.
Prefix dict has been built succesfully.
2026-02-15 16:22:22,175 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:22:22,176 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:22:22,177 - wechat_backend.api - INFO - workflow_manager.py:175 - _start_background_processor() - Workflow background processor started
2026-02-15 16:22:22,178 - wechat_backend.api - INFO - workflow_manager.py:208 - _start_retry_processor() - Workflow retry processor started
2026-02-15 16:22:22,185 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_error_rate
2026-02-15 16:22:22,185 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: slow_response_time
2026-02-15 16:22:22,185 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_request_frequency
2026-02-15 16:22:22,185 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_security_events
2026-02-15 16:22:22,185 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: service_down
✓ 监控系统配置完成
✓ 已配置 5 个告警规则
2026-02-15 16:22:22,185 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:204 - start_monitoring() - 告警监控已启动
✓ 监控系统初始化完成
✓ 所有API端点现在都受到监控保护
✓ 告警系统已启动
2026-02-15 16:22:22,186 - wechat_backend.api - INFO - app.py:149 - warm_up_adapters() - Starting adapter warm-up...
🚀 Starting WeChat Backend API server on port 5000
🔧 Debug mode: on
2026-02-15 16:22:22,186 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
📝 Log file: logs/app.log
2026-02-15 16:22:22,186 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter doubao warm-up failed: No adapter registered for platform: AIPlatformType.DOUBAO
2026-02-15 16:22:22,187 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:22:22,187 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter deepseek warm-up failed: No adapter registered for platform: AIPlatformType.DEEPSEEK
2026-02-15 16:22:22,187 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:22:22,187 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter qwen warm-up failed: No adapter registered for platform: AIPlatformType.QWEN
2026-02-15 16:22:22,187 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter chatgpt has no API key configured, skipping warm-up
2026-02-15 16:22:22,187 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter gemini has no API key configured, skipping warm-up
2026-02-15 16:22:22,187 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:22:22,187 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter zhipu warm-up failed: No adapter registered for platform: AIPlatformType.ZHIPU
2026-02-15 16:22:22,188 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter wenxin has no API key configured, skipping warm-up
 * Serving Flask app 'wechat_backend.app'
2026-02-15 16:22:22,189 - wechat_backend.api - INFO - app.py:178 - warm_up_adapters() - Adapter warm-up completed
 * Debug mode: on
Address already in use
Port 5000 is in use by another program. Either identify and stop that program, or start the server with a different port.
On macOS, try searching for and disabling 'AirPlay Receiver' in System Settings.
(.venv) sgl@SunGuolongdeMacBook-Pro backend_python % cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python run.py
Logging initialized with level: INFO, file: logs/app.log
2026-02-15 16:24:25,346 - wechat_backend.database - INFO - database.py:17 - init_db() - Initializing database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:24:25,346 - wechat_backend.database - INFO - database.py:112 - init_db() - Database initialization completed
2026-02-15 16:24:25,347 - wechat_backend.database - INFO - models.py:125 - init_task_status_db() - Initializing task status database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:24:25,347 - wechat_backend.database - INFO - models.py:181 - init_task_status_db() - Task status database initialization completed
2026-02-15 16:24:25,369 - wechat_backend.api - INFO - factory.py:8 - <module>() - === Starting AI Adapter Imports ===
2026-02-15 16:24:25,373 - wechat_backend.api - ERROR - factory.py:15 - <module>() - Failed to import DeepSeekAdapter: attempted relative import beyond top-level package
2026-02-15 16:24:25,374 - wechat_backend.api - ERROR - factory.py:17 - <module>() - Traceback for DeepSeekAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 12, in <module>
    from .deepseek_adapter import DeepSeekAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py", line 6, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:24:25,374 - wechat_backend.api - INFO - factory.py:22 - <module>() - Successfully imported DeepSeekR1Adapter
2026-02-15 16:24:25,375 - wechat_backend.api - ERROR - factory.py:33 - <module>() - Failed to import QwenAdapter: attempted relative import beyond top-level package
2026-02-15 16:24:25,375 - wechat_backend.api - ERROR - factory.py:35 - <module>() - Traceback for QwenAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 30, in <module>
    from .qwen_adapter import QwenAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:24:25,379 - wechat_backend.api - ERROR - factory.py:42 - <module>() - Failed to import DoubaoAdapter: attempted relative import beyond top-level package
2026-02-15 16:24:25,380 - wechat_backend.api - ERROR - factory.py:44 - <module>() - Traceback for DoubaoAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 39, in <module>
    from .doubao_adapter import DoubaoAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py", line 17, in <module>
    from ...utils.debug_manager import ai_io_log, exception_log, debug_log
ImportError: attempted relative import beyond top-level package

2026-02-15 16:24:25,380 - wechat_backend.api - INFO - factory.py:49 - <module>() - Successfully imported ChatGPTAdapter
2026-02-15 16:24:25,381 - wechat_backend.api - INFO - factory.py:58 - <module>() - Successfully imported GeminiAdapter
2026-02-15 16:24:25,381 - wechat_backend.api - ERROR - factory.py:69 - <module>() - Failed to import ZhipuAdapter: attempted relative import beyond top-level package
2026-02-15 16:24:25,382 - wechat_backend.api - ERROR - factory.py:71 - <module>() - Traceback for ZhipuAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 66, in <module>
    from .zhipu_adapter import ZhipuAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:24:25,382 - wechat_backend.api - INFO - factory.py:76 - <module>() - Successfully imported ErnieBotAdapter
2026-02-15 16:24:25,382 - wechat_backend.api - INFO - factory.py:83 - <module>() - === Completed AI Adapter Imports ===
2026-02-15 16:24:25,382 - wechat_backend.api - INFO - factory.py:218 - <module>() - === Adapter Registration Debug Info ===
2026-02-15 16:24:25,382 - wechat_backend.api - INFO - factory.py:219 - <module>() - DeepSeekAdapter status: False
2026-02-15 16:24:25,382 - wechat_backend.api - INFO - factory.py:220 - <module>() - DeepSeekR1Adapter status: True
2026-02-15 16:24:25,383 - wechat_backend.api - INFO - factory.py:221 - <module>() - QwenAdapter status: False
2026-02-15 16:24:25,383 - wechat_backend.api - INFO - factory.py:222 - <module>() - DoubaoAdapter status: False
2026-02-15 16:24:25,383 - wechat_backend.api - INFO - factory.py:223 - <module>() - ChatGPTAdapter status: True
2026-02-15 16:24:25,383 - wechat_backend.api - INFO - factory.py:224 - <module>() - GeminiAdapter status: True
2026-02-15 16:24:25,383 - wechat_backend.api - INFO - factory.py:225 - <module>() - ZhipuAdapter status: False
2026-02-15 16:24:25,383 - wechat_backend.api - INFO - factory.py:226 - <module>() - ErnieBotAdapter status: True
2026-02-15 16:24:25,383 - wechat_backend.api - WARNING - factory.py:233 - <module>() - NOT registering DeepSeekAdapter - it is None or failed to import
2026-02-15 16:24:25,383 - wechat_backend.api - INFO - factory.py:236 - <module>() - Registering DeepSeekR1Adapter
2026-02-15 16:24:25,383 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for deepseekr1
2026-02-15 16:24:25,383 - wechat_backend.api - WARNING - factory.py:245 - <module>() - NOT registering QwenAdapter - it is None or failed to import
2026-02-15 16:24:25,383 - wechat_backend.api - WARNING - factory.py:251 - <module>() - NOT registering DoubaoAdapter - it is None or failed to import
2026-02-15 16:24:25,384 - wechat_backend.api - INFO - factory.py:254 - <module>() - Registering ChatGPTAdapter
2026-02-15 16:24:25,384 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for chatgpt
2026-02-15 16:24:25,384 - wechat_backend.api - INFO - factory.py:260 - <module>() - Registering GeminiAdapter
2026-02-15 16:24:25,384 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for gemini
2026-02-15 16:24:25,384 - wechat_backend.api - WARNING - factory.py:269 - <module>() - NOT registering ZhipuAdapter - it is None or failed to import
2026-02-15 16:24:25,384 - wechat_backend.api - INFO - factory.py:272 - <module>() - Registering ErnieBotAdapter
2026-02-15 16:24:25,384 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for wenxin
2026-02-15 16:24:25,384 - wechat_backend.api - INFO - factory.py:278 - <module>() - Final registered models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:24:25,384 - wechat_backend.api - INFO - factory.py:279 - <module>() - === End Adapter Registration Debug Info ===
2026-02-15 16:24:25,384 - wechat_backend.api - INFO - factory.py:282 - <module>() - Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:24:25,387 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: doubao
2026-02-15 16:24:25,387 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: deepseek
2026-02-15 16:24:25,387 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: qwen
2026-02-15 16:24:25,387 - wechat_backend.api - INFO - provider_factory.py:73 - <module>() - ProviderFactory initialized with default providers
2026-02-15 16:24:27,443 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:24:27,444 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:24:27,444 - wechat_backend.api - INFO - circuit_breaker.py:77 - __init__() - CircuitBreaker 'webhook_dispatcher' initialized: threshold=3, recovery_timeout=30s, expected_exceptions=8
[2026-02-15 16:24:27.444] [GEO-DEBUG][WORKFLOW_MANAGER] Starting background processor thread
[2026-02-15 16:24:27.444] [GEO-DEBUG][WORKFLOW_MANAGER] Starting retry processor thread
2026-02-15 16:24:27,445 - wechat_backend.api - INFO - semantic_analyzer.py:22 - __init__() - SemanticAnalyzer initialized
Building prefix dict from /Users/sgl/PycharmProjects/PythonProject/.venv/lib/python3.14/site-packages/jieba/dict.txt ...
Loading model from cache /var/folders/m8/9lzgk90s02z276bclcvcvkg40000gn/T/jieba.cache
Loading model cost 0.44931507110595703 seconds.
Prefix dict has been built succesfully.
2026-02-15 16:24:27,896 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:24:27,897 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:24:27,899 - wechat_backend.api - INFO - workflow_manager.py:175 - _start_background_processor() - Workflow background processor started
2026-02-15 16:24:27,899 - wechat_backend.api - INFO - workflow_manager.py:208 - _start_retry_processor() - Workflow retry processor started
2026-02-15 16:24:27,906 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_error_rate
2026-02-15 16:24:27,906 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: slow_response_time
2026-02-15 16:24:27,906 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_request_frequency
2026-02-15 16:24:27,906 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_security_events
2026-02-15 16:24:27,906 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: service_down
✓ 监控系统配置完成
✓ 已配置 5 个告警规则
2026-02-15 16:24:27,907 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:204 - start_monitoring() - 告警监控已启动
✓ 监控系统初始化完成
✓ 所有API端点现在都受到监控保护
✓ 告警系统已启动
2026-02-15 16:24:27,907 - wechat_backend.api - INFO - app.py:149 - warm_up_adapters() - Starting adapter warm-up...
🚀 Starting WeChat Backend API server on port 5000
🔧 Debug mode: on
📝 Log file: logs/app.log
2026-02-15 16:24:27,908 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:24:27,908 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter doubao warm-up failed: No adapter registered for platform: AIPlatformType.DOUBAO
2026-02-15 16:24:27,908 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:24:27,908 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter deepseek warm-up failed: No adapter registered for platform: AIPlatformType.DEEPSEEK
2026-02-15 16:24:27,908 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:24:27,908 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter qwen warm-up failed: No adapter registered for platform: AIPlatformType.QWEN
2026-02-15 16:24:27,908 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter chatgpt has no API key configured, skipping warm-up
2026-02-15 16:24:27,909 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter gemini has no API key configured, skipping warm-up
2026-02-15 16:24:27,909 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:24:27,909 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter zhipu warm-up failed: No adapter registered for platform: AIPlatformType.ZHIPU
2026-02-15 16:24:27,910 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter wenxin has no API key configured, skipping warm-up
 * Serving Flask app 'wechat_backend.app'
2026-02-15 16:24:27,910 - wechat_backend.api - INFO - app.py:178 - warm_up_adapters() - Adapter warm-up completed
 * Debug mode: on
2026-02-15 16:24:27,939 - werkzeug - INFO - _internal.py:97 - _log() - WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
2026-02-15 16:24:27,939 - werkzeug - INFO - _internal.py:97 - _log() - Press CTRL+C to quit
2026-02-15 16:24:27,940 - werkzeug - INFO - _internal.py:97 - _log() -  * Restarting with stat
Logging initialized with level: INFO, file: logs/app.log
2026-02-15 16:24:28,063 - wechat_backend.database - INFO - database.py:17 - init_db() - Initializing database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:24:28,064 - wechat_backend.database - INFO - database.py:112 - init_db() - Database initialization completed
2026-02-15 16:24:28,064 - wechat_backend.database - INFO - models.py:125 - init_task_status_db() - Initializing task status database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:24:28,064 - wechat_backend.database - INFO - models.py:181 - init_task_status_db() - Task status database initialization completed
2026-02-15 16:24:28,081 - wechat_backend.api - INFO - factory.py:8 - <module>() - === Starting AI Adapter Imports ===
2026-02-15 16:24:28,083 - wechat_backend.api - ERROR - factory.py:15 - <module>() - Failed to import DeepSeekAdapter: attempted relative import beyond top-level package
2026-02-15 16:24:28,083 - wechat_backend.api - ERROR - factory.py:17 - <module>() - Traceback for DeepSeekAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 12, in <module>
    from .deepseek_adapter import DeepSeekAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py", line 6, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:24:28,084 - wechat_backend.api - INFO - factory.py:22 - <module>() - Successfully imported DeepSeekR1Adapter
2026-02-15 16:24:28,084 - wechat_backend.api - ERROR - factory.py:33 - <module>() - Failed to import QwenAdapter: attempted relative import beyond top-level package
2026-02-15 16:24:28,084 - wechat_backend.api - ERROR - factory.py:35 - <module>() - Traceback for QwenAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 30, in <module>
    from .qwen_adapter import QwenAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:24:28,086 - wechat_backend.api - ERROR - factory.py:42 - <module>() - Failed to import DoubaoAdapter: attempted relative import beyond top-level package
2026-02-15 16:24:28,087 - wechat_backend.api - ERROR - factory.py:44 - <module>() - Traceback for DoubaoAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 39, in <module>
    from .doubao_adapter import DoubaoAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py", line 17, in <module>
    from ...utils.debug_manager import ai_io_log, exception_log, debug_log
ImportError: attempted relative import beyond top-level package

2026-02-15 16:24:28,087 - wechat_backend.api - INFO - factory.py:49 - <module>() - Successfully imported ChatGPTAdapter
2026-02-15 16:24:28,087 - wechat_backend.api - INFO - factory.py:58 - <module>() - Successfully imported GeminiAdapter
2026-02-15 16:24:28,087 - wechat_backend.api - ERROR - factory.py:69 - <module>() - Failed to import ZhipuAdapter: attempted relative import beyond top-level package
2026-02-15 16:24:28,087 - wechat_backend.api - ERROR - factory.py:71 - <module>() - Traceback for ZhipuAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 66, in <module>
    from .zhipu_adapter import ZhipuAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:24:28,087 - wechat_backend.api - INFO - factory.py:76 - <module>() - Successfully imported ErnieBotAdapter
2026-02-15 16:24:28,087 - wechat_backend.api - INFO - factory.py:83 - <module>() - === Completed AI Adapter Imports ===
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:218 - <module>() - === Adapter Registration Debug Info ===
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:219 - <module>() - DeepSeekAdapter status: False
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:220 - <module>() - DeepSeekR1Adapter status: True
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:221 - <module>() - QwenAdapter status: False
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:222 - <module>() - DoubaoAdapter status: False
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:223 - <module>() - ChatGPTAdapter status: True
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:224 - <module>() - GeminiAdapter status: True
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:225 - <module>() - ZhipuAdapter status: False
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:226 - <module>() - ErnieBotAdapter status: True
2026-02-15 16:24:28,088 - wechat_backend.api - WARNING - factory.py:233 - <module>() - NOT registering DeepSeekAdapter - it is None or failed to import
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:236 - <module>() - Registering DeepSeekR1Adapter
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for deepseekr1
2026-02-15 16:24:28,088 - wechat_backend.api - WARNING - factory.py:245 - <module>() - NOT registering QwenAdapter - it is None or failed to import
2026-02-15 16:24:28,088 - wechat_backend.api - WARNING - factory.py:251 - <module>() - NOT registering DoubaoAdapter - it is None or failed to import
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:254 - <module>() - Registering ChatGPTAdapter
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for chatgpt
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:260 - <module>() - Registering GeminiAdapter
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for gemini
2026-02-15 16:24:28,088 - wechat_backend.api - WARNING - factory.py:269 - <module>() - NOT registering ZhipuAdapter - it is None or failed to import
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:272 - <module>() - Registering ErnieBotAdapter
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for wenxin
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:278 - <module>() - Final registered models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:279 - <module>() - === End Adapter Registration Debug Info ===
2026-02-15 16:24:28,088 - wechat_backend.api - INFO - factory.py:282 - <module>() - Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:24:28,089 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: doubao
2026-02-15 16:24:28,089 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: deepseek
2026-02-15 16:24:28,089 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: qwen
2026-02-15 16:24:28,089 - wechat_backend.api - INFO - provider_factory.py:73 - <module>() - ProviderFactory initialized with default providers
2026-02-15 16:24:29,975 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:24:29,976 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:24:29,977 - wechat_backend.api - INFO - circuit_breaker.py:77 - __init__() - CircuitBreaker 'webhook_dispatcher' initialized: threshold=3, recovery_timeout=30s, expected_exceptions=8
[2026-02-15 16:24:29.977] [GEO-DEBUG][WORKFLOW_MANAGER] Starting background processor thread
[2026-02-15 16:24:29.977] [GEO-DEBUG][WORKFLOW_MANAGER] Starting retry processor thread
2026-02-15 16:24:29,977 - wechat_backend.api - INFO - semantic_analyzer.py:22 - __init__() - SemanticAnalyzer initialized
Building prefix dict from /Users/sgl/PycharmProjects/PythonProject/.venv/lib/python3.14/site-packages/jieba/dict.txt ...
Loading model from cache /var/folders/m8/9lzgk90s02z276bclcvcvkg40000gn/T/jieba.cache
Loading model cost 0.4434511661529541 seconds.
Prefix dict has been built succesfully.
2026-02-15 16:24:30,423 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:24:30,424 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:24:30,425 - wechat_backend.api - INFO - workflow_manager.py:175 - _start_background_processor() - Workflow background processor started
2026-02-15 16:24:30,426 - wechat_backend.api - INFO - workflow_manager.py:208 - _start_retry_processor() - Workflow retry processor started
2026-02-15 16:24:30,433 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_error_rate
2026-02-15 16:24:30,433 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: slow_response_time
2026-02-15 16:24:30,433 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_request_frequency
2026-02-15 16:24:30,433 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_security_events
2026-02-15 16:24:30,433 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: service_down
✓ 监控系统配置完成
✓ 已配置 5 个告警规则
2026-02-15 16:24:30,433 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:204 - start_monitoring() - 告警监控已启动
✓ 监控系统初始化完成
✓ 所有API端点现在都受到监控保护
✓ 告警系统已启动
2026-02-15 16:24:30,433 - wechat_backend.api - INFO - app.py:149 - warm_up_adapters() - Starting adapter warm-up...
🚀 Starting WeChat Backend API server on port 5000
2026-02-15 16:24:30,434 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:24:30,434 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter doubao warm-up failed: No adapter registered for platform: AIPlatformType.DOUBAO
🔧 Debug mode: on
📝 Log file: logs/app.log
2026-02-15 16:24:30,434 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:24:30,434 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter deepseek warm-up failed: No adapter registered for platform: AIPlatformType.DEEPSEEK
2026-02-15 16:24:30,434 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:24:30,434 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter qwen warm-up failed: No adapter registered for platform: AIPlatformType.QWEN
2026-02-15 16:24:30,434 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter chatgpt has no API key configured, skipping warm-up
2026-02-15 16:24:30,435 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter gemini has no API key configured, skipping warm-up
2026-02-15 16:24:30,435 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:24:30,435 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter zhipu warm-up failed: No adapter registered for platform: AIPlatformType.ZHIPU
2026-02-15 16:24:30,435 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter wenxin has no API key configured, skipping warm-up
2026-02-15 16:24:30,435 - wechat_backend.api - INFO - app.py:178 - warm_up_adapters() - Adapter warm-up completed
2026-02-15 16:24:30,456 - werkzeug - WARNING - _internal.py:97 - _log() -  * Debugger is active!
2026-02-15 16:24:30,477 - werkzeug - INFO - _internal.py:97 - _log() -  * Debugger PIN: 884-445-834
2026-02-15 16:26:56,554 - werkzeug - INFO - _internal.py:97 - _log() -  * Detected change in '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py', reloading
2026-02-15 16:26:57,613 - werkzeug - INFO - _internal.py:97 - _log() -  * Restarting with stat
Logging initialized with level: INFO, file: logs/app.log
2026-02-15 16:26:57,858 - wechat_backend.database - INFO - database.py:17 - init_db() - Initializing database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:26:57,858 - wechat_backend.database - INFO - database.py:112 - init_db() - Database initialization completed
2026-02-15 16:26:57,859 - wechat_backend.database - INFO - models.py:125 - init_task_status_db() - Initializing task status database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:26:57,860 - wechat_backend.database - INFO - models.py:181 - init_task_status_db() - Task status database initialization completed
2026-02-15 16:26:57,886 - wechat_backend.api - INFO - factory.py:8 - <module>() - === Starting AI Adapter Imports ===
2026-02-15 16:26:57,892 - wechat_backend.api - ERROR - factory.py:15 - <module>() - Failed to import DeepSeekAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:26:57,896 - wechat_backend.api - ERROR - factory.py:17 - <module>() - Traceback for DeepSeekAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 12, in <module>
    from .deepseek_adapter import DeepSeekAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py", line 6, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:26:57,897 - wechat_backend.api - INFO - factory.py:22 - <module>() - Successfully imported DeepSeekR1Adapter
2026-02-15 16:26:57,898 - wechat_backend.api - ERROR - factory.py:33 - <module>() - Failed to import QwenAdapter: attempted relative import beyond top-level package
2026-02-15 16:26:57,898 - wechat_backend.api - ERROR - factory.py:35 - <module>() - Traceback for QwenAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 30, in <module>
    from .qwen_adapter import QwenAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:26:57,903 - wechat_backend.api - ERROR - factory.py:42 - <module>() - Failed to import DoubaoAdapter: attempted relative import beyond top-level package
2026-02-15 16:26:57,904 - wechat_backend.api - ERROR - factory.py:44 - <module>() - Traceback for DoubaoAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 39, in <module>
    from .doubao_adapter import DoubaoAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py", line 17, in <module>
    from ...utils.debug_manager import ai_io_log, exception_log, debug_log
ImportError: attempted relative import beyond top-level package

2026-02-15 16:26:57,904 - wechat_backend.api - INFO - factory.py:49 - <module>() - Successfully imported ChatGPTAdapter
2026-02-15 16:26:57,905 - wechat_backend.api - INFO - factory.py:58 - <module>() - Successfully imported GeminiAdapter
2026-02-15 16:26:57,906 - wechat_backend.api - ERROR - factory.py:69 - <module>() - Failed to import ZhipuAdapter: attempted relative import beyond top-level package
2026-02-15 16:26:57,906 - wechat_backend.api - ERROR - factory.py:71 - <module>() - Traceback for ZhipuAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 66, in <module>
    from .zhipu_adapter import ZhipuAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:26:57,907 - wechat_backend.api - INFO - factory.py:76 - <module>() - Successfully imported ErnieBotAdapter
2026-02-15 16:26:57,907 - wechat_backend.api - INFO - factory.py:83 - <module>() - === Completed AI Adapter Imports ===
2026-02-15 16:26:57,907 - wechat_backend.api - INFO - factory.py:218 - <module>() - === Adapter Registration Debug Info ===
2026-02-15 16:26:57,907 - wechat_backend.api - INFO - factory.py:219 - <module>() - DeepSeekAdapter status: False
2026-02-15 16:26:57,907 - wechat_backend.api - INFO - factory.py:220 - <module>() - DeepSeekR1Adapter status: True
2026-02-15 16:26:57,907 - wechat_backend.api - INFO - factory.py:221 - <module>() - QwenAdapter status: False
2026-02-15 16:26:57,907 - wechat_backend.api - INFO - factory.py:222 - <module>() - DoubaoAdapter status: False
2026-02-15 16:26:57,907 - wechat_backend.api - INFO - factory.py:223 - <module>() - ChatGPTAdapter status: True
2026-02-15 16:26:57,907 - wechat_backend.api - INFO - factory.py:224 - <module>() - GeminiAdapter status: True
2026-02-15 16:26:57,907 - wechat_backend.api - INFO - factory.py:225 - <module>() - ZhipuAdapter status: False
2026-02-15 16:26:57,907 - wechat_backend.api - INFO - factory.py:226 - <module>() - ErnieBotAdapter status: True
2026-02-15 16:26:57,907 - wechat_backend.api - WARNING - factory.py:233 - <module>() - NOT registering DeepSeekAdapter - it is None or failed to import
2026-02-15 16:26:57,907 - wechat_backend.api - INFO - factory.py:236 - <module>() - Registering DeepSeekR1Adapter
2026-02-15 16:26:57,908 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for deepseekr1
2026-02-15 16:26:57,908 - wechat_backend.api - WARNING - factory.py:245 - <module>() - NOT registering QwenAdapter - it is None or failed to import
2026-02-15 16:26:57,908 - wechat_backend.api - WARNING - factory.py:251 - <module>() - NOT registering DoubaoAdapter - it is None or failed to import
2026-02-15 16:26:57,908 - wechat_backend.api - INFO - factory.py:254 - <module>() - Registering ChatGPTAdapter
2026-02-15 16:26:57,908 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for chatgpt
2026-02-15 16:26:57,908 - wechat_backend.api - INFO - factory.py:260 - <module>() - Registering GeminiAdapter
2026-02-15 16:26:57,908 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for gemini
2026-02-15 16:26:57,908 - wechat_backend.api - WARNING - factory.py:269 - <module>() - NOT registering ZhipuAdapter - it is None or failed to import
2026-02-15 16:26:57,908 - wechat_backend.api - INFO - factory.py:272 - <module>() - Registering ErnieBotAdapter
2026-02-15 16:26:57,908 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for wenxin
2026-02-15 16:26:57,908 - wechat_backend.api - INFO - factory.py:278 - <module>() - Final registered models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:26:57,908 - wechat_backend.api - INFO - factory.py:279 - <module>() - === End Adapter Registration Debug Info ===
2026-02-15 16:26:57,908 - wechat_backend.api - INFO - factory.py:282 - <module>() - Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:26:57,913 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: doubao
2026-02-15 16:26:57,913 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: deepseek
2026-02-15 16:26:57,913 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: qwen
2026-02-15 16:26:57,913 - wechat_backend.api - INFO - provider_factory.py:73 - <module>() - ProviderFactory initialized with default providers
2026-02-15 16:27:00,229 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:27:00,230 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:27:00,231 - wechat_backend.api - INFO - circuit_breaker.py:77 - __init__() - CircuitBreaker 'webhook_dispatcher' initialized: threshold=3, recovery_timeout=30s, expected_exceptions=8
[2026-02-15 16:27:00.232] [GEO-DEBUG][WORKFLOW_MANAGER] Starting background processor thread
[2026-02-15 16:27:00.232] [GEO-DEBUG][WORKFLOW_MANAGER] Starting retry processor thread
2026-02-15 16:27:00,232 - wechat_backend.api - INFO - semantic_analyzer.py:22 - __init__() - SemanticAnalyzer initialized
Building prefix dict from /Users/sgl/PycharmProjects/PythonProject/.venv/lib/python3.14/site-packages/jieba/dict.txt ...
Loading model from cache /var/folders/m8/9lzgk90s02z276bclcvcvkg40000gn/T/jieba.cache
Loading model cost 0.4396650791168213 seconds.
Prefix dict has been built succesfully.
2026-02-15 16:27:00,673 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:27:00,674 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:27:00,676 - wechat_backend.api - INFO - workflow_manager.py:175 - _start_background_processor() - Workflow background processor started
2026-02-15 16:27:00,677 - wechat_backend.api - INFO - workflow_manager.py:208 - _start_retry_processor() - Workflow retry processor started
2026-02-15 16:27:00,686 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_error_rate
2026-02-15 16:27:00,686 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: slow_response_time
2026-02-15 16:27:00,686 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_request_frequency
2026-02-15 16:27:00,686 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_security_events
2026-02-15 16:27:00,686 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: service_down
✓ 监控系统配置完成
✓ 已配置 5 个告警规则
2026-02-15 16:27:00,686 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:204 - start_monitoring() - 告警监控已启动
✓ 监控系统初始化完成
✓ 所有API端点现在都受到监控保护
✓ 告警系统已启动
2026-02-15 16:27:00,686 - wechat_backend.api - INFO - app.py:149 - warm_up_adapters() - Starting adapter warm-up...
🚀 Starting WeChat Backend API server on port 5000
🔧 Debug mode: on
📝 Log file: logs/app.log
2026-02-15 16:27:00,687 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:00,687 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter doubao warm-up failed: No adapter registered for platform: AIPlatformType.DOUBAO
2026-02-15 16:27:00,687 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:00,687 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter deepseek warm-up failed: No adapter registered for platform: AIPlatformType.DEEPSEEK
2026-02-15 16:27:00,687 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:00,687 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter qwen warm-up failed: No adapter registered for platform: AIPlatformType.QWEN
2026-02-15 16:27:00,688 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter chatgpt has no API key configured, skipping warm-up
2026-02-15 16:27:00,688 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter gemini has no API key configured, skipping warm-up
2026-02-15 16:27:00,688 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:00,688 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter zhipu warm-up failed: No adapter registered for platform: AIPlatformType.ZHIPU
2026-02-15 16:27:00,688 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter wenxin has no API key configured, skipping warm-up
2026-02-15 16:27:00,688 - wechat_backend.api - INFO - app.py:178 - warm_up_adapters() - Adapter warm-up completed
2026-02-15 16:27:00,713 - werkzeug - WARNING - _internal.py:97 - _log() -  * Debugger is active!
2026-02-15 16:27:00,732 - werkzeug - INFO - _internal.py:97 - _log() -  * Debugger PIN: 884-445-834
2026-02-15 16:27:04,883 - werkzeug - INFO - _internal.py:97 - _log() -  * Detected change in '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py', reloading
2026-02-15 16:27:05,797 - werkzeug - INFO - _internal.py:97 - _log() -  * Restarting with stat
Logging initialized with level: INFO, file: logs/app.log
2026-02-15 16:27:05,950 - wechat_backend.database - INFO - database.py:17 - init_db() - Initializing database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:27:05,951 - wechat_backend.database - INFO - database.py:112 - init_db() - Database initialization completed
2026-02-15 16:27:05,951 - wechat_backend.database - INFO - models.py:125 - init_task_status_db() - Initializing task status database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:27:05,951 - wechat_backend.database - INFO - models.py:181 - init_task_status_db() - Task status database initialization completed
2026-02-15 16:27:05,969 - wechat_backend.api - INFO - factory.py:8 - <module>() - === Starting AI Adapter Imports ===
2026-02-15 16:27:05,973 - wechat_backend.api - ERROR - factory.py:15 - <module>() - Failed to import DeepSeekAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:27:05,974 - wechat_backend.api - ERROR - factory.py:17 - <module>() - Traceback for DeepSeekAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 12, in <module>
    from .deepseek_adapter import DeepSeekAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py", line 6, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:27:05,974 - wechat_backend.api - INFO - factory.py:22 - <module>() - Successfully imported DeepSeekR1Adapter
2026-02-15 16:27:05,974 - wechat_backend.api - ERROR - factory.py:33 - <module>() - Failed to import QwenAdapter: attempted relative import beyond top-level package
2026-02-15 16:27:05,975 - wechat_backend.api - ERROR - factory.py:35 - <module>() - Traceback for QwenAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 30, in <module>
    from .qwen_adapter import QwenAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:27:05,978 - wechat_backend.api - ERROR - factory.py:42 - <module>() - Failed to import DoubaoAdapter: attempted relative import beyond top-level package
2026-02-15 16:27:05,978 - wechat_backend.api - ERROR - factory.py:44 - <module>() - Traceback for DoubaoAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 39, in <module>
    from .doubao_adapter import DoubaoAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py", line 17, in <module>
    from ...utils.debug_manager import ai_io_log, exception_log, debug_log
ImportError: attempted relative import beyond top-level package

2026-02-15 16:27:05,979 - wechat_backend.api - INFO - factory.py:49 - <module>() - Successfully imported ChatGPTAdapter
2026-02-15 16:27:05,979 - wechat_backend.api - INFO - factory.py:58 - <module>() - Successfully imported GeminiAdapter
2026-02-15 16:27:05,979 - wechat_backend.api - ERROR - factory.py:69 - <module>() - Failed to import ZhipuAdapter: attempted relative import beyond top-level package
2026-02-15 16:27:05,980 - wechat_backend.api - ERROR - factory.py:71 - <module>() - Traceback for ZhipuAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 66, in <module>
    from .zhipu_adapter import ZhipuAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:76 - <module>() - Successfully imported ErnieBotAdapter
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:83 - <module>() - === Completed AI Adapter Imports ===
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:218 - <module>() - === Adapter Registration Debug Info ===
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:219 - <module>() - DeepSeekAdapter status: False
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:220 - <module>() - DeepSeekR1Adapter status: True
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:221 - <module>() - QwenAdapter status: False
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:222 - <module>() - DoubaoAdapter status: False
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:223 - <module>() - ChatGPTAdapter status: True
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:224 - <module>() - GeminiAdapter status: True
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:225 - <module>() - ZhipuAdapter status: False
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:226 - <module>() - ErnieBotAdapter status: True
2026-02-15 16:27:05,980 - wechat_backend.api - WARNING - factory.py:233 - <module>() - NOT registering DeepSeekAdapter - it is None or failed to import
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:236 - <module>() - Registering DeepSeekR1Adapter
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for deepseekr1
2026-02-15 16:27:05,980 - wechat_backend.api - WARNING - factory.py:245 - <module>() - NOT registering QwenAdapter - it is None or failed to import
2026-02-15 16:27:05,980 - wechat_backend.api - WARNING - factory.py:251 - <module>() - NOT registering DoubaoAdapter - it is None or failed to import
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:254 - <module>() - Registering ChatGPTAdapter
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for chatgpt
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:260 - <module>() - Registering GeminiAdapter
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for gemini
2026-02-15 16:27:05,980 - wechat_backend.api - WARNING - factory.py:269 - <module>() - NOT registering ZhipuAdapter - it is None or failed to import
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:272 - <module>() - Registering ErnieBotAdapter
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for wenxin
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:278 - <module>() - Final registered models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:279 - <module>() - === End Adapter Registration Debug Info ===
2026-02-15 16:27:05,980 - wechat_backend.api - INFO - factory.py:282 - <module>() - Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:27:05,982 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: doubao
2026-02-15 16:27:05,982 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: deepseek
2026-02-15 16:27:05,982 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: qwen
2026-02-15 16:27:05,982 - wechat_backend.api - INFO - provider_factory.py:73 - <module>() - ProviderFactory initialized with default providers
2026-02-15 16:27:07,966 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:27:07,967 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:27:07,968 - wechat_backend.api - INFO - circuit_breaker.py:77 - __init__() - CircuitBreaker 'webhook_dispatcher' initialized: threshold=3, recovery_timeout=30s, expected_exceptions=8
[2026-02-15 16:27:07.968] [GEO-DEBUG][WORKFLOW_MANAGER] Starting background processor thread
[2026-02-15 16:27:07.968] [GEO-DEBUG][WORKFLOW_MANAGER] Starting retry processor thread
2026-02-15 16:27:07,968 - wechat_backend.api - INFO - semantic_analyzer.py:22 - __init__() - SemanticAnalyzer initialized
Building prefix dict from /Users/sgl/PycharmProjects/PythonProject/.venv/lib/python3.14/site-packages/jieba/dict.txt ...
Loading model from cache /var/folders/m8/9lzgk90s02z276bclcvcvkg40000gn/T/jieba.cache
Loading model cost 0.43491029739379883 seconds.
Prefix dict has been built succesfully.
2026-02-15 16:27:08,405 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:27:08,406 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:27:08,408 - wechat_backend.api - INFO - workflow_manager.py:175 - _start_background_processor() - Workflow background processor started
2026-02-15 16:27:08,408 - wechat_backend.api - INFO - workflow_manager.py:208 - _start_retry_processor() - Workflow retry processor started
2026-02-15 16:27:08,416 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_error_rate
2026-02-15 16:27:08,417 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: slow_response_time
2026-02-15 16:27:08,417 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_request_frequency
2026-02-15 16:27:08,417 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_security_events
2026-02-15 16:27:08,417 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: service_down
✓ 监控系统配置完成
✓ 已配置 5 个告警规则
2026-02-15 16:27:08,417 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:204 - start_monitoring() - 告警监控已启动
✓ 监控系统初始化完成
✓ 所有API端点现在都受到监控保护
✓ 告警系统已启动
2026-02-15 16:27:08,417 - wechat_backend.api - INFO - app.py:149 - warm_up_adapters() - Starting adapter warm-up...
🚀 Starting WeChat Backend API server on port 5000
🔧 Debug mode: on
📝 Log file: logs/app.log
2026-02-15 16:27:08,418 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:08,418 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter doubao warm-up failed: No adapter registered for platform: AIPlatformType.DOUBAO
2026-02-15 16:27:08,418 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:08,418 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter deepseek warm-up failed: No adapter registered for platform: AIPlatformType.DEEPSEEK
2026-02-15 16:27:08,419 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:08,419 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter qwen warm-up failed: No adapter registered for platform: AIPlatformType.QWEN
2026-02-15 16:27:08,419 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter chatgpt has no API key configured, skipping warm-up
2026-02-15 16:27:08,419 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter gemini has no API key configured, skipping warm-up
2026-02-15 16:27:08,420 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:08,420 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter zhipu warm-up failed: No adapter registered for platform: AIPlatformType.ZHIPU
2026-02-15 16:27:08,420 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter wenxin has no API key configured, skipping warm-up
2026-02-15 16:27:08,420 - wechat_backend.api - INFO - app.py:178 - warm_up_adapters() - Adapter warm-up completed
2026-02-15 16:27:08,442 - werkzeug - WARNING - _internal.py:97 - _log() -  * Debugger is active!
2026-02-15 16:27:08,460 - werkzeug - INFO - _internal.py:97 - _log() -  * Debugger PIN: 884-445-834
2026-02-15 16:27:17,756 - werkzeug - INFO - _internal.py:97 - _log() -  * Detected change in '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py', reloading
2026-02-15 16:27:18,519 - werkzeug - INFO - _internal.py:97 - _log() -  * Restarting with stat
Logging initialized with level: INFO, file: logs/app.log
2026-02-15 16:27:18,711 - wechat_backend.database - INFO - database.py:17 - init_db() - Initializing database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:27:18,712 - wechat_backend.database - INFO - database.py:112 - init_db() - Database initialization completed
2026-02-15 16:27:18,712 - wechat_backend.database - INFO - models.py:125 - init_task_status_db() - Initializing task status database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:27:18,712 - wechat_backend.database - INFO - models.py:181 - init_task_status_db() - Task status database initialization completed
2026-02-15 16:27:18,735 - wechat_backend.api - INFO - factory.py:8 - <module>() - === Starting AI Adapter Imports ===
2026-02-15 16:27:18,739 - wechat_backend.api - ERROR - factory.py:15 - <module>() - Failed to import DeepSeekAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:27:18,739 - wechat_backend.api - ERROR - factory.py:17 - <module>() - Traceback for DeepSeekAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 12, in <module>
    from .deepseek_adapter import DeepSeekAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py", line 6, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:27:18,740 - wechat_backend.api - INFO - factory.py:22 - <module>() - Successfully imported DeepSeekR1Adapter
2026-02-15 16:27:18,742 - wechat_backend.api - ERROR - factory.py:33 - <module>() - Failed to import QwenAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:27:18,742 - wechat_backend.api - ERROR - factory.py:35 - <module>() - Traceback for QwenAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 30, in <module>
    from .qwen_adapter import QwenAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py", line 10, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:27:18,746 - wechat_backend.api - ERROR - factory.py:42 - <module>() - Failed to import DoubaoAdapter: attempted relative import beyond top-level package
2026-02-15 16:27:18,746 - wechat_backend.api - ERROR - factory.py:44 - <module>() - Traceback for DoubaoAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 39, in <module>
    from .doubao_adapter import DoubaoAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py", line 17, in <module>
    from ...utils.debug_manager import ai_io_log, exception_log, debug_log
ImportError: attempted relative import beyond top-level package

2026-02-15 16:27:18,747 - wechat_backend.api - INFO - factory.py:49 - <module>() - Successfully imported ChatGPTAdapter
2026-02-15 16:27:18,747 - wechat_backend.api - INFO - factory.py:58 - <module>() - Successfully imported GeminiAdapter
2026-02-15 16:27:18,748 - wechat_backend.api - ERROR - factory.py:69 - <module>() - Failed to import ZhipuAdapter: attempted relative import beyond top-level package
2026-02-15 16:27:18,748 - wechat_backend.api - ERROR - factory.py:71 - <module>() - Traceback for ZhipuAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 66, in <module>
    from .zhipu_adapter import ZhipuAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:27:18,748 - wechat_backend.api - INFO - factory.py:76 - <module>() - Successfully imported ErnieBotAdapter
2026-02-15 16:27:18,748 - wechat_backend.api - INFO - factory.py:83 - <module>() - === Completed AI Adapter Imports ===
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:218 - <module>() - === Adapter Registration Debug Info ===
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:219 - <module>() - DeepSeekAdapter status: False
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:220 - <module>() - DeepSeekR1Adapter status: True
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:221 - <module>() - QwenAdapter status: False
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:222 - <module>() - DoubaoAdapter status: False
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:223 - <module>() - ChatGPTAdapter status: True
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:224 - <module>() - GeminiAdapter status: True
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:225 - <module>() - ZhipuAdapter status: False
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:226 - <module>() - ErnieBotAdapter status: True
2026-02-15 16:27:18,749 - wechat_backend.api - WARNING - factory.py:233 - <module>() - NOT registering DeepSeekAdapter - it is None or failed to import
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:236 - <module>() - Registering DeepSeekR1Adapter
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for deepseekr1
2026-02-15 16:27:18,749 - wechat_backend.api - WARNING - factory.py:245 - <module>() - NOT registering QwenAdapter - it is None or failed to import
2026-02-15 16:27:18,749 - wechat_backend.api - WARNING - factory.py:251 - <module>() - NOT registering DoubaoAdapter - it is None or failed to import
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:254 - <module>() - Registering ChatGPTAdapter
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for chatgpt
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:260 - <module>() - Registering GeminiAdapter
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for gemini
2026-02-15 16:27:18,749 - wechat_backend.api - WARNING - factory.py:269 - <module>() - NOT registering ZhipuAdapter - it is None or failed to import
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:272 - <module>() - Registering ErnieBotAdapter
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for wenxin
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:278 - <module>() - Final registered models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:279 - <module>() - === End Adapter Registration Debug Info ===
2026-02-15 16:27:18,749 - wechat_backend.api - INFO - factory.py:282 - <module>() - Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:27:18,751 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: doubao
2026-02-15 16:27:18,751 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: deepseek
2026-02-15 16:27:18,752 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: qwen
2026-02-15 16:27:18,752 - wechat_backend.api - INFO - provider_factory.py:73 - <module>() - ProviderFactory initialized with default providers
2026-02-15 16:27:20,698 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:27:20,700 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:27:20,700 - wechat_backend.api - INFO - circuit_breaker.py:77 - __init__() - CircuitBreaker 'webhook_dispatcher' initialized: threshold=3, recovery_timeout=30s, expected_exceptions=8
[2026-02-15 16:27:20.701] [GEO-DEBUG][WORKFLOW_MANAGER] Starting background processor thread
[2026-02-15 16:27:20.701] [GEO-DEBUG][WORKFLOW_MANAGER] Starting retry processor thread
2026-02-15 16:27:20,701 - wechat_backend.api - INFO - semantic_analyzer.py:22 - __init__() - SemanticAnalyzer initialized
Building prefix dict from /Users/sgl/PycharmProjects/PythonProject/.venv/lib/python3.14/site-packages/jieba/dict.txt ...
Loading model from cache /var/folders/m8/9lzgk90s02z276bclcvcvkg40000gn/T/jieba.cache
Loading model cost 0.4439077377319336 seconds.
Prefix dict has been built succesfully.
2026-02-15 16:27:21,147 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:27:21,148 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:27:21,150 - wechat_backend.api - INFO - workflow_manager.py:175 - _start_background_processor() - Workflow background processor started
2026-02-15 16:27:21,150 - wechat_backend.api - INFO - workflow_manager.py:208 - _start_retry_processor() - Workflow retry processor started
2026-02-15 16:27:21,158 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_error_rate
2026-02-15 16:27:21,158 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: slow_response_time
2026-02-15 16:27:21,158 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_request_frequency
2026-02-15 16:27:21,158 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_security_events
2026-02-15 16:27:21,158 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: service_down
✓ 监控系统配置完成
✓ 已配置 5 个告警规则
2026-02-15 16:27:21,158 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:204 - start_monitoring() - 告警监控已启动
✓ 监控系统初始化完成
✓ 所有API端点现在都受到监控保护
✓ 告警系统已启动
2026-02-15 16:27:21,158 - wechat_backend.api - INFO - app.py:149 - warm_up_adapters() - Starting adapter warm-up...
🚀 Starting WeChat Backend API server on port 5000
🔧 Debug mode: on
📝 Log file: logs/app.log
2026-02-15 16:27:21,159 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:21,159 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter doubao warm-up failed: No adapter registered for platform: AIPlatformType.DOUBAO
2026-02-15 16:27:21,159 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:21,159 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter deepseek warm-up failed: No adapter registered for platform: AIPlatformType.DEEPSEEK
2026-02-15 16:27:21,160 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:21,160 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter qwen warm-up failed: No adapter registered for platform: AIPlatformType.QWEN
2026-02-15 16:27:21,160 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter chatgpt has no API key configured, skipping warm-up
2026-02-15 16:27:21,160 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter gemini has no API key configured, skipping warm-up
2026-02-15 16:27:21,160 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:21,161 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter zhipu warm-up failed: No adapter registered for platform: AIPlatformType.ZHIPU
2026-02-15 16:27:21,161 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter wenxin has no API key configured, skipping warm-up
2026-02-15 16:27:21,162 - wechat_backend.api - INFO - app.py:178 - warm_up_adapters() - Adapter warm-up completed
2026-02-15 16:27:21,193 - werkzeug - WARNING - _internal.py:97 - _log() -  * Debugger is active!
2026-02-15 16:27:21,213 - werkzeug - INFO - _internal.py:97 - _log() -  * Debugger PIN: 884-445-834
2026-02-15 16:27:29,470 - werkzeug - INFO - _internal.py:97 - _log() -  * Detected change in '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py', reloading
2026-02-15 16:27:30,257 - werkzeug - INFO - _internal.py:97 - _log() -  * Restarting with stat
Logging initialized with level: INFO, file: logs/app.log
2026-02-15 16:27:30,426 - wechat_backend.database - INFO - database.py:17 - init_db() - Initializing database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:27:30,427 - wechat_backend.database - INFO - database.py:112 - init_db() - Database initialization completed
2026-02-15 16:27:30,427 - wechat_backend.database - INFO - models.py:125 - init_task_status_db() - Initializing task status database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:27:30,428 - wechat_backend.database - INFO - models.py:181 - init_task_status_db() - Task status database initialization completed
2026-02-15 16:27:30,447 - wechat_backend.api - INFO - factory.py:8 - <module>() - === Starting AI Adapter Imports ===
2026-02-15 16:27:30,450 - wechat_backend.api - ERROR - factory.py:15 - <module>() - Failed to import DeepSeekAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:27:30,450 - wechat_backend.api - ERROR - factory.py:17 - <module>() - Traceback for DeepSeekAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 12, in <module>
    from .deepseek_adapter import DeepSeekAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py", line 6, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:27:30,451 - wechat_backend.api - INFO - factory.py:22 - <module>() - Successfully imported DeepSeekR1Adapter
2026-02-15 16:27:30,451 - wechat_backend.api - ERROR - factory.py:33 - <module>() - Failed to import QwenAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:27:30,452 - wechat_backend.api - ERROR - factory.py:35 - <module>() - Traceback for QwenAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 30, in <module>
    from .qwen_adapter import QwenAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py", line 10, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:27:30,458 - wechat_backend.api - ERROR - factory.py:42 - <module>() - Failed to import DoubaoAdapter: attempted relative import beyond top-level package
2026-02-15 16:27:30,458 - wechat_backend.api - ERROR - factory.py:44 - <module>() - Traceback for DoubaoAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 39, in <module>
    from .doubao_adapter import DoubaoAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py", line 17, in <module>
    from ...utils.debug_manager import ai_io_log, exception_log, debug_log
ImportError: attempted relative import beyond top-level package

2026-02-15 16:27:30,458 - wechat_backend.api - INFO - factory.py:49 - <module>() - Successfully imported ChatGPTAdapter
2026-02-15 16:27:30,459 - wechat_backend.api - INFO - factory.py:58 - <module>() - Successfully imported GeminiAdapter
2026-02-15 16:27:30,459 - wechat_backend.api - ERROR - factory.py:69 - <module>() - Failed to import ZhipuAdapter: attempted relative import beyond top-level package
2026-02-15 16:27:30,459 - wechat_backend.api - ERROR - factory.py:71 - <module>() - Traceback for ZhipuAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 66, in <module>
    from .zhipu_adapter import ZhipuAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:76 - <module>() - Successfully imported ErnieBotAdapter
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:83 - <module>() - === Completed AI Adapter Imports ===
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:218 - <module>() - === Adapter Registration Debug Info ===
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:219 - <module>() - DeepSeekAdapter status: False
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:220 - <module>() - DeepSeekR1Adapter status: True
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:221 - <module>() - QwenAdapter status: False
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:222 - <module>() - DoubaoAdapter status: False
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:223 - <module>() - ChatGPTAdapter status: True
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:224 - <module>() - GeminiAdapter status: True
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:225 - <module>() - ZhipuAdapter status: False
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:226 - <module>() - ErnieBotAdapter status: True
2026-02-15 16:27:30,460 - wechat_backend.api - WARNING - factory.py:233 - <module>() - NOT registering DeepSeekAdapter - it is None or failed to import
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:236 - <module>() - Registering DeepSeekR1Adapter
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for deepseekr1
2026-02-15 16:27:30,460 - wechat_backend.api - WARNING - factory.py:245 - <module>() - NOT registering QwenAdapter - it is None or failed to import
2026-02-15 16:27:30,460 - wechat_backend.api - WARNING - factory.py:251 - <module>() - NOT registering DoubaoAdapter - it is None or failed to import
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:254 - <module>() - Registering ChatGPTAdapter
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for chatgpt
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:260 - <module>() - Registering GeminiAdapter
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for gemini
2026-02-15 16:27:30,460 - wechat_backend.api - WARNING - factory.py:269 - <module>() - NOT registering ZhipuAdapter - it is None or failed to import
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:272 - <module>() - Registering ErnieBotAdapter
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for wenxin
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:278 - <module>() - Final registered models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:279 - <module>() - === End Adapter Registration Debug Info ===
2026-02-15 16:27:30,460 - wechat_backend.api - INFO - factory.py:282 - <module>() - Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:27:30,462 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: doubao
2026-02-15 16:27:30,462 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: deepseek
2026-02-15 16:27:30,463 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: qwen
2026-02-15 16:27:30,463 - wechat_backend.api - INFO - provider_factory.py:73 - <module>() - ProviderFactory initialized with default providers
2026-02-15 16:27:32,492 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:27:32,494 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:27:32,495 - wechat_backend.api - INFO - circuit_breaker.py:77 - __init__() - CircuitBreaker 'webhook_dispatcher' initialized: threshold=3, recovery_timeout=30s, expected_exceptions=8
[2026-02-15 16:27:32.495] [GEO-DEBUG][WORKFLOW_MANAGER] Starting background processor thread
[2026-02-15 16:27:32.495] [GEO-DEBUG][WORKFLOW_MANAGER] Starting retry processor thread
2026-02-15 16:27:32,495 - wechat_backend.api - INFO - semantic_analyzer.py:22 - __init__() - SemanticAnalyzer initialized
Building prefix dict from /Users/sgl/PycharmProjects/PythonProject/.venv/lib/python3.14/site-packages/jieba/dict.txt ...
Loading model from cache /var/folders/m8/9lzgk90s02z276bclcvcvkg40000gn/T/jieba.cache
Loading model cost 0.4566981792449951 seconds.
Prefix dict has been built succesfully.
2026-02-15 16:27:32,954 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:27:32,955 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:27:32,957 - wechat_backend.api - INFO - workflow_manager.py:175 - _start_background_processor() - Workflow background processor started
2026-02-15 16:27:32,957 - wechat_backend.api - INFO - workflow_manager.py:208 - _start_retry_processor() - Workflow retry processor started
2026-02-15 16:27:32,965 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_error_rate
2026-02-15 16:27:32,965 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: slow_response_time
2026-02-15 16:27:32,965 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_request_frequency
2026-02-15 16:27:32,965 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_security_events
2026-02-15 16:27:32,965 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: service_down
✓ 监控系统配置完成
✓ 已配置 5 个告警规则
2026-02-15 16:27:32,965 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:204 - start_monitoring() - 告警监控已启动
✓ 监控系统初始化完成
✓ 所有API端点现在都受到监控保护
✓ 告警系统已启动
2026-02-15 16:27:32,965 - wechat_backend.api - INFO - app.py:149 - warm_up_adapters() - Starting adapter warm-up...
🚀 Starting WeChat Backend API server on port 5000
🔧 Debug mode: on
📝 Log file: logs/app.log
2026-02-15 16:27:32,966 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:32,966 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter doubao warm-up failed: No adapter registered for platform: AIPlatformType.DOUBAO
2026-02-15 16:27:32,966 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:32,966 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter deepseek warm-up failed: No adapter registered for platform: AIPlatformType.DEEPSEEK
2026-02-15 16:27:32,967 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:32,967 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter qwen warm-up failed: No adapter registered for platform: AIPlatformType.QWEN
2026-02-15 16:27:32,967 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter chatgpt has no API key configured, skipping warm-up
2026-02-15 16:27:32,967 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter gemini has no API key configured, skipping warm-up
2026-02-15 16:27:32,967 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:32,967 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter zhipu warm-up failed: No adapter registered for platform: AIPlatformType.ZHIPU
2026-02-15 16:27:32,967 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter wenxin has no API key configured, skipping warm-up
2026-02-15 16:27:32,967 - wechat_backend.api - INFO - app.py:178 - warm_up_adapters() - Adapter warm-up completed
2026-02-15 16:27:32,990 - werkzeug - WARNING - _internal.py:97 - _log() -  * Debugger is active!
2026-02-15 16:27:33,009 - werkzeug - INFO - _internal.py:97 - _log() -  * Debugger PIN: 884-445-834
2026-02-15 16:27:39,211 - werkzeug - INFO - _internal.py:97 - _log() -  * Detected change in '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py', reloading
2026-02-15 16:27:39,993 - werkzeug - INFO - _internal.py:97 - _log() -  * Restarting with stat
Logging initialized with level: INFO, file: logs/app.log
2026-02-15 16:27:40,158 - wechat_backend.database - INFO - database.py:17 - init_db() - Initializing database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:27:40,158 - wechat_backend.database - INFO - database.py:112 - init_db() - Database initialization completed
2026-02-15 16:27:40,159 - wechat_backend.database - INFO - models.py:125 - init_task_status_db() - Initializing task status database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:27:40,159 - wechat_backend.database - INFO - models.py:181 - init_task_status_db() - Task status database initialization completed
2026-02-15 16:27:40,177 - wechat_backend.api - INFO - factory.py:8 - <module>() - === Starting AI Adapter Imports ===
2026-02-15 16:27:40,181 - wechat_backend.api - ERROR - factory.py:15 - <module>() - Failed to import DeepSeekAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:27:40,182 - wechat_backend.api - ERROR - factory.py:17 - <module>() - Traceback for DeepSeekAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 12, in <module>
    from .deepseek_adapter import DeepSeekAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py", line 6, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:27:40,183 - wechat_backend.api - INFO - factory.py:22 - <module>() - Successfully imported DeepSeekR1Adapter
2026-02-15 16:27:40,183 - wechat_backend.api - ERROR - factory.py:33 - <module>() - Failed to import QwenAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:27:40,183 - wechat_backend.api - ERROR - factory.py:35 - <module>() - Traceback for QwenAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 30, in <module>
    from .qwen_adapter import QwenAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py", line 10, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:27:40,189 - wechat_backend.api - ERROR - factory.py:42 - <module>() - Failed to import DoubaoAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:27:40,189 - wechat_backend.api - ERROR - factory.py:44 - <module>() - Traceback for DoubaoAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 39, in <module>
    from .doubao_adapter import DoubaoAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py", line 17, in <module>
    from ..utils.debug_manager import ai_io_log, exception_log, debug_log
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:27:40,189 - wechat_backend.api - INFO - factory.py:49 - <module>() - Successfully imported ChatGPTAdapter
2026-02-15 16:27:40,190 - wechat_backend.api - INFO - factory.py:58 - <module>() - Successfully imported GeminiAdapter
2026-02-15 16:27:40,190 - wechat_backend.api - ERROR - factory.py:69 - <module>() - Failed to import ZhipuAdapter: attempted relative import beyond top-level package
2026-02-15 16:27:40,190 - wechat_backend.api - ERROR - factory.py:71 - <module>() - Traceback for ZhipuAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 66, in <module>
    from .zhipu_adapter import ZhipuAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:76 - <module>() - Successfully imported ErnieBotAdapter
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:83 - <module>() - === Completed AI Adapter Imports ===
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:218 - <module>() - === Adapter Registration Debug Info ===
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:219 - <module>() - DeepSeekAdapter status: False
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:220 - <module>() - DeepSeekR1Adapter status: True
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:221 - <module>() - QwenAdapter status: False
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:222 - <module>() - DoubaoAdapter status: False
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:223 - <module>() - ChatGPTAdapter status: True
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:224 - <module>() - GeminiAdapter status: True
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:225 - <module>() - ZhipuAdapter status: False
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:226 - <module>() - ErnieBotAdapter status: True
2026-02-15 16:27:40,191 - wechat_backend.api - WARNING - factory.py:233 - <module>() - NOT registering DeepSeekAdapter - it is None or failed to import
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:236 - <module>() - Registering DeepSeekR1Adapter
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for deepseekr1
2026-02-15 16:27:40,191 - wechat_backend.api - WARNING - factory.py:245 - <module>() - NOT registering QwenAdapter - it is None or failed to import
2026-02-15 16:27:40,191 - wechat_backend.api - WARNING - factory.py:251 - <module>() - NOT registering DoubaoAdapter - it is None or failed to import
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:254 - <module>() - Registering ChatGPTAdapter
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for chatgpt
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:260 - <module>() - Registering GeminiAdapter
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for gemini
2026-02-15 16:27:40,191 - wechat_backend.api - WARNING - factory.py:269 - <module>() - NOT registering ZhipuAdapter - it is None or failed to import
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:272 - <module>() - Registering ErnieBotAdapter
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for wenxin
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:278 - <module>() - Final registered models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:279 - <module>() - === End Adapter Registration Debug Info ===
2026-02-15 16:27:40,191 - wechat_backend.api - INFO - factory.py:282 - <module>() - Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:27:40,193 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: doubao
2026-02-15 16:27:40,193 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: deepseek
2026-02-15 16:27:40,193 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: qwen
2026-02-15 16:27:40,193 - wechat_backend.api - INFO - provider_factory.py:73 - <module>() - ProviderFactory initialized with default providers
2026-02-15 16:27:42,157 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:27:42,158 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:27:42,159 - wechat_backend.api - INFO - circuit_breaker.py:77 - __init__() - CircuitBreaker 'webhook_dispatcher' initialized: threshold=3, recovery_timeout=30s, expected_exceptions=8
[2026-02-15 16:27:42.159] [GEO-DEBUG][WORKFLOW_MANAGER] Starting background processor thread
[2026-02-15 16:27:42.159] [GEO-DEBUG][WORKFLOW_MANAGER] Starting retry processor thread
2026-02-15 16:27:42,159 - wechat_backend.api - INFO - semantic_analyzer.py:22 - __init__() - SemanticAnalyzer initialized
Building prefix dict from /Users/sgl/PycharmProjects/PythonProject/.venv/lib/python3.14/site-packages/jieba/dict.txt ...
Loading model from cache /var/folders/m8/9lzgk90s02z276bclcvcvkg40000gn/T/jieba.cache
Loading model cost 0.4400289058685303 seconds.
Prefix dict has been built succesfully.
2026-02-15 16:27:42,601 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:27:42,602 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:27:42,604 - wechat_backend.api - INFO - workflow_manager.py:175 - _start_background_processor() - Workflow background processor started
2026-02-15 16:27:42,604 - wechat_backend.api - INFO - workflow_manager.py:208 - _start_retry_processor() - Workflow retry processor started
2026-02-15 16:27:42,612 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_error_rate
2026-02-15 16:27:42,612 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: slow_response_time
2026-02-15 16:27:42,612 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_request_frequency
2026-02-15 16:27:42,612 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_security_events
2026-02-15 16:27:42,612 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: service_down
✓ 监控系统配置完成
✓ 已配置 5 个告警规则
2026-02-15 16:27:42,612 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:204 - start_monitoring() - 告警监控已启动
✓ 监控系统初始化完成
✓ 所有API端点现在都受到监控保护
✓ 告警系统已启动
2026-02-15 16:27:42,612 - wechat_backend.api - INFO - app.py:149 - warm_up_adapters() - Starting adapter warm-up...
🚀 Starting WeChat Backend API server on port 5000
🔧 Debug mode: on
📝 Log file: logs/app.log
2026-02-15 16:27:42,613 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:42,613 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter doubao warm-up failed: No adapter registered for platform: AIPlatformType.DOUBAO
2026-02-15 16:27:42,613 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:42,613 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter deepseek warm-up failed: No adapter registered for platform: AIPlatformType.DEEPSEEK
2026-02-15 16:27:42,613 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:42,614 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter qwen warm-up failed: No adapter registered for platform: AIPlatformType.QWEN
2026-02-15 16:27:42,614 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter chatgpt has no API key configured, skipping warm-up
2026-02-15 16:27:42,615 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter gemini has no API key configured, skipping warm-up
2026-02-15 16:27:42,615 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:42,615 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter zhipu warm-up failed: No adapter registered for platform: AIPlatformType.ZHIPU
2026-02-15 16:27:42,615 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter wenxin has no API key configured, skipping warm-up
2026-02-15 16:27:42,615 - wechat_backend.api - INFO - app.py:178 - warm_up_adapters() - Adapter warm-up completed
2026-02-15 16:27:42,636 - werkzeug - WARNING - _internal.py:97 - _log() -  * Debugger is active!
2026-02-15 16:27:42,657 - werkzeug - INFO - _internal.py:97 - _log() -  * Debugger PIN: 884-445-834
2026-02-15 16:27:49,883 - werkzeug - INFO - _internal.py:97 - _log() -  * Detected change in '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py', reloading
2026-02-15 16:27:50,634 - werkzeug - INFO - _internal.py:97 - _log() -  * Restarting with stat
Logging initialized with level: INFO, file: logs/app.log
2026-02-15 16:27:50,801 - wechat_backend.database - INFO - database.py:17 - init_db() - Initializing database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:27:50,801 - wechat_backend.database - INFO - database.py:112 - init_db() - Database initialization completed
2026-02-15 16:27:50,802 - wechat_backend.database - INFO - models.py:125 - init_task_status_db() - Initializing task status database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:27:50,802 - wechat_backend.database - INFO - models.py:181 - init_task_status_db() - Task status database initialization completed
2026-02-15 16:27:50,822 - wechat_backend.api - INFO - factory.py:8 - <module>() - === Starting AI Adapter Imports ===
2026-02-15 16:27:50,826 - wechat_backend.api - ERROR - factory.py:15 - <module>() - Failed to import DeepSeekAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:27:50,827 - wechat_backend.api - ERROR - factory.py:17 - <module>() - Traceback for DeepSeekAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 12, in <module>
    from .deepseek_adapter import DeepSeekAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py", line 6, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:27:50,827 - wechat_backend.api - INFO - factory.py:22 - <module>() - Successfully imported DeepSeekR1Adapter
2026-02-15 16:27:50,828 - wechat_backend.api - ERROR - factory.py:33 - <module>() - Failed to import QwenAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:27:50,828 - wechat_backend.api - ERROR - factory.py:35 - <module>() - Traceback for QwenAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 30, in <module>
    from .qwen_adapter import QwenAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py", line 10, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:27:50,833 - wechat_backend.api - ERROR - factory.py:42 - <module>() - Failed to import DoubaoAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:27:50,834 - wechat_backend.api - ERROR - factory.py:44 - <module>() - Traceback for DoubaoAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 39, in <module>
    from .doubao_adapter import DoubaoAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py", line 17, in <module>
    from ..utils.debug_manager import ai_io_log, exception_log, debug_log
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:27:50,834 - wechat_backend.api - INFO - factory.py:49 - <module>() - Successfully imported ChatGPTAdapter
2026-02-15 16:27:50,834 - wechat_backend.api - INFO - factory.py:58 - <module>() - Successfully imported GeminiAdapter
2026-02-15 16:27:50,835 - wechat_backend.api - ERROR - factory.py:69 - <module>() - Failed to import ZhipuAdapter: attempted relative import beyond top-level package
2026-02-15 16:27:50,835 - wechat_backend.api - ERROR - factory.py:71 - <module>() - Traceback for ZhipuAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 66, in <module>
    from .zhipu_adapter import ZhipuAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py", line 10, in <module>
    from ...utils.ai_response_wrapper import log_detailed_response
ImportError: attempted relative import beyond top-level package

2026-02-15 16:27:50,835 - wechat_backend.api - INFO - factory.py:76 - <module>() - Successfully imported ErnieBotAdapter
2026-02-15 16:27:50,835 - wechat_backend.api - INFO - factory.py:83 - <module>() - === Completed AI Adapter Imports ===
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:218 - <module>() - === Adapter Registration Debug Info ===
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:219 - <module>() - DeepSeekAdapter status: False
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:220 - <module>() - DeepSeekR1Adapter status: True
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:221 - <module>() - QwenAdapter status: False
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:222 - <module>() - DoubaoAdapter status: False
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:223 - <module>() - ChatGPTAdapter status: True
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:224 - <module>() - GeminiAdapter status: True
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:225 - <module>() - ZhipuAdapter status: False
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:226 - <module>() - ErnieBotAdapter status: True
2026-02-15 16:27:50,836 - wechat_backend.api - WARNING - factory.py:233 - <module>() - NOT registering DeepSeekAdapter - it is None or failed to import
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:236 - <module>() - Registering DeepSeekR1Adapter
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for deepseekr1
2026-02-15 16:27:50,836 - wechat_backend.api - WARNING - factory.py:245 - <module>() - NOT registering QwenAdapter - it is None or failed to import
2026-02-15 16:27:50,836 - wechat_backend.api - WARNING - factory.py:251 - <module>() - NOT registering DoubaoAdapter - it is None or failed to import
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:254 - <module>() - Registering ChatGPTAdapter
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for chatgpt
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:260 - <module>() - Registering GeminiAdapter
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for gemini
2026-02-15 16:27:50,836 - wechat_backend.api - WARNING - factory.py:269 - <module>() - NOT registering ZhipuAdapter - it is None or failed to import
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:272 - <module>() - Registering ErnieBotAdapter
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for wenxin
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:278 - <module>() - Final registered models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:279 - <module>() - === End Adapter Registration Debug Info ===
2026-02-15 16:27:50,836 - wechat_backend.api - INFO - factory.py:282 - <module>() - Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:27:50,838 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: doubao
2026-02-15 16:27:50,838 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: deepseek
2026-02-15 16:27:50,838 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: qwen
2026-02-15 16:27:50,838 - wechat_backend.api - INFO - provider_factory.py:73 - <module>() - ProviderFactory initialized with default providers
2026-02-15 16:27:52,785 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:27:52,786 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:27:52,786 - wechat_backend.api - INFO - circuit_breaker.py:77 - __init__() - CircuitBreaker 'webhook_dispatcher' initialized: threshold=3, recovery_timeout=30s, expected_exceptions=8
[2026-02-15 16:27:52.787] [GEO-DEBUG][WORKFLOW_MANAGER] Starting background processor thread
[2026-02-15 16:27:52.787] [GEO-DEBUG][WORKFLOW_MANAGER] Starting retry processor thread
2026-02-15 16:27:52,787 - wechat_backend.api - INFO - semantic_analyzer.py:22 - __init__() - SemanticAnalyzer initialized
Building prefix dict from /Users/sgl/PycharmProjects/PythonProject/.venv/lib/python3.14/site-packages/jieba/dict.txt ...
Loading model from cache /var/folders/m8/9lzgk90s02z276bclcvcvkg40000gn/T/jieba.cache
Loading model cost 0.44335412979125977 seconds.
Prefix dict has been built succesfully.
2026-02-15 16:27:53,232 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:27:53,233 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:27:53,236 - wechat_backend.api - INFO - workflow_manager.py:175 - _start_background_processor() - Workflow background processor started
2026-02-15 16:27:53,236 - wechat_backend.api - INFO - workflow_manager.py:208 - _start_retry_processor() - Workflow retry processor started
2026-02-15 16:27:53,243 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_error_rate
2026-02-15 16:27:53,243 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: slow_response_time
2026-02-15 16:27:53,243 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_request_frequency
2026-02-15 16:27:53,243 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_security_events
2026-02-15 16:27:53,243 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: service_down
✓ 监控系统配置完成
✓ 已配置 5 个告警规则
2026-02-15 16:27:53,243 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:204 - start_monitoring() - 告警监控已启动
✓ 监控系统初始化完成
✓ 所有API端点现在都受到监控保护
✓ 告警系统已启动
2026-02-15 16:27:53,243 - wechat_backend.api - INFO - app.py:149 - warm_up_adapters() - Starting adapter warm-up...
🚀 Starting WeChat Backend API server on port 5000
🔧 Debug mode: on
📝 Log file: logs/app.log
2026-02-15 16:27:53,244 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:53,244 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter doubao warm-up failed: No adapter registered for platform: AIPlatformType.DOUBAO
2026-02-15 16:27:53,244 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:53,244 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter deepseek warm-up failed: No adapter registered for platform: AIPlatformType.DEEPSEEK
2026-02-15 16:27:53,244 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:53,244 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter qwen warm-up failed: No adapter registered for platform: AIPlatformType.QWEN
2026-02-15 16:27:53,245 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter chatgpt has no API key configured, skipping warm-up
2026-02-15 16:27:53,245 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter gemini has no API key configured, skipping warm-up
2026-02-15 16:27:53,246 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:27:53,246 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter zhipu warm-up failed: No adapter registered for platform: AIPlatformType.ZHIPU
2026-02-15 16:27:53,246 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter wenxin has no API key configured, skipping warm-up
2026-02-15 16:27:53,246 - wechat_backend.api - INFO - app.py:178 - warm_up_adapters() - Adapter warm-up completed
2026-02-15 16:27:53,267 - werkzeug - WARNING - _internal.py:97 - _log() -  * Debugger is active!
2026-02-15 16:27:53,286 - werkzeug - INFO - _internal.py:97 - _log() -  * Debugger PIN: 884-445-834
2026-02-15 16:27:59,463 - werkzeug - INFO - _internal.py:97 - _log() -  * Detected change in '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py', reloading
2026-02-15 16:28:00,244 - werkzeug - INFO - _internal.py:97 - _log() -  * Restarting with stat
Logging initialized with level: INFO, file: logs/app.log
2026-02-15 16:28:00,413 - wechat_backend.database - INFO - database.py:17 - init_db() - Initializing database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:28:00,413 - wechat_backend.database - INFO - database.py:112 - init_db() - Database initialization completed
2026-02-15 16:28:00,414 - wechat_backend.database - INFO - models.py:125 - init_task_status_db() - Initializing task status database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:28:00,414 - wechat_backend.database - INFO - models.py:181 - init_task_status_db() - Task status database initialization completed
2026-02-15 16:28:00,432 - wechat_backend.api - INFO - factory.py:8 - <module>() - === Starting AI Adapter Imports ===
2026-02-15 16:28:00,435 - wechat_backend.api - ERROR - factory.py:15 - <module>() - Failed to import DeepSeekAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:28:00,435 - wechat_backend.api - ERROR - factory.py:17 - <module>() - Traceback for DeepSeekAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 12, in <module>
    from .deepseek_adapter import DeepSeekAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py", line 6, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:28:00,436 - wechat_backend.api - INFO - factory.py:22 - <module>() - Successfully imported DeepSeekR1Adapter
2026-02-15 16:28:00,436 - wechat_backend.api - ERROR - factory.py:33 - <module>() - Failed to import QwenAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:28:00,436 - wechat_backend.api - ERROR - factory.py:35 - <module>() - Traceback for QwenAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 30, in <module>
    from .qwen_adapter import QwenAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py", line 10, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:28:00,440 - wechat_backend.api - ERROR - factory.py:42 - <module>() - Failed to import DoubaoAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:28:00,440 - wechat_backend.api - ERROR - factory.py:44 - <module>() - Traceback for DoubaoAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 39, in <module>
    from .doubao_adapter import DoubaoAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py", line 17, in <module>
    from ..utils.debug_manager import ai_io_log, exception_log, debug_log
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:28:00,440 - wechat_backend.api - INFO - factory.py:49 - <module>() - Successfully imported ChatGPTAdapter
2026-02-15 16:28:00,441 - wechat_backend.api - INFO - factory.py:58 - <module>() - Successfully imported GeminiAdapter
2026-02-15 16:28:00,443 - wechat_backend.api - ERROR - factory.py:69 - <module>() - Failed to import ZhipuAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:28:00,443 - wechat_backend.api - ERROR - factory.py:71 - <module>() - Traceback for ZhipuAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 66, in <module>
    from .zhipu_adapter import ZhipuAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py", line 10, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:76 - <module>() - Successfully imported ErnieBotAdapter
2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:83 - <module>() - === Completed AI Adapter Imports ===
2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:218 - <module>() - === Adapter Registration Debug Info ===
2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:219 - <module>() - DeepSeekAdapter status: False
2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:220 - <module>() - DeepSeekR1Adapter status: True
2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:221 - <module>() - QwenAdapter status: False
2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:222 - <module>() - DoubaoAdapter status: False
2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:223 - <module>() - ChatGPTAdapter status: True
2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:224 - <module>() - GeminiAdapter status: True
2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:225 - <module>() - ZhipuAdapter status: False
2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:226 - <module>() - ErnieBotAdapter status: True
2026-02-15 16:28:00,443 - wechat_backend.api - WARNING - factory.py:233 - <module>() - NOT registering DeepSeekAdapter - it is None or failed to import
2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:236 - <module>() - Registering DeepSeekR1Adapter
2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for deepseekr1
2026-02-15 16:28:00,443 - wechat_backend.api - WARNING - factory.py:245 - <module>() - NOT registering QwenAdapter - it is None or failed to import
2026-02-15 16:28:00,443 - wechat_backend.api - WARNING - factory.py:251 - <module>() - NOT registering DoubaoAdapter - it is None or failed to import
2026-02-15 16:28:00,443 - wechat_backend.api - INFO - factory.py:254 - <module>() - Registering ChatGPTAdapter
2026-02-15 16:28:00,444 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for chatgpt
2026-02-15 16:28:00,444 - wechat_backend.api - INFO - factory.py:260 - <module>() - Registering GeminiAdapter
2026-02-15 16:28:00,444 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for gemini
2026-02-15 16:28:00,444 - wechat_backend.api - WARNING - factory.py:269 - <module>() - NOT registering ZhipuAdapter - it is None or failed to import
2026-02-15 16:28:00,444 - wechat_backend.api - INFO - factory.py:272 - <module>() - Registering ErnieBotAdapter
2026-02-15 16:28:00,444 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for wenxin
2026-02-15 16:28:00,444 - wechat_backend.api - INFO - factory.py:278 - <module>() - Final registered models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:28:00,444 - wechat_backend.api - INFO - factory.py:279 - <module>() - === End Adapter Registration Debug Info ===
2026-02-15 16:28:00,444 - wechat_backend.api - INFO - factory.py:282 - <module>() - Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:28:00,445 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: doubao
2026-02-15 16:28:00,445 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: deepseek
2026-02-15 16:28:00,445 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: qwen
2026-02-15 16:28:00,446 - wechat_backend.api - INFO - provider_factory.py:73 - <module>() - ProviderFactory initialized with default providers
2026-02-15 16:28:02,469 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:28:02,470 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:28:02,471 - wechat_backend.api - INFO - circuit_breaker.py:77 - __init__() - CircuitBreaker 'webhook_dispatcher' initialized: threshold=3, recovery_timeout=30s, expected_exceptions=8
[2026-02-15 16:28:02.471] [GEO-DEBUG][WORKFLOW_MANAGER] Starting background processor thread
[2026-02-15 16:28:02.471] [GEO-DEBUG][WORKFLOW_MANAGER] Starting retry processor thread
2026-02-15 16:28:02,471 - wechat_backend.api - INFO - semantic_analyzer.py:22 - __init__() - SemanticAnalyzer initialized
Building prefix dict from /Users/sgl/PycharmProjects/PythonProject/.venv/lib/python3.14/site-packages/jieba/dict.txt ...
Loading model from cache /var/folders/m8/9lzgk90s02z276bclcvcvkg40000gn/T/jieba.cache
Loading model cost 0.4563007354736328 seconds.
Prefix dict has been built succesfully.
2026-02-15 16:28:02,930 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:28:02,930 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:28:02,933 - wechat_backend.api - INFO - workflow_manager.py:175 - _start_background_processor() - Workflow background processor started
2026-02-15 16:28:02,933 - wechat_backend.api - INFO - workflow_manager.py:208 - _start_retry_processor() - Workflow retry processor started
2026-02-15 16:28:02,941 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_error_rate
2026-02-15 16:28:02,941 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: slow_response_time
2026-02-15 16:28:02,941 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_request_frequency
2026-02-15 16:28:02,941 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_security_events
2026-02-15 16:28:02,941 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: service_down
✓ 监控系统配置完成
✓ 已配置 5 个告警规则
2026-02-15 16:28:02,941 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:204 - start_monitoring() - 告警监控已启动
✓ 监控系统初始化完成
✓ 所有API端点现在都受到监控保护
✓ 告警系统已启动
2026-02-15 16:28:02,941 - wechat_backend.api - INFO - app.py:149 - warm_up_adapters() - Starting adapter warm-up...
🚀 Starting WeChat Backend API server on port 5000
🔧 Debug mode: on
📝 Log file: logs/app.log
2026-02-15 16:28:02,942 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:28:02,942 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter doubao warm-up failed: No adapter registered for platform: AIPlatformType.DOUBAO
2026-02-15 16:28:02,942 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:28:02,942 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter deepseek warm-up failed: No adapter registered for platform: AIPlatformType.DEEPSEEK
2026-02-15 16:28:02,942 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:28:02,942 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter qwen warm-up failed: No adapter registered for platform: AIPlatformType.QWEN
2026-02-15 16:28:02,943 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter chatgpt has no API key configured, skipping warm-up
2026-02-15 16:28:02,943 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter gemini has no API key configured, skipping warm-up
2026-02-15 16:28:02,943 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:28:02,943 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter zhipu warm-up failed: No adapter registered for platform: AIPlatformType.ZHIPU
2026-02-15 16:28:02,943 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter wenxin has no API key configured, skipping warm-up
2026-02-15 16:28:02,943 - wechat_backend.api - INFO - app.py:178 - warm_up_adapters() - Adapter warm-up completed
2026-02-15 16:28:02,968 - werkzeug - WARNING - _internal.py:97 - _log() -  * Debugger is active!
2026-02-15 16:28:02,987 - werkzeug - INFO - _internal.py:97 - _log() -  * Debugger PIN: 884-445-834
^C%                                                                                                                                                                                                                                              
(.venv) sgl@SunGuolongdeMacBook-Pro backend_python % cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python run.py
Logging initialized with level: INFO, file: logs/app.log
2026-02-15 16:28:24,240 - wechat_backend.database - INFO - database.py:17 - init_db() - Initializing database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:28:24,241 - wechat_backend.database - INFO - database.py:112 - init_db() - Database initialization completed
2026-02-15 16:28:24,241 - wechat_backend.database - INFO - models.py:125 - init_task_status_db() - Initializing task status database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:28:24,241 - wechat_backend.database - INFO - models.py:181 - init_task_status_db() - Task status database initialization completed
2026-02-15 16:28:24,259 - wechat_backend.api - INFO - factory.py:8 - <module>() - === Starting AI Adapter Imports ===
2026-02-15 16:28:24,263 - wechat_backend.api - ERROR - factory.py:15 - <module>() - Failed to import DeepSeekAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:28:24,264 - wechat_backend.api - ERROR - factory.py:17 - <module>() - Traceback for DeepSeekAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 12, in <module>
    from .deepseek_adapter import DeepSeekAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py", line 6, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:28:24,264 - wechat_backend.api - INFO - factory.py:22 - <module>() - Successfully imported DeepSeekR1Adapter
2026-02-15 16:28:24,265 - wechat_backend.api - ERROR - factory.py:33 - <module>() - Failed to import QwenAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:28:24,265 - wechat_backend.api - ERROR - factory.py:35 - <module>() - Traceback for QwenAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 30, in <module>
    from .qwen_adapter import QwenAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py", line 10, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:28:24,268 - wechat_backend.api - ERROR - factory.py:42 - <module>() - Failed to import DoubaoAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:28:24,268 - wechat_backend.api - ERROR - factory.py:44 - <module>() - Traceback for DoubaoAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 39, in <module>
    from .doubao_adapter import DoubaoAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py", line 17, in <module>
    from ..utils.debug_manager import ai_io_log, exception_log, debug_log
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:28:24,268 - wechat_backend.api - INFO - factory.py:49 - <module>() - Successfully imported ChatGPTAdapter
2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:58 - <module>() - Successfully imported GeminiAdapter
2026-02-15 16:28:24,269 - wechat_backend.api - ERROR - factory.py:69 - <module>() - Failed to import ZhipuAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:28:24,269 - wechat_backend.api - ERROR - factory.py:71 - <module>() - Traceback for ZhipuAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 66, in <module>
    from .zhipu_adapter import ZhipuAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py", line 10, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:76 - <module>() - Successfully imported ErnieBotAdapter
2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:83 - <module>() - === Completed AI Adapter Imports ===
2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:218 - <module>() - === Adapter Registration Debug Info ===
2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:219 - <module>() - DeepSeekAdapter status: False
2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:220 - <module>() - DeepSeekR1Adapter status: True
2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:221 - <module>() - QwenAdapter status: False
2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:222 - <module>() - DoubaoAdapter status: False
2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:223 - <module>() - ChatGPTAdapter status: True
2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:224 - <module>() - GeminiAdapter status: True
2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:225 - <module>() - ZhipuAdapter status: False
2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:226 - <module>() - ErnieBotAdapter status: True
2026-02-15 16:28:24,269 - wechat_backend.api - WARNING - factory.py:233 - <module>() - NOT registering DeepSeekAdapter - it is None or failed to import
2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:236 - <module>() - Registering DeepSeekR1Adapter
2026-02-15 16:28:24,269 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for deepseekr1
2026-02-15 16:28:24,269 - wechat_backend.api - WARNING - factory.py:245 - <module>() - NOT registering QwenAdapter - it is None or failed to import
2026-02-15 16:28:24,269 - wechat_backend.api - WARNING - factory.py:251 - <module>() - NOT registering DoubaoAdapter - it is None or failed to import
2026-02-15 16:28:24,270 - wechat_backend.api - INFO - factory.py:254 - <module>() - Registering ChatGPTAdapter
2026-02-15 16:28:24,270 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for chatgpt
2026-02-15 16:28:24,270 - wechat_backend.api - INFO - factory.py:260 - <module>() - Registering GeminiAdapter
2026-02-15 16:28:24,270 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for gemini
2026-02-15 16:28:24,270 - wechat_backend.api - WARNING - factory.py:269 - <module>() - NOT registering ZhipuAdapter - it is None or failed to import
2026-02-15 16:28:24,270 - wechat_backend.api - INFO - factory.py:272 - <module>() - Registering ErnieBotAdapter
2026-02-15 16:28:24,270 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for wenxin
2026-02-15 16:28:24,270 - wechat_backend.api - INFO - factory.py:278 - <module>() - Final registered models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:28:24,270 - wechat_backend.api - INFO - factory.py:279 - <module>() - === End Adapter Registration Debug Info ===
2026-02-15 16:28:24,270 - wechat_backend.api - INFO - factory.py:282 - <module>() - Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:28:24,272 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: doubao
2026-02-15 16:28:24,272 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: deepseek
2026-02-15 16:28:24,272 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: qwen
2026-02-15 16:28:24,272 - wechat_backend.api - INFO - provider_factory.py:73 - <module>() - ProviderFactory initialized with default providers
2026-02-15 16:28:26,292 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:28:26,293 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:28:26,294 - wechat_backend.api - INFO - circuit_breaker.py:77 - __init__() - CircuitBreaker 'webhook_dispatcher' initialized: threshold=3, recovery_timeout=30s, expected_exceptions=8
[2026-02-15 16:28:26.294] [GEO-DEBUG][WORKFLOW_MANAGER] Starting background processor thread
[2026-02-15 16:28:26.294] [GEO-DEBUG][WORKFLOW_MANAGER] Starting retry processor thread
2026-02-15 16:28:26,294 - wechat_backend.api - INFO - semantic_analyzer.py:22 - __init__() - SemanticAnalyzer initialized
Building prefix dict from /Users/sgl/PycharmProjects/PythonProject/.venv/lib/python3.14/site-packages/jieba/dict.txt ...
Loading model from cache /var/folders/m8/9lzgk90s02z276bclcvcvkg40000gn/T/jieba.cache
Loading model cost 0.4510951042175293 seconds.
Prefix dict has been built succesfully.
2026-02-15 16:28:26,747 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:28:26,748 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:28:26,750 - wechat_backend.api - INFO - workflow_manager.py:175 - _start_background_processor() - Workflow background processor started
2026-02-15 16:28:26,750 - wechat_backend.api - INFO - workflow_manager.py:208 - _start_retry_processor() - Workflow retry processor started
2026-02-15 16:28:26,757 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_error_rate
2026-02-15 16:28:26,758 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: slow_response_time
2026-02-15 16:28:26,758 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_request_frequency
2026-02-15 16:28:26,758 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_security_events
2026-02-15 16:28:26,758 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: service_down
✓ 监控系统配置完成
✓ 已配置 5 个告警规则
2026-02-15 16:28:26,758 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:204 - start_monitoring() - 告警监控已启动
✓ 监控系统初始化完成
✓ 所有API端点现在都受到监控保护
✓ 告警系统已启动
2026-02-15 16:28:26,758 - wechat_backend.api - INFO - app.py:149 - warm_up_adapters() - Starting adapter warm-up...
🚀 Starting WeChat Backend API server on port 5000
🔧 Debug mode: on
📝 Log file: logs/app.log
2026-02-15 16:28:26,759 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:28:26,759 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter doubao warm-up failed: No adapter registered for platform: AIPlatformType.DOUBAO
2026-02-15 16:28:26,759 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:28:26,759 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter deepseek warm-up failed: No adapter registered for platform: AIPlatformType.DEEPSEEK
2026-02-15 16:28:26,759 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:28:26,759 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter qwen warm-up failed: No adapter registered for platform: AIPlatformType.QWEN
2026-02-15 16:28:26,760 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter chatgpt has no API key configured, skipping warm-up
2026-02-15 16:28:26,760 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter gemini has no API key configured, skipping warm-up
2026-02-15 16:28:26,760 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:28:26,761 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter zhipu warm-up failed: No adapter registered for platform: AIPlatformType.ZHIPU
 * Serving Flask app 'wechat_backend.app'
 * Debug mode: on
2026-02-15 16:28:26,761 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter wenxin has no API key configured, skipping warm-up
2026-02-15 16:28:26,761 - wechat_backend.api - INFO - app.py:178 - warm_up_adapters() - Adapter warm-up completed
2026-02-15 16:28:26,787 - werkzeug - INFO - _internal.py:97 - _log() - WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
2026-02-15 16:28:26,787 - werkzeug - INFO - _internal.py:97 - _log() - Press CTRL+C to quit
2026-02-15 16:28:26,788 - werkzeug - INFO - _internal.py:97 - _log() -  * Restarting with stat
Logging initialized with level: INFO, file: logs/app.log
2026-02-15 16:28:26,908 - wechat_backend.database - INFO - database.py:17 - init_db() - Initializing database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:28:26,909 - wechat_backend.database - INFO - database.py:112 - init_db() - Database initialization completed
2026-02-15 16:28:26,909 - wechat_backend.database - INFO - models.py:125 - init_task_status_db() - Initializing task status database at /Users/sgl/PycharmProjects/PythonProject/backend_python/database.db
2026-02-15 16:28:26,909 - wechat_backend.database - INFO - models.py:181 - init_task_status_db() - Task status database initialization completed
2026-02-15 16:28:26,922 - wechat_backend.api - INFO - factory.py:8 - <module>() - === Starting AI Adapter Imports ===
2026-02-15 16:28:26,925 - wechat_backend.api - ERROR - factory.py:15 - <module>() - Failed to import DeepSeekAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:28:26,925 - wechat_backend.api - ERROR - factory.py:17 - <module>() - Traceback for DeepSeekAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 12, in <module>
    from .deepseek_adapter import DeepSeekAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/deepseek_adapter.py", line 6, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:28:26,925 - wechat_backend.api - INFO - factory.py:22 - <module>() - Successfully imported DeepSeekR1Adapter
2026-02-15 16:28:26,926 - wechat_backend.api - ERROR - factory.py:33 - <module>() - Failed to import QwenAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:28:26,926 - wechat_backend.api - ERROR - factory.py:35 - <module>() - Traceback for QwenAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 30, in <module>
    from .qwen_adapter import QwenAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/qwen_adapter.py", line 10, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:28:26,928 - wechat_backend.api - ERROR - factory.py:42 - <module>() - Failed to import DoubaoAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:28:26,929 - wechat_backend.api - ERROR - factory.py:44 - <module>() - Traceback for DoubaoAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 39, in <module>
    from .doubao_adapter import DoubaoAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/doubao_adapter.py", line 17, in <module>
    from ..utils.debug_manager import ai_io_log, exception_log, debug_log
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:28:26,929 - wechat_backend.api - INFO - factory.py:49 - <module>() - Successfully imported ChatGPTAdapter
2026-02-15 16:28:26,929 - wechat_backend.api - INFO - factory.py:58 - <module>() - Successfully imported GeminiAdapter
2026-02-15 16:28:26,929 - wechat_backend.api - ERROR - factory.py:69 - <module>() - Failed to import ZhipuAdapter: No module named 'wechat_backend.utils'
2026-02-15 16:28:26,929 - wechat_backend.api - ERROR - factory.py:71 - <module>() - Traceback for ZhipuAdapter import error: Traceback (most recent call last):
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/factory.py", line 66, in <module>
    from .zhipu_adapter import ZhipuAdapter
  File "/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/ai_adapters/zhipu_adapter.py", line 10, in <module>
    from ..utils.ai_response_wrapper import log_detailed_response
ModuleNotFoundError: No module named 'wechat_backend.utils'

2026-02-15 16:28:26,929 - wechat_backend.api - INFO - factory.py:76 - <module>() - Successfully imported ErnieBotAdapter
2026-02-15 16:28:26,929 - wechat_backend.api - INFO - factory.py:83 - <module>() - === Completed AI Adapter Imports ===
2026-02-15 16:28:26,929 - wechat_backend.api - INFO - factory.py:218 - <module>() - === Adapter Registration Debug Info ===
2026-02-15 16:28:26,929 - wechat_backend.api - INFO - factory.py:219 - <module>() - DeepSeekAdapter status: False
2026-02-15 16:28:26,929 - wechat_backend.api - INFO - factory.py:220 - <module>() - DeepSeekR1Adapter status: True
2026-02-15 16:28:26,929 - wechat_backend.api - INFO - factory.py:221 - <module>() - QwenAdapter status: False
2026-02-15 16:28:26,929 - wechat_backend.api - INFO - factory.py:222 - <module>() - DoubaoAdapter status: False
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:223 - <module>() - ChatGPTAdapter status: True
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:224 - <module>() - GeminiAdapter status: True
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:225 - <module>() - ZhipuAdapter status: False
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:226 - <module>() - ErnieBotAdapter status: True
2026-02-15 16:28:26,930 - wechat_backend.api - WARNING - factory.py:233 - <module>() - NOT registering DeepSeekAdapter - it is None or failed to import
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:236 - <module>() - Registering DeepSeekR1Adapter
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for deepseekr1
2026-02-15 16:28:26,930 - wechat_backend.api - WARNING - factory.py:245 - <module>() - NOT registering QwenAdapter - it is None or failed to import
2026-02-15 16:28:26,930 - wechat_backend.api - WARNING - factory.py:251 - <module>() - NOT registering DoubaoAdapter - it is None or failed to import
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:254 - <module>() - Registering ChatGPTAdapter
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for chatgpt
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:260 - <module>() - Registering GeminiAdapter
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for gemini
2026-02-15 16:28:26,930 - wechat_backend.api - WARNING - factory.py:269 - <module>() - NOT registering ZhipuAdapter - it is None or failed to import
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:272 - <module>() - Registering ErnieBotAdapter
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:140 - register() - Registered adapter for wenxin
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:278 - <module>() - Final registered models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:279 - <module>() - === End Adapter Registration Debug Info ===
2026-02-15 16:28:26,930 - wechat_backend.api - INFO - factory.py:282 - <module>() - Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
Current Registered Models: ['deepseekr1', 'chatgpt', 'gemini', 'wenxin']
2026-02-15 16:28:26,931 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: doubao
2026-02-15 16:28:26,931 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: deepseek
2026-02-15 16:28:26,931 - wechat_backend.api - INFO - provider_factory.py:30 - register() - Registered provider for platform: qwen
2026-02-15 16:28:26,931 - wechat_backend.api - INFO - provider_factory.py:73 - <module>() - ProviderFactory initialized with default providers
2026-02-15 16:28:28,867 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:28:28,868 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:28:28,868 - wechat_backend.api - INFO - circuit_breaker.py:77 - __init__() - CircuitBreaker 'webhook_dispatcher' initialized: threshold=3, recovery_timeout=30s, expected_exceptions=8
[2026-02-15 16:28:28.869] [GEO-DEBUG][WORKFLOW_MANAGER] Starting background processor thread
[2026-02-15 16:28:28.869] [GEO-DEBUG][WORKFLOW_MANAGER] Starting retry processor thread
2026-02-15 16:28:28,869 - wechat_backend.api - INFO - semantic_analyzer.py:22 - __init__() - SemanticAnalyzer initialized
Building prefix dict from /Users/sgl/PycharmProjects/PythonProject/.venv/lib/python3.14/site-packages/jieba/dict.txt ...
Loading model from cache /var/folders/m8/9lzgk90s02z276bclcvcvkg40000gn/T/jieba.cache
Loading model cost 0.44324183464050293 seconds.
Prefix dict has been built succesfully.
2026-02-15 16:28:29,314 - apscheduler.scheduler - INFO - base.py:214 - start() - Scheduler started
2026-02-15 16:28:29,315 - wechat_backend.api - INFO - cruise_controller.py:53 - _init_scheduler() - Cruise controller scheduler initialized and started
2026-02-15 16:28:29,317 - wechat_backend.api - INFO - workflow_manager.py:175 - _start_background_processor() - Workflow background processor started
2026-02-15 16:28:29,317 - wechat_backend.api - INFO - workflow_manager.py:208 - _start_retry_processor() - Workflow retry processor started
2026-02-15 16:28:29,324 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_error_rate
2026-02-15 16:28:29,325 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: slow_response_time
2026-02-15 16:28:29,325 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_request_frequency
2026-02-15 16:28:29,325 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: high_security_events
2026-02-15 16:28:29,325 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:160 - add_alert() - 添加告警: service_down
✓ 监控系统配置完成
✓ 已配置 5 个告警规则
2026-02-15 16:28:29,325 - wechat_backend.monitoring.alert_system - INFO - alert_system.py:204 - start_monitoring() - 告警监控已启动
✓ 监控系统初始化完成
✓ 所有API端点现在都受到监控保护
✓ 告警系统已启动
2026-02-15 16:28:29,325 - wechat_backend.api - INFO - app.py:149 - warm_up_adapters() - Starting adapter warm-up...
🚀 Starting WeChat Backend API server on port 5000
🔧 Debug mode: on
📝 Log file: logs/app.log
2026-02-15 16:28:29,326 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:28:29,326 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter doubao warm-up failed: No adapter registered for platform: AIPlatformType.DOUBAO
2026-02-15 16:28:29,326 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:28:29,326 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter deepseek warm-up failed: No adapter registered for platform: AIPlatformType.DEEPSEEK
2026-02-15 16:28:29,326 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:28:29,326 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter qwen warm-up failed: No adapter registered for platform: AIPlatformType.QWEN
2026-02-15 16:28:29,327 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter chatgpt has no API key configured, skipping warm-up
2026-02-15 16:28:29,327 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter gemini has no API key configured, skipping warm-up
2026-02-15 16:28:29,328 - wechat_backend.api - ERROR - factory.py:197 - create() - REGISTERED_MODELS: [<AIPlatformType.DEEPSEEKR1: 'deepseekr1'>, <AIPlatformType.CHATGPT: 'chatgpt'>, <AIPlatformType.GEMINI: 'gemini'>, <AIPlatformType.WENXIN: 'wenxin'>]
2026-02-15 16:28:29,328 - wechat_backend.api - WARNING - app.py:176 - warm_up_adapters() - Adapter zhipu warm-up failed: No adapter registered for platform: AIPlatformType.ZHIPU
2026-02-15 16:28:29,328 - wechat_backend.api - WARNING - app.py:173 - warm_up_adapters() - Adapter wenxin has no API key configured, skipping warm-up
2026-02-15 16:28:29,328 - wechat_backend.api - INFO - app.py:178 - warm_up_adapters() - Adapter warm-up completed
2026-02-15 16:28:29,347 - werkzeug - WARNING - _internal.py:97 - _log() -  * Debugger is active!
2026-02-15 16:28:29,365 - werkzeug - INFO - _internal.py:97 - _log() -  * Debugger PIN: 884-445-834
