#!/usr/bin/env python3
"""
P0-2 竞品遍历功能修复脚本 - 版本 2
使用行号精确插入
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到第 91 行（索引 90）："            # 外层循环：遍历问题"
# 在其前面插入品牌遍历代码

insert_line = 90  # 0-based index

# 构建新的代码块
new_code = '''            # P0-2 修复：遍历所有品牌（主品牌 + 竞品）
            all_brands = [main_brand] + (competitor_brands or [])
            api_logger.info(f"[NxM] 执行品牌数：{len(all_brands)}, 品牌列表：{all_brands}")

            # 外层循环：遍历品牌
            for brand in all_brands:
                # 中层循环：遍历问题
                for q_idx, question in enumerate(raw_questions):
                    # 内层循环：遍历模型
                    for model_info in selected_models:
                        model_name = model_info.get('name', '')

                        # 检查模型是否可用（熔断器）
                        if not scheduler.is_model_available(model_name):
                            api_logger.warning(f"[NxM] 模型 {model_name} 已熔断，跳过")
                            completed += 1
                            scheduler.update_progress(completed, total_tasks, 'ai_fetching')
                            continue

                        try:
                            # P0 修复：直接使用 Config 类获取 API Key，避免循环依赖
                            from config import Config

                            # 创建 AI 客户端
                            client = AIAdapterFactory.create(model_name)
                            api_key = Config.get_api_key(model_name)

                            if not api_key:
                                raise ValueError(f"模型 {model_name} API Key 未配置")

                            # 构建提示词
                            # P0-2 修复：模板需要 brand_name, competitors, question 三个参数
                            # 竞品是当前品牌，其他品牌是竞争对手
                            current_competitors = [b for b in all_brands if b != brand]
                            prompt = GEO_PROMPT_TEMPLATE.format(
                                brand_name=brand,  # P0-2 修复：使用当前遍历的品牌
                                competitors=', '.join(current_competitors) if current_competitors else '无',
                                question=question
                            )

'''

# 删除原来的 3 行（第 91-93 行）
# 然后插入新代码
# 实际上我们需要替换第 91-120 行的整个循环结构

# 更简单的方法：找到特定行并替换
for i, line in enumerate(lines):
    if '# 外层循环：遍历问题' in line and i > 85 and i < 95:
        # 找到这一行，替换整个循环结构
        # 删除从这一行到 prompt = GEO_PROMPT_TEMPLATE.format( 之后的行
        
        # 找到循环结束的位置
        start_line = i
        # 找到 prompt = GEO_PROMPT_TEMPLATE.format( 这一行
        for j in range(i, min(i+50, len(lines))):
            if "prompt = GEO_PROMPT_TEMPLATE.format(" in lines[j]:
                # 替换从 start_line 到 j+4 行（prompt 的结束行）
                lines[start_line:j+5] = [new_code]
                break
        break

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ P0-2 竞品遍历功能修复完成！")
