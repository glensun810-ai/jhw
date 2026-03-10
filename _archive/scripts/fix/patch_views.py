#!/usr/bin/env python
"""
Script to patch views.py with the new NxM run_async_test function
"""
import re

VIEWS_FILE = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views.py'

# The new run_async_test function
NEW_RUN_ASYNC_TEST = '''    def run_async_test():
        """
        重构后的 NxM 执行逻辑
        外层循环遍历问题，内层循环遍历模型
        使用 execute_nxm_test 函数执行实际测试
        """
        try:
            # 在异步线程中进行所有耗时的操作
            api_logger.info(f"[AsyncTest] Initializing QuestionManager for execution_id: {execution_id}")
            question_manager = QuestionManager()
            api_logger.info(f"[AsyncTest] Successfully initialized managers for execution_id: {execution_id}")

            cleaned_custom_questions_for_validation = [q.strip() for q in custom_questions if q.strip()]

            if cleaned_custom_questions_for_validation:
                api_logger.info(f"[AsyncTest] Validating custom questions for execution_id: {execution_id}, questions: {cleaned_custom_questions_for_validation}")
                validation_result = question_manager.validate_custom_questions(cleaned_custom_questions_for_validation)
                api_logger.info(f"[AsyncTest] Question validation result for execution_id: {execution_id}, result: {validation_result}")

                if not validation_result['valid']:
                    api_logger.error(f"[AsyncTest] Question validation failed for execution_id: {execution_id}, errors: {validation_result['errors']}")
                    if execution_id in execution_store:
                        execution_store[execution_id].update({'status': 'failed', 'error': f"Invalid questions: {'; '.join(validation_result['errors'])}"})
                    return
                raw_questions = validation_result['cleaned_questions']
                api_logger.info(f"[AsyncTest] Successfully validated questions for execution_id: {execution_id}, raw_questions: {raw_questions}")
            else:
                raw_questions = [
                    "介绍一下{brandName}",
                    "{brandName}的主要产品是什么",
                    "{brandName}和竞品有什么区别"
                ]
                api_logger.info(f"[AsyncTest] Using default questions for execution_id: {execution_id}")

        # 使用 NxM 执行引擎执行测试
        api_logger.info(f"Starting NxM execution engine for '{execution_id}'")
        
        # 调用 NxM 执行函数
        result = execute_nxm_test(
            execution_id=execution_id,
            brand_list=brand_list,
            selected_models=selected_models,
            raw_questions=raw_questions,
            user_id=user_id or "anonymous",
            user_level=user_level.value,
            execution_store=execution_store
        )
        
        if result.get('success'):
            api_logger.info(f"NxM execution completed successfully for '{execution_id}'")
        else:
            api_logger.error(f"NxM execution failed for '{execution_id}': {result.get('error')}")

        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            api_logger.error(f"Async test execution failed for execution_id {execution_id}: {e}\\nTraceback: {error_traceback}")
            if execution_id in execution_store:
                execution_store[execution_id].update({
                    'status': 'failed',
                    'error': f"{str(e)}\\nTraceback: {error_traceback}"
                })
'''

def patch_views_file():
    with open(VIEWS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the old run_async_test function
    # Pattern: from "    def run_async_test():" to "    thread = Thread(target=run_async_test)"
    pattern = r'(    def run_async_test\(\):.*?)(    thread = Thread\(target=run_async_test\))'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("ERROR: Could not find run_async_test function")
        return False
    
    old_function = match.group(1)
    
    # Replace the old function with the new one
    new_content = content.replace(old_function, NEW_RUN_ASYNC_TEST)
    
    # Write the updated content
    with open(VIEWS_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("SUCCESS: views.py has been patched")
    return True

if __name__ == '__main__':
    patch_views_file()
