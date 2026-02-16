"""
测试新的 /action/recommendations API 端点
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import json
from unittest.mock import Mock, patch
from flask import Flask
from wechat_backend.views import wechat_bp


def test_recommendations_endpoint():
    """测试推荐API端点"""

    print("=== 测试 /action/recommendations API 端点 ===")

    # 创建Flask应用并注册蓝图
    app = Flask(__name__)
    app.register_blueprint(wechat_bp)

    # 准备测试数据
    test_data = {
        "source_intelligence": {
            "source_pool": [
                {
                    "id": "zhihu",
                    "url": "https://www.zhihu.com",
                    "site_name": "知乎",
                    "citation_count": 15,
                    "domain_authority": "High"
                },
                {
                    "id": "baidu_baike",
                    "url": "https://baike.baidu.com",
                    "site_name": "百度百科",
                    "citation_count": 12,
                    "domain_authority": "High"
                }
            ],
            "citation_rank": ["zhihu", "baidu_baike"]
        },
        "evidence_chain": [
            {
                "negative_fragment": "德施曼智能锁质量不过关，多次出现故障",
                "associated_url": "https://www.zhihu.com/question/123456",
                "source_name": "知乎",
                "risk_level": "High"
            }
        ],
        "brand_name": "德施曼"
    }

    with app.test_client() as client:
        # 发送POST请求到新端点
        response = client.post(
            '/action/recommendations',
            data=json.dumps(test_data),
            content_type='application/json'
        )

        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            response_data = response.get_json()
            print(f"响应状态: {response_data.get('status')}")
            print(f"建议数量: {response_data.get('count')}")

            recommendations = response_data.get('recommendations', [])
            print(f"获取到 {len(recommendations)} 条建议")

            # 显示第一条建议的详细信息
            if recommendations:
                first_rec = recommendations[0]
                print(f"第一条建议标题: {first_rec.get('title')}")
                print(f"优先级: {first_rec.get('priority')}")
                print(f"类型: {first_rec.get('type')}")
                print(f"紧急程度: {first_rec.get('urgency')}")

            print("✓ API端点测试成功")
            return True
        else:
            print(f"✗ API端点测试失败，状态码: {response.status_code}")
            print(f"响应内容: {response.get_data(as_text=True)}")
            return False


def test_recommendations_endpoint_no_negative():
    """测试无负面内容时的API端点"""

    print("\n=== 测试无负面内容时的 /action/recommendations API 端点 ===")

    # 创建Flask应用并注册蓝图
    app = Flask(__name__)
    app.register_blueprint(wechat_bp)

    # 准备测试数据 - 无负面内容
    test_data = {
        "source_intelligence": {
            "source_pool": [
                {
                    "id": "zhihu",
                    "url": "https://www.zhihu.com",
                    "site_name": "知乎",
                    "citation_count": 15,
                    "domain_authority": "High"
                }
            ],
            "citation_rank": ["zhihu"]
        },
        "evidence_chain": [],  # 无负面内容
        "brand_name": "德施曼"
    }

    with app.test_client() as client:
        # 发送POST请求到新端点
        response = client.post(
            '/action/recommendations',
            data=json.dumps(test_data),
            content_type='application/json'
        )

        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            response_data = response.get_json()
            print(f"响应状态: {response_data.get('status')}")
            print(f"建议数量: {response_data.get('count')}")

            recommendations = response_data.get('recommendations', [])
            print(f"获取到 {len(recommendations)} 条建议")

            # 检查是否生成了品牌强化建议
            brand_strengthening_count = sum(
                1 for rec in recommendations
                if rec.get('type') == 'brand_strengthening'
            )
            print(f"品牌强化建议数量: {brand_strengthening_count}")

            if brand_strengthening_count > 0:
                print("✓ 正确生成了品牌强化建议")
            else:
                print("✗ 未生成品牌强化建议")

            print("✓ 无负面内容API端点测试成功")
            return True
        else:
            print(f"✗ 无负面内容API端点测试失败，状态码: {response.status_code}")
            print(f"响应内容: {response.get_data(as_text=True)}")
            return False


def test_invalid_input():
    """测试无效输入"""

    print("\n=== 测试无效输入处理 ===")

    # 创建Flask应用并注册蓝图
    app = Flask(__name__)
    app.register_blueprint(wechat_bp)

    # 准备无效数据
    invalid_data = {
        "source_intelligence": "invalid_type",  # 应该是字典
        "evidence_chain": "invalid_type",       # 应该是列表
        "brand_name": "德施曼"
    }

    with app.test_client() as client:
        # 发送POST请求到新端点
        response = client.post(
            '/action/recommendations',
            data=json.dumps(invalid_data),
            content_type='application/json'
        )

        print(f"响应状态码: {response.status_code}")

        if response.status_code == 400:
            print("✓ 正确处理了无效输入")
            return True
        else:
            print(f"✗ 未正确处理无效输入，期望400，得到{response.status_code}")
            return False


def run_endpoint_tests():
    """运行端点测试"""

    print("开始运行API端点测试...\n")

    success_count = 0
    total_tests = 3

    if test_recommendations_endpoint():
        success_count += 1

    if test_recommendations_endpoint_no_negative():
        success_count += 1

    if test_invalid_input():
        success_count += 1

    print(f"\n=== 端点测试总结 ===")
    print(f"通过测试: {success_count}/{total_tests}")

    if success_count == total_tests:
        print("✓ 所有端点测试通过！")
        return True
    else:
        print("✗ 部分端点测试失败")
        return False


from flask_cors import CORS

# Add a minimal Flask app instance for the CLI to recognize
app = Flask(__name__)
app.register_blueprint(wechat_bp)

# Enable CORS to allow requests from WeChat Mini Program
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}})


if __name__ == "__main__":
    # Explicitly specify host and port to align with frontend contract
    app.run(host='0.0.0.0', port=5000, debug=True)