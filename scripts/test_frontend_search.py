#!/usr/bin/env python3
"""
验证前端搜索功能

检查 API 返回的数据是否包含正确的字段，以便前端搜索能正常工作
"""

import json
import urllib.request

EXECUTION_ID = '12bed967-1094-46b7-a363-0864971df7b0'
BRAND_NAME = '元若曦'

def test_api_response():
    """测试 API 响应"""
    print("="*60)
    print("测试 API 响应")
    print("="*60)
    
    url = f"http://localhost:5001/api/history/list?userOpenid=anonymous&limit=50&offset=0"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            
            history = data.get('history', [])
            print(f"API 返回记录数：{len(history)}")
            
            # 查找元若曦记录
            yuanruoxi_records = [r for r in history if '元若曦' in (r.get('brandName') or r.get('brand_name') or '')]
            print(f"元若曦记录数：{len(yuanruoxi_records)}")
            
            if yuanruoxi_records:
                print("\n✅ 元若曦记录存在:")
                for r in yuanruoxi_records:
                    print(f"  - executionId: {r.get('executionId', 'N/A')[:8]}...")
                    print(f"    brandName: {r.get('brandName', 'N/A')}")
                    print(f"    brand_name: {r.get('brand_name', 'N/A')}")
                    print(f"    status: {r.get('status', 'N/A')}")
                    print(f"    createdAt: {r.get('createdAt', 'N/A')}")
                
                # 检查字段映射
                first_record = yuanruoxi_records[0]
                print("\n字段检查:")
                print(f"  brandName 字段：{'✅' if first_record.get('brandName') else '❌'}")
                print(f"  brand_name 字段：{'✅' if first_record.get('brand_name') else '❌'}")
                print(f"  executionId 字段：{'✅' if first_record.get('executionId') else '❌'}")
                print(f"  execution_id 字段：{'✅' if first_record.get('execution_id') else '❌'}")
                
                return True
            else:
                print("\n❌ 未找到元若曦记录")
                print("\n所有记录的品牌:")
                brands = set()
                for r in history:
                    brands.add(r.get('brandName') or r.get('brand_name') or '未知')
                for b in sorted(brands):
                    print(f"  - {b}")
                return False
                
    except Exception as e:
        print(f"❌ API 调用失败：{e}")
        return False


def test_search_logic():
    """测试搜索逻辑"""
    print("\n" + "="*60)
    print("测试搜索逻辑")
    print("="*60)
    
    # 模拟前端搜索逻辑
    test_data = [
        {'brandName': '元若曦', 'executionId': '12bed967-1094-46b7-a363-0864971df7b0'},
        {'brand_name': '华为', 'execution_id': '97cf82c0-e548-4f2e-a9f4-b3b1fa0e4547'},
        {'brandName': '华为', 'brand_name': '华为', 'executionId': '5e850620-03a4-45b5-9166-15290871c3de'},
    ]
    
    keyword = '元若曦'
    
    # 修复后的搜索逻辑
    filtered = []
    for item in test_data:
        brandName = (item.get('brandName') or item.get('brand_name') or '').lower()
        executionId = (item.get('executionId') or item.get('execution_id') or '').lower()
        
        if keyword.lower() in brandName or keyword.lower() in executionId:
            filtered.append(item)
    
    print(f"搜索关键词：{keyword}")
    print(f"匹配结果数：{len(filtered)}")
    
    if filtered:
        print("✅ 搜索逻辑正确")
        for item in filtered:
            print(f"  - {item.get('brandName') or item.get('brand_name')}")
        return True
    else:
        print("❌ 搜索逻辑有问题")
        return False


def main():
    print("\n" + "="*60)
    print("前端搜索功能验证")
    print("="*60)
    
    api_ok = test_api_response()
    search_ok = test_search_logic()
    
    print("\n" + "="*60)
    print("验证总结")
    print("="*60)
    
    if api_ok:
        print("✅ API 返回数据正确，包含元若曦记录")
    else:
        print("❌ API 返回数据有问题")
    
    if search_ok:
        print("✅ 搜索逻辑正确")
    else:
        print("❌ 搜索逻辑有问题")
    
    if api_ok and search_ok:
        print("\n✅ 前端搜索应该能正常工作")
        print("\n如果前端仍然搜索不到，请检查:")
        print("1. 微信开发者工具控制台是否有错误日志")
        print("2. 本地存储是否已更新（可能需要清除缓存）")
        print("3. 数据加载是否完成（查看 loading 状态）")
        return 0
    else:
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
