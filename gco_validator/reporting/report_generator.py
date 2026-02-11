"""
Report generation and visualization for GEO Content Quality Validator
"""
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any
import json
import csv
from io import StringIO
from datetime import datetime


class ReportFormat(Enum):
    """Supported report formats"""
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    TEXT = "text"


@dataclass
class ReportData:
    """Structure for report data"""
    brand_name: str
    test_date: str
    ai_models_tested: List[str]
    overall_score: float
    detailed_results: List[Dict[str, Any]]
    summary_stats: Dict[str, Any]


class ReportGenerator:
    """Generates reports in various formats"""
    
    def __init__(self):
        pass
    
    def generate_report(
        self, 
        brand_name: str, 
        ai_models: List[str], 
        overall_score: float, 
        detailed_results: List[Dict[str, Any]]
    ) -> ReportData:
        """Generate report data structure"""
        # Calculate summary statistics
        summary_stats = self._calculate_summary_stats(detailed_results)
        
        return ReportData(
            brand_name=brand_name,
            test_date=datetime.now().isoformat(),
            ai_models_tested=ai_models,
            overall_score=overall_score,
            detailed_results=detailed_results,
            summary_stats=summary_stats
        )
    
    def format_report(self, report_data: ReportData, format_type: ReportFormat) -> str:
        """Format the report in the specified format"""
        if format_type == ReportFormat.JSON:
            return self._format_json(report_data)
        elif format_type == ReportFormat.CSV:
            return self._format_csv(report_data)
        elif format_type == ReportFormat.HTML:
            return self._format_html(report_data)
        elif format_type == ReportFormat.TEXT:
            return self._format_text(report_data)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _calculate_summary_stats(self, detailed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics from detailed results"""
        if not detailed_results:
            return {}
        
        # Calculate averages
        total_accuracy = sum(r.get('accuracy', 0) for r in detailed_results)
        total_completeness = sum(r.get('completeness', 0) for r in detailed_results)
        total_overall = sum(r.get('score', 0) for r in detailed_results)
        
        # Group by AI model
        model_scores = {}
        for result in detailed_results:
            model = result.get('aiModel', 'unknown')
            if model not in model_scores:
                model_scores[model] = {'scores': [], 'count': 0}
            model_scores[model]['scores'].append(result.get('score', 0))
            model_scores[model]['count'] += 1
        
        # Calculate per-model averages
        model_averages = {}
        for model, data in model_scores.items():
            model_averages[model] = sum(data['scores']) / len(data['scores'])
        
        return {
            'total_tests': len(detailed_results),
            'average_accuracy': total_accuracy / len(detailed_results) if detailed_results else 0,
            'average_completeness': total_completeness / len(detailed_results) if detailed_results else 0,
            'average_overall': total_overall / len(detailed_results) if detailed_results else 0,
            'model_performance': model_averages,
            'top_performing_model': max(model_averages.items(), key=lambda x: x[1])[0] if model_averages else None,
            'bottom_performing_model': min(model_averages.items(), key=lambda x: x[1])[0] if model_averages else None
        }
    
    def _format_json(self, report_data: ReportData) -> str:
        """Format report as JSON"""
        return json.dumps({
            'brand_name': report_data.brand_name,
            'test_date': report_data.test_date,
            'ai_models_tested': report_data.ai_models_tested,
            'overall_score': report_data.overall_score,
            'summary_stats': report_data.summary_stats,
            'detailed_results': report_data.detailed_results
        }, indent=2)
    
    def _format_csv(self, report_data: ReportData) -> str:
        """Format report as CSV"""
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'AI_Model', 'Question', 'Response', 'Accuracy', 
            'Completeness', 'Score', 'Tokens_Used', 'Latency', 'Category'
        ])
        
        # Write data rows
        for result in report_data.detailed_results:
            writer.writerow([
                result.get('aiModel', ''),
                result.get('question', ''),
                result.get('response', ''),
                result.get('accuracy', ''),
                result.get('completeness', ''),
                result.get('score', ''),
                result.get('tokens_used', ''),
                result.get('latency', ''),
                result.get('category', '')
            ])
        
        return output.getvalue()
    
    def _format_html(self, report_data: ReportData) -> str:
        """Format report as HTML"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>GEO Content Quality Report - {report_data.brand_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .high-score {{ color: green; font-weight: bold; }}
        .low-score {{ color: red; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>GEO Content Quality Report</h1>
    <div class="summary">
        <h2>Summary for {report_data.brand_name}</h2>
        <p><strong>Test Date:</strong> {report_data.test_date}</p>
        <p><strong>Overall Score:</strong> <span class="{'high-score' if report_data.overall_score >= 70 else 'low-score' if report_data.overall_score < 50 else ''}">{report_data.overall_score:.2f}</span>/100</p>
        <p><strong>AI Models Tested:</strong> {', '.join(report_data.ai_models_tested)}</p>
        <p><strong>Total Tests:</strong> {report_data.summary_stats.get('total_tests', 0)}</p>
    </div>
    
    <h2>Detailed Results</h2>
    <table>
        <thead>
            <tr>
                <th>AI Model</th>
                <th>Question</th>
                <th>Score</th>
                <th>Accuracy</th>
                <th>Completeness</th>
                <th>Category</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for result in report_data.detailed_results:
            score_class = 'high-score' if result.get('score', 0) >= 70 else 'low-score' if result.get('score', 0) < 50 else ''
            html += f"""
            <tr>
                <td>{result.get('aiModel', '')}</td>
                <td>{result.get('question', '')[:50]}...</td>
                <td class="{score_class}">{result.get('score', 0):.1f}</td>
                <td>{result.get('accuracy', 0):.1f}</td>
                <td>{result.get('completeness', 0):.1f}</td>
                <td>{result.get('category', '')}</td>
            </tr>
"""
        
        html += """
        </tbody>
    </table>
</body>
</html>
"""
        
        return html
    
    def _format_text(self, report_data: ReportData) -> str:
        """Format report as plain text"""
        text = f"GEO Content Quality Report\n"
        text += f"==========================\n\n"
        text += f"Brand: {report_data.brand_name}\n"
        text += f"Test Date: {report_data.test_date}\n"
        text += f"Overall Score: {report_data.overall_score:.2f}/100\n"
        text += f"AI Models Tested: {', '.join(report_data.ai_models_tested)}\n"
        text += f"Total Tests: {report_data.summary_stats.get('total_tests', 0)}\n\n"
        
        text += "Detailed Results:\n"
        text += "-" * 80 + "\n"
        
        for result in report_data.detailed_results:
            text += f"Model: {result.get('aiModel', '')}\n"
            text += f"Question: {result.get('question', '')}\n"
            text += f"Score: {result.get('score', 0):.1f} (Acc: {result.get('accuracy', 0):.1f}, Comp: {result.get('completeness', 0):.1f})\n"
            text += f"Category: {result.get('category', '')}\n"
            text += "-" * 40 + "\n"
        
        return text


class ResultVisualizer:
    """Provides visualization capabilities for test results"""
    
    def __init__(self):
        pass
    
    def generate_performance_chart(self, results: List[Dict[str, Any]]) -> str:
        """Generate a simple text-based performance chart"""
        # Group results by AI model
        model_scores = {}
        for result in results:
            model = result.get('aiModel', 'unknown')
            if model not in model_scores:
                model_scores[model] = []
            model_scores[model].append(result.get('score', 0))
        
        # Calculate average scores
        avg_scores = {model: sum(scores)/len(scores) for model, scores in model_scores.items()}
        
        # Generate text chart
        chart = "AI Model Performance Chart\n"
        chart += "=" * 30 + "\n"
        
        for model, avg_score in sorted(avg_scores.items(), key=lambda x: x[1], reverse=True):
            bar_length = int(avg_score / 10)  # Scale to 10 chars for 100%
            chart += f"{model:<20} [{'█' * bar_length}{'░' * (10-bar_length)}] {avg_score:.1f}\n"
        
        return chart