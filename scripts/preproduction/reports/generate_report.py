#!/usr/bin/env python3
"""
验证报告生成器
生成 Markdown 和 HTML 格式的验证报告
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any


class ReportGenerator:
    """验证报告生成器"""
    
    def __init__(self, results: Dict[str, List[Dict]], start_time: datetime, base_url: str = ''):
        self.results = results
        self.start_time = start_time
        self.end_time = datetime.now()
        self.base_url = base_url
    
    def generate(self) -> str:
        """生成报告文件"""
        os.makedirs('scripts/preproduction/reports', exist_ok=True)
        
        timestamp = self.start_time.strftime('%Y%m%d_%H%M%S')
        markdown_filename = f"scripts/preproduction/reports/stage1_validation_{timestamp}.md"
        html_filename = f"scripts/preproduction/reports/stage1_validation_{timestamp}.html"
        json_filename = f"scripts/preproduction/reports/stage1_validation_{timestamp}.json"
        
        markdown_content = self._generate_markdown()
        
        with open(markdown_filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        html_content = self._generate_html()
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        json_content = self._generate_json()
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_content, f, ensure_ascii=False, indent=2)
        
        return markdown_filename
    
    def _generate_markdown(self) -> str:
        """生成 Markdown 格式报告"""
        duration = (self.end_time - self.start_time).total_seconds() / 60
        
        lines = [
            "# 阶段一预发布验证报告",
            "",
            "## 基本信息",
            "",
            f"**生成时间**: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**验证开始**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**验证时长**: {duration:.1f} 分钟",
            f"**测试环境**: {self.base_url}",
            "",
            "## 验证结果概览",
            "",
            "| 验证项 | 通过 | 警告 | 失败 | 总计 |",
            "|--------|------|------|------|------|",
        ]
        
        totals = {}
        for category, results in self.results.items():
            if not results:
                continue
            
            passed = sum(1 for r in results if r.get('status') == '✅')
            warnings = sum(1 for r in results if r.get('status') == '⚠️')
            failed = sum(1 for r in results if r.get('status') == '❌')
            total = len(results)
            
            category_name = {
                'environment': '环境检查',
                'functional': '功能测试',
                'performance': '性能测试',
                'stability': '稳定性测试',
                'compatibility': '兼容性测试',
                'rollback': '回滚测试'
            }.get(category, category)
            
            lines.append(f"| {category_name} | {passed} | {warnings} | {failed} | {total} |")
            totals[category] = {'passed': passed, 'warnings': warnings, 'failed': failed, 'total': total}
        
        lines.extend(["", "## 详细结果", ""])
        
        if self.results.get('environment'):
            lines.extend(["### 1. 环境检查", ""])
            for r in self.results['environment']:
                lines.append(f"- {r['status']} **{r['check']}**: {r['details']}")
            lines.append("")
        
        if self.results.get('functional'):
            lines.extend(["### 2. 功能测试", ""])
            for r in self.results['functional']:
                lines.append(f"- {r['status']} **{r['test']}**: {r['details']}")
            lines.append("")
        
        if self.results.get('performance'):
            lines.extend(["### 3. 性能测试", ""])
            for r in self.results['performance']:
                lines.append(f"- {r['status']} **{r['test']}**: {r['details']}")
            lines.append("")
        
        if self.results.get('stability'):
            lines.extend(["### 4. 稳定性测试", ""])
            for r in self.results['stability']:
                lines.append(f"- {r['status']} **{r['test']}**: {r['details']}")
            lines.append("")
        
        if self.results.get('compatibility'):
            lines.extend(["### 5. 兼容性测试", ""])
            for r in self.results['compatibility']:
                lines.append(f"- {r['status']} **{r['test']}**: {r['details']}")
            lines.append("")
        
        if self.results.get('rollback'):
            lines.extend(["### 6. 回滚测试", ""])
            for r in self.results['rollback']:
                lines.append(f"- {r['status']} **{r['test']}**: {r['details']}")
            lines.append("")
        
        lines.extend(["## 结论", ""])
        
        total_failed = sum(t['failed'] for t in totals.values())
        total_warnings = sum(t['warnings'] for t in totals.values())
        total_passed = sum(t['passed'] for t in totals.values())
        total_tests = sum(t['total'] for t in totals.values())
        
        lines.append(f"**总计**: {total_tests} 项测试，{total_passed} 通过，{total_warnings} 警告，{total_failed} 失败")
        lines.append("")
        
        if total_failed == 0:
            if total_warnings == 0:
                lines.append("✅ **验证通过** - 所有检查项均通过，可以进入灰度发布。")
            else:
                lines.append("⚠️ **有条件通过** - 存在警告项，建议在灰度发布时重点关注。")
                lines.append("")
                lines.append("警告项列表:")
                for category, results in self.results.items():
                    for r in results:
                        if r.get('status') == '⚠️':
                            lines.append(f"- {category}: {r.get('test', r.get('check', 'unknown'))}")
        else:
            lines.append("❌ **验证失败** - 存在失败项，请修复后重新验证。")
            lines.append("")
            lines.append("失败项列表:")
            for category, results in self.results.items():
                for r in results:
                    if r.get('status') == '❌':
                        lines.append(f"- {category}: {r.get('test', r.get('check', 'unknown'))} - {r.get('details', '')}")
        
        lines.extend([
            "",
            "---",
            "",
            "## 附录",
            "",
            "### 验证人员",
            "",
            "- 测试执行：自动化脚本",
            "- 审核人员：__________",
            "- 批准人员：__________",
            "",
            "### 备注",
            "",
            "本报告由自动化验证系统生成，详细日志请查看项目目录。"
        ])
        
        return "\n".join(lines)
    
    def _generate_html(self) -> str:
        """生成 HTML 格式报告"""
        markdown_content = self._generate_markdown()
        
        html_content = self._markdown_to_html(markdown_content)
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>阶段一预发布验证报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #34495e;
            margin: 30px 0 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }}
        h3 {{
            color: #7f8c8d;
            margin: 20px 0 10px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .summary {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .pass {{ color: #27ae60; font-weight: bold; }}
        .fail {{ color: #e74c3c; font-weight: bold; }}
        .warning {{ color: #f39c12; font-weight: bold; }}
        .conclusion {{
            background: #d5f5e3;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #27ae60;
        }}
        .conclusion.fail {{
            background: #fadbd8;
            border-left-color: #e74c3c;
        }}
        .conclusion.warning {{
            background: #fdebd0;
            border-left-color: #f39c12;
        }}
        ul {{
            margin-left: 20px;
            margin-bottom: 15px;
        }}
        li {{
            margin-bottom: 5px;
        }}
        .timestamp {{
            color: #95a5a6;
            font-size: 0.9em;
            margin-top: 30px;
            border-top: 1px solid #eee;
            padding-top: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
    </div>
</body>
</html>
"""
    
    def _markdown_to_html(self, markdown_content: str) -> str:
        """简单 Markdown 转 HTML"""
        html = markdown_content
        
        html = html.replace('# ', '<h1>')
        html = html.replace('## ', '</h1>\n<h2>')
        html = html.replace('### ', '</h2>\n<h3>')
        html = html.replace('#### ', '</h3>\n<h4>')
        
        lines = html.split('\n')
        result = []
        in_table = False
        
        for line in lines:
            if line.startswith('|---'):
                continue
            if line.startswith('|') and not in_table:
                in_table = True
                result.append('<table>')
            if not line.startswith('|') and in_table:
                in_table = False
                result.append('</table>')
            
            if in_table:
                if line.startswith('|'):
                    cells = line.strip('|').split('|')
                    if 'th' not in ''.join(result[-3:]):
                        row = '<tr>' + ''.join(f'<th>{c.strip()}</th>' for c in cells) + '</tr>'
                    else:
                        row = '<tr>' + ''.join(f'<td>{c.strip()}</td>' for c in cells) + '</tr>'
                    result.append(row)
            else:
                if line.startswith('- '):
                    result.append(f'<li>{line[2:]}</li>')
                elif line.startswith('**') and '**' in line[2:]:
                    result.append(f'<p><strong>{line}</strong></p>')
                elif line:
                    result.append(f'<p>{line}</p>')
        
        if in_table:
            result.append('</table>')
        
        return '\n'.join(result)
    
    def _generate_json(self) -> Dict:
        """生成 JSON 格式报告"""
        duration = (self.end_time - self.start_time).total_seconds() / 60
        
        totals = {}
        for category, results in self.results.items():
            if not results:
                continue
            
            passed = sum(1 for r in results if r.get('status') == '✅')
            warnings = sum(1 for r in results if r.get('status') == '⚠️')
            failed = sum(1 for r in results if r.get('status') == '❌')
            total = len(results)
            
            totals[category] = {'passed': passed, 'warnings': warnings, 'failed': failed, 'total': total}
        
        total_failed = sum(t['failed'] for t in totals.values())
        total_warnings = sum(t['warnings'] for t in totals.values())
        total_passed = sum(t['passed'] for t in totals.values())
        
        if total_failed == 0:
            if total_warnings == 0:
                conclusion = 'passed'
            else:
                conclusion = 'warning'
        else:
            conclusion = 'failed'
        
        return {
            'metadata': {
                'generated_at': self.end_time.isoformat(),
                'started_at': self.start_time.isoformat(),
                'duration_minutes': round(duration, 2),
                'environment': self.base_url
            },
            'summary': {
                'total_tests': sum(t['total'] for t in totals.values()),
                'passed': total_passed,
                'warnings': total_warnings,
                'failed': total_failed,
                'conclusion': conclusion
            },
            'details': self.results,
            'totals_by_category': totals
        }


def main():
    """主函数 - 用于测试报告生成器"""
    sample_results = {
        'environment': [
            {'check': 'API 连通性', 'status': '✅', 'details': '响应时间：0.15s'},
            {'check': '数据库', 'status': '✅', 'details': '存在，大小：50.2MB'},
            {'check': '特性开关', 'status': '✅', 'details': '所有开关配置正确'}
        ],
        'functional': [
            {'test': '发起诊断', 'status': '✅', 'details': 'execution_id: test-123'},
            {'test': '状态轮询', 'status': '✅', 'details': '最终状态：completed'},
            {'test': '获取报告', 'status': '✅', 'details': '结果数：5'}
        ],
        'performance': [
            {'test': '单次诊断时间', 'status': '✅', 'details': '180.5 秒'},
            {'test': '并发 5 任务', 'status': '✅', 'details': '成功率：5/5'}
        ]
    }
    
    generator = ReportGenerator(
        results=sample_results,
        start_time=datetime.now(),
        base_url='http://localhost:5000'
    )
    
    filename = generator.generate()
    print(f"报告已生成：{filename}")


if __name__ == '__main__':
    main()
