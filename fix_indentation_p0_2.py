#!/usr/bin/env python3
"""
修复 P0-2 后的缩进问题
"""

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/nxm_execution_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复缩进：# 修复 3: 添加 AI 响应重试机制 及之后的代码
old_text = '''                            )


                        # 修复 3: 添加 AI 响应重试机制
                        max_retries = 2
                        retry_count = 0
                        response = None
                        geo_data = None
                        parse_error = None

                        while retry_count <= max_retries:
                            try:
                                # 调用 AI 接口
                                response = client.generate_response(
                                    prompt=prompt,
                                    api_key=api_key
                                )

                                # 解析 GEO 数据
                                geo_data, parse_error = parse_geo_with_validation(
                                    response,
                                    execution_id,
                                    q_idx,
                                    model_name
                                )

                                # 如果解析成功，跳出重试循环
                                if not parse_error and not geo_data.get('_error'):
                                    break

                                # 解析失败，记录日志并准备重试
                                api_logger.warning(f"[NxM] 解析失败，准备重试：{model_name}, Q{q_idx}, 尝试 {retry_count + 1}/{max_retries}")
                                retry_count += 1

                            except Exception as call_error:
                                api_logger.error(f"[NxM] AI 调用失败：{model_name}, Q{q_idx}: {call_error}")
                                retry_count += 1

                        # 检查最终结果
                        if not response or not geo_data or geo_data.get('_error'):
                            api_logger.error(f"[NxM] 重试耗尽，标记为失败：{model_name}, Q{q_idx}")
                            scheduler.record_model_failure(model_name)
                            # 仍然添加结果，但标记为失败
                            result = {
                                'brand': brand,  # P0-2 修复：使用当前遍历的品牌
                                'question': question,
                                'model': model_name,
                                'response': response,
                                'geo_data': geo_data or {'_error': 'AI 调用或解析失败'},
                                'timestamp': datetime.now().isoformat(),
                                '_failed': True
                            }
                            scheduler.add_result(result)
                            results.append(result)
                        else:
                            scheduler.record_model_success(model_name)

                            # 构建结果（确保所有字段都是 JSON 可序列化的）
                            result = {
                                'brand': brand,  # P0-2 修复：使用当前遍历的品牌
                                'question': question,
                                'model': model_name,
                                'response': response,
                                'geo_data': geo_data,
                                'timestamp': datetime.now().isoformat()
                            }

                            scheduler.add_result(result)
                            results.append(result)

                        # 更新进度
                        completed += 1
                        scheduler.update_progress(completed, total_tasks, 'ai_fetching')

                    except Exception as e:'''

new_text = '''                            )

                            # 修复 3: 添加 AI 响应重试机制
                            max_retries = 2
                            retry_count = 0
                            response = None
                            geo_data = None
                            parse_error = None

                            while retry_count <= max_retries:
                                try:
                                    # 调用 AI 接口
                                    response = client.generate_response(
                                        prompt=prompt,
                                        api_key=api_key
                                    )

                                    # 解析 GEO 数据
                                    geo_data, parse_error = parse_geo_with_validation(
                                        response,
                                        execution_id,
                                        q_idx,
                                        model_name
                                    )

                                    # 如果解析成功，跳出重试循环
                                    if not parse_error and not geo_data.get('_error'):
                                        break

                                    # 解析失败，记录日志并准备重试
                                    api_logger.warning(f"[NxM] 解析失败，准备重试：{model_name}, Q{q_idx}, 尝试 {retry_count + 1}/{max_retries}")
                                    retry_count += 1

                                except Exception as call_error:
                                    api_logger.error(f"[NxM] AI 调用失败：{model_name}, Q{q_idx}: {call_error}")
                                    retry_count += 1

                            # 检查最终结果
                            if not response or not geo_data or geo_data.get('_error'):
                                api_logger.error(f"[NxM] 重试耗尽，标记为失败：{model_name}, Q{q_idx}")
                                scheduler.record_model_failure(model_name)
                                # 仍然添加结果，但标记为失败
                                result = {
                                    'brand': brand,  # P0-2 修复：使用当前遍历的品牌
                                    'question': question,
                                    'model': model_name,
                                    'response': response,
                                    'geo_data': geo_data or {'_error': 'AI 调用或解析失败'},
                                    'timestamp': datetime.now().isoformat(),
                                    '_failed': True
                                }
                                scheduler.add_result(result)
                                results.append(result)
                            else:
                                scheduler.record_model_success(model_name)

                                # 构建结果（确保所有字段都是 JSON 可序列化的）
                                result = {
                                    'brand': brand,  # P0-2 修复：使用当前遍历的品牌
                                    'question': question,
                                    'model': model_name,
                                    'response': response,
                                    'geo_data': geo_data,
                                    'timestamp': datetime.now().isoformat()
                                }

                                scheduler.add_result(result)
                                results.append(result)

                            # 更新进度
                            completed += 1
                            scheduler.update_progress(completed, total_tasks, 'ai_fetching')

                        except Exception as e:'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ 缩进修复完成")
else:
    print("❌ 未找到目标文本")
    # 尝试查找部分匹配
    if '# 修复 3: 添加 AI 响应重试机制' in content:
        print("找到目标注释，但缩进可能不同")
