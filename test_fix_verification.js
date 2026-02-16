/**
 * AI品牌战略诊断启动修复验证脚本
 * 用于验证修复后的API调用是否正常工作
 */

const { checkServerConnectionApi, startBrandTestApi, getTestProgressApi, getTaskStatusApi } = require('./api/home');

console.log('🔍 开始验证AI品牌战略诊断修复...');

// 验证1: 检查服务器连接
async function testServerConnection() {
    console.log('\n📋 测试1: 检查服务器连接...');
    try {
        const result = await checkServerConnectionApi();
        console.log('✅ 服务器连接测试成功:', result);
        return true;
    } catch (error) {
        console.log('❌ 服务器连接测试失败:', error.message);
        return false;
    }
}

// 验证2: 测试品牌诊断API调用
async function testBrandDiagnosisAPI() {
    console.log('\n📋 测试2: 测试品牌诊断API调用...');
    try {
        // 模拟请求数据
        const testData = {
            brand_list: ['测试品牌'],
            selectedModels: [
                { name: 'DeepSeek', checked: true },
                { name: '豆包', checked: true }
            ],
            customQuestions: ['介绍一下{brandName}', '{brandName}的主要产品是什么']
        };

        console.log('📤 发送品牌诊断请求:', JSON.stringify(testData, null, 2));
        
        const result = await startBrandTestApi(testData);
        console.log('✅ 品牌诊断API调用成功:', result);
        return result;
    } catch (error) {
        console.log('❌ 品牌诊断API调用失败:', error.message);
        return null;
    }
}

// 验证3: 测试任务状态API调用
async function testTaskStatusAPI(executionId) {
    console.log('\n📋 测试3: 测试任务状态API调用...');
    try {
        if (!executionId) {
            console.log('⚠️  无执行ID，跳过任务状态测试');
            return null;
        }

        console.log(`📤 查询任务状态，ID: ${executionId}`);
        const result = await getTaskStatusApi(executionId);
        console.log('✅ 任务状态API调用成功:', result);
        return result;
    } catch (error) {
        console.log('❌ 任务状态API调用失败:', error.message);
        return null;
    }
}

// 主验证函数
async function runVerification() {
    console.log('🚀 开始执行AI品牌战略诊断修复验证...\n');
    
    // 依次执行测试
    const serverOk = await testServerConnection();
    
    if (serverOk) {
        const brandResult = await testBrandDiagnosisAPI();
        
        if (brandResult && brandResult.execution_id) {
            // 等待一段时间再测试状态查询
            console.log('⏳ 等待2秒后测试任务状态查询...');
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            await testTaskStatusAPI(brandResult.execution_id);
        }
    }
    
    console.log('\n🎯 验证完成！');
}

// 运行验证
runVerification().catch(console.error);

module.exports = {
    testServerConnection,
    testBrandDiagnosisAPI,
    testTaskStatusAPI,
    runVerification
};