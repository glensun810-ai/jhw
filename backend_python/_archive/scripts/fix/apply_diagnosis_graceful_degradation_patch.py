#!/usr/bin/env python3
"""
诊断视图优雅降级修复补丁
修复问题：
1. 模型未注册时返回 400 错误而非跳过
2. 前端选择未支持模型时优雅降级

使用方法：
python3 apply_diagnosis_graceful_degradation_patch.py
"""

import os
import re

DIAGNOSIS_VIEWS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'wechat_backend',
    'views',
    'diagnosis_views.py'
)

def apply_patch():
    """应用优雅降级补丁"""
    
    if not os.path.exists(DIAGNOSIS_VIEWS_PATH):
        print(f"❌ 文件不存在：{DIAGNOSIS_VIEWS_PATH}")
        return False
    
    with open(DIAGNOSIS_VIEWS_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找需要替换的代码段
    old_code = '''        # Provider 可用性检查：验证所选模型是否已配置 API Key 并在 AIAdapterFactory 中注册
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType

        # 添加运行时调试信息
        api_logger.info(f"=== Runtime Adapter Status Check ===")
        api_logger.info(f"Selected models: {selected_models}")
        api_logger.info(f"All registered adapters: {[pt.value for pt in AIAdapterFactory._adapters.keys()]}")
        api_logger.info(f"MODEL_NAME_MAP: {AIAdapterFactory.MODEL_NAME_MAP}")
        api_logger.info(f"=== End Runtime Adapter Status Check ===")

        for model in selected_models:
            model_name = model['name'] if isinstance(model, dict) else model
            # 使用 AIAdapterFactory 的标准化方法
            normalized_model_name = AIAdapterFactory.get_normalized_model_name(model_name)

            # 检查平台是否可用（已注册且 API 密钥已配置）
            if not AIAdapterFactory.is_platform_available(normalized_model_name):
                # 打印出当前所有已注册的 Keys 并在报错中返回给前端
                registered_keys = [pt.value for pt in AIAdapterFactory._adapters.keys()]
                api_logger.error(f"Model {model_name} (normalized to {normalized_model_name}) not registered or not configured. Available models: {registered_keys}")
                return jsonify({
                    "status": "error",
                    "error": f'Model {model_name} not registered or not configured in AIAdapterFactory',
                    "code": 400,
                    "available_models": registered_keys,
                    "received_model": model_name,
                    "normalized_to": normalized_model_name
                }), 400

            # 检查 API Key 是否已配置
            from wechat_backend.config_manager import config_manager
            api_key = config_manager.get_api_key(normalized_model_name)
            if not api_key:
                return jsonify({"status": "error", "error": f'Model {model_name} not configured - missing API key', "code": 400, 'message': 'API Key 缺失'}), 400'''
    
    new_code = '''        # Provider 可用性检查：验证所选模型是否已配置 API Key 并在 AIAdapterFactory 中注册
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType

        # 添加运行时调试信息
        api_logger.info(f"=== Runtime Adapter Status Check ===")
        api_logger.info(f"Selected models: {selected_models}")
        api_logger.info(f"All registered adapters: {[pt.value for pt in AIAdapterFactory._adapters.keys()]}")
        api_logger.info(f"MODEL_NAME_MAP: {AIAdapterFactory.MODEL_NAME_MAP}")
        api_logger.info(f"=== End Runtime Adapter Status Check ===")

        # P2 修复：优雅降级 - 过滤掉未注册的模型，而不是返回 400 错误
        valid_models = []
        skipped_models = []
        
        for model in selected_models:
            model_name = model['name'] if isinstance(model, dict) else model
            # 使用 AIAdapterFactory 的标准化方法
            normalized_model_name = AIAdapterFactory.get_normalized_model_name(model_name)

            # 检查平台是否可用（已注册且 API 密钥已配置）
            if AIAdapterFactory.is_platform_available(normalized_model_name):
                # 检查 API Key 是否已配置
                from wechat_backend.config_manager import config_manager
                api_key = config_manager.get_api_key(normalized_model_name)
                if api_key:
                    valid_models.append(model)
                    api_logger.info(f"✅ Model {model_name} ({normalized_model_name}) is available")
                else:
                    skipped_models.append(model_name)
                    api_logger.warning(f"⚠️ Model {model_name} skipped - missing API key")
            else:
                # 模型未注册，跳过而非报错
                skipped_models.append(model_name)
                api_logger.warning(f"⚠️ Model {model_name} ({normalized_model_name}) not registered, skipping")
        
        # 如果所有模型都被过滤掉了，返回错误
        if not valid_models:
            registered_keys = [pt.value for pt in AIAdapterFactory._adapters.keys()]
            api_logger.error(f"All models were filtered out. Available models: {registered_keys}")
            return jsonify({
                "status": "error",
                "error": 'No valid AI models available. Please check your model selection.',
                "code": 400,
                "available_models": registered_keys,
                "requested_models": [m['name'] if isinstance(m, dict) else m for m in selected_models],
                "skipped_models": skipped_models,
                "message": "所选模型均未注册或 API Key 未配置"
            }), 400
        
        # 如果有模型被跳过，记录警告但不阻止执行
        if skipped_models:
            api_logger.info(f"⚠️ Skipped {len(skipped_models)} models: {skipped_models}")
            api_logger.info(f"✅ Proceeding with {len(valid_models)} valid models: {[m['name'] if isinstance(m, dict) else m for m in valid_models]}")
        
        # 更新 selected_models 为有效模型列表
        selected_models = valid_models'''
    
    if old_code not in content:
        print("⚠️  未找到需要替换的代码段")
        print("   可能已经应用过补丁或代码已变更")
        return False
    
    content = content.replace(old_code, new_code)
    
    with open(DIAGNOSIS_VIEWS_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 优雅降级补丁应用成功")
    print("   修改文件：diagnosis_views.py")
    print("   修改内容：模型未注册时优雅降级而非返回 400 错误")
    
    return True

if __name__ == '__main__':
    success = apply_patch()
    exit(0 if success else 1)
