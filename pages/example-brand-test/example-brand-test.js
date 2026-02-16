/**
 * 示例品牌测试页面
 * 演示如何按照架构规范集成问题解析和分发功能
 */

// 导入API层
const { performEnhancedBrandTest, getTestProgress } = require('../../api/brand-enhanced-api');

// 导入服务层
const { executeQuestionDistributionTest } = require('../../services/brand-question-service');

// 导入常量
const { BRAND_TEST_STATUS, BRAND_TEST_LIMITS } = require('../../constants/index');

Page({
  /**
   * 页面的初始数据
   */
  data: {
    brandList: [],
    selectedModels: [],
    customQuestion: '',
    testStatus: BRAND_TEST_STATUS.INIT,
    progress: 0,
    executionId: null,
    errorMessage: '',
    showLoading: false
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    // 页面加载时的初始化逻辑
    console.log('品牌测试页面加载');
  },

  /**
   * 输入品牌列表
   */
  onBrandListChange(e) {
    const brandList = e.detail.value.split(',').map(item => item.trim()).filter(item => item);
    this.setData({
      brandList
    });
  },

  /**
   * 输入自定义问题
   */
  onQuestionChange(e) {
    this.setData({
      customQuestion: e.detail.value
    });
  },

  /**
   * 选择AI模型
   */
  onModelToggle(e) {
    const { index } = e.currentTarget.dataset;
    const selectedModels = this.data.selectedModels;
    selectedModels[index].checked = !selectedModels[index].checked;
    this.setData({
      selectedModels
    });
  },

  /**
   * 执行品牌测试
   */
  async startBrandTest() {
    try {
      // 显示加载状态
      this.setData({
        showLoading: true,
        errorMessage: ''
      });

      // 验证输入
      if (!this.validateInputs()) {
        return;
      }

      // 准备测试数据
      const testData = {
        brand_list: this.data.brandList,
        selectedModels: this.data.selectedModels,
        custom_question: this.data.customQuestion
      };

      // 使用服务层处理问题解析和分发
      const processedData = await executeQuestionDistributionTest(testData);

      // 调用API执行测试
      const result = await performEnhancedBrandTest(processedData);

      if (result.statusCode === 200 && result.data.status === 'success') {
        // 启动进度轮询
        this.setData({
          executionId: result.data.executionId,
          testStatus: BRAND_TEST_STATUS.DISTRIBUTING,
          progress: 0
        });
        
        // 开始轮询进度
        this.pollTestProgress(result.data.executionId);
      } else {
        throw new Error(result.data.error || '启动测试失败');
      }
    } catch (error) {
      console.error('品牌测试启动失败:', error);
      this.setData({
        errorMessage: error.message || '启动测试时发生错误',
        showLoading: false
      });
      
      wx.showToast({
        title: '测试启动失败',
        icon: 'error',
        duration: 2000
      });
    }
  },

  /**
   * 验证输入数据
   */
  validateInputs() {
    const { brandList, selectedModels, customQuestion } = this.data;

    if (!brandList || brandList.length === 0) {
      this.setData({ errorMessage: '请输入至少一个品牌名称' });
      wx.showToast({
        title: '请输入品牌名称',
        icon: 'none'
      });
      return false;
    }

    if (!selectedModels.some(model => model.checked)) {
      this.setData({ errorMessage: '请选择至少一个AI模型' });
      wx.showToast({
        title: '请选择AI模型',
        icon: 'none'
      });
      return false;
    }

    if (!customQuestion || customQuestion.trim().length === 0) {
      this.setData({ errorMessage: '请输入自定义问题' });
      wx.showToast({
        title: '请输入问题',
        icon: 'none'
      });
      return false;
    }

    return true;
  },

  /**
   * 轮询测试进度
   */
  async pollTestProgress(executionId) {
    const pollInterval = setInterval(async () => {
      try {
        const result = await getTestProgress({ executionId });

        if (result.statusCode === 200) {
          const progressData = result.data;

          // 更新进度
          this.setData({
            progress: progressData.progress || 0,
            testStatus: progressData.status || BRAND_TEST_STATUS.PROCESSING
          });

          // 检查是否完成
          if (progressData.completed) {
            clearInterval(pollInterval);
            this.setData({
              showLoading: false,
              testStatus: BRAND_TEST_STATUS.COMPLETED
            });

            wx.showToast({
              title: '测试完成',
              icon: 'success',
              duration: 2000
            });

            // 跳转到结果页面
            setTimeout(() => {
              wx.navigateTo({
                url: `/pages/results/results?executionId=${executionId}`
              });
            }, 1500);
          }
        } else {
          throw new Error('获取进度失败');
        }
      } catch (error) {
        console.error('获取进度失败:', error);
        clearInterval(pollInterval);
        this.setData({
          showLoading: false,
          errorMessage: '获取进度失败',
          testStatus: BRAND_TEST_STATUS.FAILED
        });
      }
    }, 2000); // 每2秒轮询一次
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {
    // 页面渲染完成后的逻辑
  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
    // 页面显示时的逻辑
  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {
    // 页面隐藏时的逻辑
  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {
    // 页面卸载时的逻辑
  }
});