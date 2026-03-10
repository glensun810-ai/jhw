#!/usr/bin/env python3
"""
API 文档生成脚本

从 OpenAPI 规范生成：
1. Markdown 文档
2. HTML 文档
3. 类型定义文件

使用方法:
    python generate-docs.py --input docs/api-spec.yaml --output docs/api
    python generate-docs.py --input docs/api-spec.yaml --format html --output docs/api
    python generate-docs.py --input docs/api-spec.yaml --format types --output miniprogram/types

作者：系统架构组
日期：2026-03-01
版本：1.0
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    print("错误：请安装 PyYAML: pip install pyyaml")
    sys.exit(1)


class APIDocGenerator:
    """API 文档生成器"""
    
    def __init__(self, spec_path: str):
        """初始化生成器"""
        self.spec_path = spec_path
        self.spec = self._load_spec()
        
    def _load_spec(self) -> Dict[str, Any]:
        """加载 OpenAPI 规范"""
        with open(self.spec_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def generate_markdown(self, output_path: str) -> None:
        """生成 Markdown 文档"""
        info = self.spec.get('info', {})
        paths = self.spec.get('paths', {})
        components = self.spec.get('components', {})
        
        md = []
        
        # 标题
        md.append(f"# {info.get('title', 'API 文档')}\n")
        md.append(f"**版本**: {info.get('version', '1.0.0')}\n")
        md.append(f"**最后更新**: {datetime.now().strftime('%Y-%m-%d')}\n")
        
        # 描述
        if info.get('description'):
            md.append("\n## 概述\n")
            md.append(info['description'])
        
        # 服务器
        servers = self.spec.get('servers', [])
        if servers:
            md.append("\n## 服务器\n")
            for server in servers:
                md.append(f"- **{server.get('description', '生产环境')}**: `{server.get('url')}`")
        
        # 认证
        md.append("\n## 认证\n")
        md.append("大部分接口需要 Bearer Token 认证\n")
        md.append("```http")
        md.append("Authorization: Bearer <your_token>")
        md.append("```\n")
        
        # API 端点
        md.append("\n## API 端点\n")
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    md.append(self._generate_endpoint_md(path, method.upper(), operation))
        
        # Schema 定义
        schemas = components.get('schemas', {})
        if schemas:
            md.append("\n## 数据模型\n")
            for name, schema in schemas.items():
                md.append(self._generate_schema_md(name, schema))
        
        # 错误码
        md.append("\n## 错误码\n")
        md.append("| 状态码 | 说明 |\n|--------|------|")
        md.append("| 200 | 成功 |\n| 400 | 请求参数错误 |\n| 401 | 未认证 |")
        md.append("| 403 | 权限不足 |\n| 404 | 资源不存在 |\n| 429 | 请求频率超限 |\n| 500 | 服务器内部错误 |")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md))
        
        print(f"✅ Markdown 文档已生成：{output_path}")
    
    def _generate_endpoint_md(self, path: str, method: str, operation: Dict[str, Any]) -> str:
        """生成端点 Markdown"""
        md = []
        
        summary = operation.get('summary', '')
        description = operation.get('description', '')
        operation_id = operation.get('operationId', '')
        
        md.append(f"\n### {method} {path}\n")
        md.append(f"**{summary}**\n")
        
        if description:
            md.append(f"{description}\n")
        
        if operation_id:
            md.append(f"**操作 ID**: `{operation_id}`\n")
        
        # 参数
        parameters = operation.get('parameters', [])
        if parameters:
            md.append("\n**请求参数**:\n")
            md.append("| 参数 | 位置 | 类型 | 必填 | 说明 |")
            md.append("|------|------|------|------|------|")
            for param in parameters:
                name = param.get('name', '')
                location = param.get('in', '')
                required = '是' if param.get('required', False) else '否'
                schema = param.get('schema', {})
                param_type = schema.get('type', 'string')
                desc = param.get('description', '')
                md.append(f"| {name} | {location} | {param_type} | {required} | {desc} |")
        
        # 响应
        responses = operation.get('responses', {})
        if responses:
            md.append("\n**响应**:\n")
            for status, response in responses.items():
                desc = response.get('description', '')
                md.append(f"- **{status}**: {desc}")
        
        return '\n'.join(md)
    
    def _generate_schema_md(self, name: str, schema: Dict[str, Any]) -> str:
        """生成 Schema Markdown"""
        md = []
        
        md.append(f"\n### {name}\n")
        
        # 类型
        schema_type = schema.get('type', 'object')
        md.append(f"**类型**: {schema_type}\n")
        
        # 属性
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        if properties:
            md.append("\n**属性**:\n")
            md.append("| 属性 | 类型 | 必填 | 说明 |")
            md.append("|------|------|------|------|")
            
            for prop_name, prop_schema in properties.items():
                prop_type = prop_schema.get('type', 'any')
                is_required = '是' if prop_name in required else '否'
                description = prop_schema.get('description', '')
                
                # 处理枚举
                if 'enum' in prop_schema:
                    enum_values = prop_schema['enum']
                    description = f"枚举：{', '.join(enum_values)}. {description}"
                
                # 处理引用
                if '$ref' in prop_schema:
                    ref = prop_schema['$ref']
                    ref_name = ref.split('/')[-1]
                    prop_type = f"[{ref_name}](#{ref_name.lower()})"
                
                md.append(f"| {prop_name} | {prop_type} | {is_required} | {description} |")
        
        return '\n'.join(md)
    
    def generate_html(self, output_path: str) -> None:
        """生成 HTML 文档"""
        # 简单实现，实际使用可以使用 sphinx 或其他工具
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>品牌战略洞察报告 API</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        h3 { color: #666; border-left: 4px solid #007bff; padding-left: 10px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f5f5f5; font-weight: 600; }
        code { background-color: #f5f5f5; padding: 2px 6px; border-radius: 3px; }
        .endpoint { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .method { display: inline-block; padding: 4px 8px; border-radius: 3px; font-weight: bold; margin-right: 10px; }
        .GET { background-color: #28a745; color: white; }
        .POST { background-color: #007bff; color: white; }
        .PUT { background-color: #ffc107; color: black; }
        .DELETE { background-color: #dc3545; color: white; }
    </style>
</head>
<body>
    <h1>""" + self.spec.get('info', {}).get('title', 'API 文档') + """</h1>
    <p><strong>版本</strong>: """ + str(self.spec.get('info', {}).get('version', '1.0.0')) + """</p>
    <p><strong>最后更新</strong>: """ + datetime.now().strftime('%Y-%m-%d') + """</p>
    
    <div id="content"></div>
    
    <script>
        // 简单 Markdown 渲染
        fetch('api-docs.md')
            .then(r => r.text())
            .then(md => {
                // 这里可以添加 Markdown 解析逻辑
                document.getElementById('content').innerHTML = md.replace(/\\n/g, '<br>');
            });
    </script>
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ HTML 文档已生成：{output_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='API 文档生成器')
    parser.add_argument('--input', '-i', required=True, help='OpenAPI 规范文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出目录')
    parser.add_argument('--format', '-f', choices=['md', 'html', 'all'], default='all', help='输出格式')
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not os.path.exists(args.input):
        print(f"错误：文件不存在：{args.input}")
        sys.exit(1)
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 生成文档
    generator = APIDocGenerator(args.input)
    
    if args.format in ['md', 'all']:
        generator.generate_markdown(os.path.join(args.output, 'api-docs.md'))
    
    if args.format in ['html', 'all']:
        generator.generate_html(os.path.join(args.output, 'api-docs.html'))
    
    print("\n✅ 文档生成完成!")


if __name__ == '__main__':
    main()
