#!/usr/bin/env python3
"""
项目架构分析工具
提取所有 API 端点、函数定义、参数和调用关系
生成可视化架构图
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
BACKEND_ROOT = PROJECT_ROOT / 'backend_python'
FRONTEND_ROOT = PROJECT_ROOT

# 存储结构
api_endpoints = []
function_definitions = []
class_definitions = []
import_relationships = defaultdict(set)
call_relationships = defaultdict(set)
data_models = []

def extract_api_endpoints_from_views(file_path: Path) -> List[Dict]:
    """从 views.py 提取 API 端点"""
    endpoints = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 匹配 Flask 路由装饰器
        pattern = r'@\w+\.route\([\'"]([^\'"]+)[\'"].*?methods=\[([^\]]+)\]'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for route, methods in matches:
            methods_list = [m.strip().strip("'\"") for m in methods.split(',')]
            endpoints.append({
                'path': route,
                'methods': methods_list,
                'file': str(file_path.relative_to(PROJECT_ROOT))
            })
        
        # 匹配 blueprint 路由
        pattern2 = r'@\w+_bp\.route\([\'"]([^\'"]+)[\'"]'
        matches2 = re.findall(pattern2, content)
        
        for route in matches2:
            if not any(ep['path'] == route for ep in endpoints):
                endpoints.append({
                    'path': route,
                    'methods': ['GET', 'POST'],
                    'file': str(file_path.relative_to(PROJECT_ROOT))
                })
    except Exception as e:
        print(f"Error extracting endpoints from {file_path}: {e}")
    
    return endpoints

def extract_function_definitions(file_path: Path) -> List[Dict]:
    """提取函数定义和参数"""
    functions = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 匹配 Python 函数定义
        pattern = r'def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*([^\n:]+))?:'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            func_name = match.group(1)
            params_str = match.group(2)
            return_type = match.group(3).strip() if match.group(3) else None
            
            # 解析参数
            params = []
            if params_str.strip():
                param_list = params_str.split(',')
                for param in param_list:
                    param = param.strip()
                    if param and param != 'self' and param != 'cls':
                        # 提取参数名和类型
                        if ':' in param:
                            param_name, param_type = param.split(':', 1)
                            params.append({
                                'name': param_name.strip(),
                                'type': param_type.strip().split('=')[0].strip()
                            })
                        else:
                            param_name = param.split('=')[0].strip()
                            if param_name:
                                params.append({
                                    'name': param_name,
                                    'type': 'Any'
                                })
            
            functions.append({
                'name': func_name,
                'params': params,
                'return_type': return_type,
                'file': str(file_path.relative_to(PROJECT_ROOT)),
                'line': content[:match.start()].count('\n') + 1
            })
    except Exception as e:
        print(f"Error extracting functions from {file_path}: {e}")
    
    return functions

def extract_class_definitions(file_path: Path) -> List[Dict]:
    """提取类定义"""
    classes = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 匹配 Python 类定义
        pattern = r'class\s+(\w+)(?:\s*\(\s*([^\)]*)\s*\))?:'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            class_name = match.group(1)
            parents = match.group(2).strip() if match.group(2) else ''
            
            classes.append({
                'name': class_name,
                'parents': [p.strip() for p in parents.split(',') if p.strip()],
                'file': str(file_path.relative_to(PROJECT_ROOT)),
                'line': content[:match.start()].count('\n') + 1
            })
    except Exception as e:
        print(f"Error extracting classes from {file_path}: {e}")
    
    return classes

def extract_import_relationships(file_path: Path) -> Dict[str, Set[str]]:
    """提取导入关系"""
    imports = defaultdict(set)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 匹配 import 语句
        patterns = [
            r'from\s+([\w.]+)\s+import\s+(?:\(([^)]+)\)|([^\n]+))',
            r'import\s+([\w.]+)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if match.group(1):
                    module = match.group(1)
                    imports[str(file_path.stem)].add(module)
    except Exception as e:
        print(f"Error extracting imports from {file_path}: {e}")
    
    return imports

def extract_data_models(file_path: Path) -> List[Dict]:
    """提取数据模型（dataclass, Pydantic 等）"""
    models = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 匹配 dataclass
        pattern = r'@dataclass\s+class\s+(\w+).*?:(.*?)(?=\n@|\nclass|\Z)'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            model_name = match.group(1)
            fields_str = match.group(2)
            
            fields = []
            if fields_str:
                field_pattern = r'(\w+)\s*:\s*([^\n]+)'
                field_matches = re.finditer(field_pattern, fields_str)
                for field_match in field_matches:
                    fields.append({
                        'name': field_match.group(1),
                        'type': field_match.group(2).strip()
                    })
            
            models.append({
                'name': model_name,
                'type': 'dataclass',
                'fields': fields,
                'file': str(file_path.relative_to(PROJECT_ROOT))
            })
    except Exception as e:
        print(f"Error extracting models from {file_path}: {e}")
    
    return models

def scan_backend_directory():
    """扫描后端目录"""
    print("🔍 扫描后端目录...")
    
    backend_dirs = [
        BACKEND_ROOT / 'wechat_backend',
        BACKEND_ROOT / 'wechat_backend' / 'ai_adapters',
        BACKEND_ROOT / 'wechat_backend' / 'views',
        BACKEND_ROOT / 'wechat_backend' / 'database',
        BACKEND_ROOT / 'src',
        BACKEND_ROOT / 'src' / 'api',
        BACKEND_ROOT / 'src' / 'services',
        BACKEND_ROOT / 'src' / 'models',
    ]
    
    for directory in backend_dirs:
        if not directory.exists():
            continue
            
        for file_path in directory.glob('*.py'):
            if file_path.name.startswith('__'):
                continue
            
            print(f"  📄 分析：{file_path.relative_to(PROJECT_ROOT)}")
            
            # 提取 API 端点
            if 'views' in str(file_path) or file_path.name == 'views.py':
                api_endpoints.extend(extract_api_endpoints_from_views(file_path))
            
            # 提取函数定义
            function_definitions.extend(extract_function_definitions(file_path))
            
            # 提取类定义
            class_definitions.extend(extract_class_definitions(file_path))
            
            # 提取导入关系
            imports = extract_import_relationships(file_path)
            for module, imported in imports.items():
                import_relationships[module].update(imported)
            
            # 提取数据模型
            data_models.extend(extract_data_models(file_path))

def scan_frontend_directory():
    """扫描前端目录"""
    print("🔍 扫描前端目录...")
    
    frontend_dirs = [
        FRONTEND_ROOT / 'services',
        FRONTEND_ROOT / 'pages' / 'index',
        FRONTEND_ROOT / 'api',
        FRONTEND_ROOT / 'utils',
    ]
    
    for directory in frontend_dirs:
        if not directory.exists():
            continue
            
        for file_path in directory.glob('*.js'):
            print(f"  📄 分析：{file_path.relative_to(PROJECT_ROOT)}")
            
            # 提取函数定义
            function_definitions.extend(extract_function_definitions(file_path))

def generate_architecture_report():
    """生成架构报告"""
    print("\n📊 生成架构报告...")
    
    report = {
        'summary': {
            'total_api_endpoints': len(api_endpoints),
            'total_functions': len(function_definitions),
            'total_classes': len(class_definitions),
            'total_data_models': len(data_models),
            'total_import_relationships': len(import_relationships)
        },
        'api_endpoints': api_endpoints[:50],  # 限制数量
        'core_functions': [f for f in function_definitions if not f['name'].startswith('_')][:100],
        'core_classes': class_definitions[:50],
        'data_models': data_models[:50],
        'import_graph': {k: list(v)[:10] for k, v in list(import_relationships.items())[:30]}
    }
    
    return report

def generate_mermaid_diagram(report: Dict) -> str:
    """生成 Mermaid 架构图"""
    mermaid = ["# 项目架构总览\n\n```mermaid", "graph TB"]
    
    # 添加样式定义
    mermaid.append("    classDef api fill:#e1f5ff,stroke:#0066cc")
    mermaid.append("    classDef service fill:#fff4e1,stroke:#ff9900")
    mermaid.append("    classDef model fill:#f0e1ff,stroke:#9900cc")
    mermaid.append("    classDef frontend fill:#e1ffe1,stroke:#00cc00")
    mermaid.append("    classDef backend fill:#ffe1e1,stroke:#cc0000")
    
    # 前端模块
    mermaid.append("\n    subgraph Frontend[前端 - 微信小程序]")
    mermaid.append("        Pages[pages/ - 页面层]")
    mermaid.append("        Services[services/ - 服务层]")
    mermaid.append("        API[api/ - API 调用]")
    mermaid.append("        Utils[utils/ - 工具函数]")
    mermaid.append("    end")
    
    # 后端模块
    mermaid.append("\n    subgraph Backend[后端 - Flask API]")
    mermaid.append("        Views[views.py - API 路由层]")
    mermaid.append("        Adapters[ai_adapters/ - AI 适配器]")
    mermaid.append("        Services[services/ - 业务服务]")
    mermaid.append("        Models[models/ - 数据模型]")
    mermaid.append("        Database[database/ - 数据库]")
    mermaid.append("    end")
    
    # 外部服务
    mermaid.append("\n    subgraph External[外部服务]")
    mermaid.append("        Doubao[豆包 AI API]")
    mermaid.append("        DeepSeek[DeepSeek API]")
    mermaid.append("        Qwen[通义千问 API]")
    mermaid.append("        WeChat[微信小程序 API]")
    mermaid.append("    end")
    
    # 连接关系
    mermaid.append("\n    %% 前端调用关系")
    mermaid.append("    Pages --> Services")
    mermaid.append("    Services --> API")
    mermaid.append("    API -->|HTTP/HTTPS| Views")
    
    mermaid.append("\n    %% 后端内部调用")
    mermaid.append("    Views --> Adapters")
    mermaid.append("    Views --> Services")
    mermaid.append("    Services --> Models")
    mermaid.append("    Models --> Database")
    
    mermaid.append("\n    %% 后端调用外部服务")
    mermaid.append("    Adapters --> Doubao")
    mermaid.append("    Adapters --> DeepSeek")
    mermaid.append("    Adapters --> Qwen")
    
    mermaid.append("\n    %% 样式应用")
    mermaid.append("    class Pages,Services,API,Utils frontend")
    mermaid.append("    class Views,Adapters,Services,Models,Database backend")
    mermaid.append("    class Doubao,DeepSeek,Qwen,WeChat service")
    
    mermaid.append("```")
    
    return "\n".join(mermaid)

def generate_data_flow_diagram() -> str:
    """生成数据流图"""
    mermaid = ["\n## 诊断功能数据流\n\n```mermaid", "sequenceDiagram"]
    
    mermaid.append("    participant User as 用户")
    mermaid.append("    participant Frontend as 前端小程序")
    mermaid.append("    participant API as 后端 API")
    mermaid.append("    participant NxM as NxM 引擎")
    mermaid.append("    participant Adapter as AI 适配器")
    mermaid.append("    participant AI as AI 平台")
    mermaid.append("    participant DB as 数据库")
    
    mermaid.append("\n    User->>Frontend: 输入品牌名称")
    mermaid.append("    Frontend->>Frontend: 选择 AI 模型")
    mermaid.append("    Frontend->>API: POST /api/perform-brand-test")
    mermaid.append("    API->>API: 验证输入参数")
    mermaid.append("    API->>API: 生成 execution_id")
    mermaid.append("    API->>NxM: 启动异步任务")
    mermaid.append("    API-->>Frontend: 返回 execution_id")
    
    mermaid.append("\n    loop 轮询状态 (800ms)")
    mermaid.append("        Frontend->>API: GET /test/status/{execution_id}")
    mermaid.append("        API-->>Frontend: 返回进度状态")
    mermaid.append("    end")
    
    mermaid.append("\n    NxM->>NxM: 解析问题模板")
    mermaid.append("    NxM->>Adapter: 创建 AI 客户端")
    mermaid.append("    Adapter->>Adapter: 构建 Prompt")
    mermaid.append("    Note over Adapter: brand_name, competitors, question")
    mermaid.append("    Adapter->>AI: 发送 API 请求")
    mermaid.append("    AI-->>Adapter: 返回 AI 响应")
    mermaid.append("    Adapter->>Adapter: 解析 GEO JSON")
    mermaid.append("    Adapter->>NxM: 返回结果")
    
    mermaid.append("\n    NxM->>DB: 保存测试结果")
    mermaid.append("    NxM->>API: 更新 execution_store")
    mermaid.append("    API-->>Frontend: 返回完成状态")
    mermaid.append("    Frontend->>Frontend: 跳转结果页")
    
    mermaid.append("```")
    
    return "\n".join(mermaid)

def generate_parameter_flow_diagram() -> str:
    """生成参数传递流程图"""
    mermaid = ["\n## 核心参数传递流程\n\n```mermaid", "graph LR"]
    
    mermaid.append("    subgraph FrontendParams[前端参数]")
    mermaid.append("        FP1[brandName: 品牌名称]")
    mermaid.append("        FP2[competitorBrands: 竞品列表]")
    mermaid.append("        FP3[selectedModels: AI 模型]")
    mermaid.append("        FP4[customQuestions: 自定义问题]")
    mermaid.append("    end")
    
    mermaid.append("\n    subgraph APIParams[API 参数]")
    mermaid.append("        AP1[brand_list: Array]")
    mermaid.append("        AP2[selectedModels: Array]")
    mermaid.append("        AP3[custom_question: String]")
    mermaid.append("    end")
    
    mermaid.append("\n    subgraph NxMParams[NxM 引擎参数]")
    mermaid.append("        NP1[main_brand: String]")
    mermaid.append("        NP2[competitor_brands: Array]")
    mermaid.append("        NP3[selected_models: Array]")
    mermaid.append("        NP4[raw_questions: Array]")
    mermaid.append("    end")
    
    mermaid.append("\n    subgraph TemplateParams[模板参数]")
    mermaid.append("        TP1[brand_name: String ✅]")
    mermaid.append("        TP2[competitors: String ✅]")
    mermaid.append("        TP3[question: String ✅]")
    mermaid.append("    end")
    
    mermaid.append("\n    FP1 --> AP1")
    mermaid.append("    FP2 --> AP1")
    mermaid.append("    FP3 --> AP2")
    mermaid.append("    FP4 --> AP3")
    
    mermaid.append("    AP1 --> NP1")
    mermaid.append("    AP1 --> NP2")
    mermaid.append("    AP2 --> NP3")
    mermaid.append("    AP3 --> NP4")
    
    mermaid.append("    NP1 --> TP1")
    mermaid.append("    NP2 --> TP2")
    mermaid.append("    NP4 --> TP3")
    
    mermaid.append("\n    classDef frontend fill:#e1ffe1,stroke:#00cc00")
    mermaid.append("    classDef api fill:#e1f5ff,stroke:#0066cc")
    mermaid.append("    classDef nxm fill:#fff4e1,stroke:#ff9900")
    mermaid.append("    classDef template fill:#f0e1ff,stroke:#9900cc")
    
    mermaid.append("    class FP1,FP2,FP3,FP4 frontend")
    mermaid.append("    class AP1,AP2,AP3 api")
    mermaid.append("    class NP1,NP2,NP3,NP4 nxm")
    mermaid.append("    class TP1,TP2,TP3 template")
    
    mermaid.append("```")
    
    return "\n".join(mermaid)

def main():
    """主函数"""
    print("="*70)
    print("项目架构分析工具")
    print("="*70)
    print()
    
    # 扫描后端
    scan_backend_directory()
    
    # 扫描前端
    scan_frontend_directory()
    
    # 生成报告
    report = generate_architecture_report()
    
    # 保存 JSON 报告
    report_file = PROJECT_ROOT / 'docs' / 'architecture_analysis.json'
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON 报告已保存：{report_file}")
    
    # 生成 Mermaid 图表
    mermaid_content = []
    mermaid_content.append("# 项目架构可视化总览\n")
    mermaid_content.append(f"**生成时间**: {__import__('datetime').datetime.now().isoformat()}\n")
    mermaid_content.append(f"**文件统计**: {report['summary']}\n")
    mermaid_content.append(generate_mermaid_diagram(report))
    mermaid_content.append(generate_data_flow_diagram())
    mermaid_content.append(generate_parameter_flow_diagram())
    
    # 保存 Markdown 报告
    md_file = PROJECT_ROOT / 'docs' / '2026-02-23_项目架构可视化总览.md'
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(mermaid_content))
    print(f"✅ Markdown 报告已保存：{md_file}")
    
    # 打印摘要
    print("\n" + "="*70)
    print("架构分析摘要")
    print("="*70)
    print(f"API 端点数量：{report['summary']['total_api_endpoints']}")
    print(f"函数定义数量：{report['summary']['total_functions']}")
    print(f"类定义数量：{report['summary']['total_classes']}")
    print(f"数据模型数量：{report['summary']['total_data_models']}")
    print(f"导入关系数量：{report['summary']['total_import_relationships']}")
    print()

if __name__ == '__main__':
    main()
