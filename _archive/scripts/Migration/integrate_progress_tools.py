#!/usr/bin/env python3
# -*- coding: utf-8 -*-

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加工具类引用
old_imports = '''const { getMatrixData, getColorByScore } = require('./utils/matrixHelper');
const { getTaskStatusApi } = require('../../api/home');
const { parseTaskStatus } = require('../../services/DiagnosisService');
const TimeEstimator = require('../../utils/timeEstimator');'''

new_imports = '''const { getMatrixData, getColorByScore } = require('./utils/matrixHelper');
const { getTaskStatusApi } = require('../../api/home');
const { parseTaskStatus } = require('../../services/DiagnosisService');
const TimeEstimator = require('../../utils/timeEstimator');
const RemainingTimeCalculator = require('../../utils/remainingTimeCalculator');
const ProgressValidator = require('../../utils/progressValidator');'''

content = content.replace(old_imports, new_imports)

# 2. 添加实例变量
old_instances = '''  /**
   * 【P0 新增】时间预估器实例
   */
  timeEstimator: null,

  data: {'''

new_instances = '''  /**
   * 【P0 新增】时间预估器实例
   */
  timeEstimator: null,
  
  /**
   * 【P0-3 新增】剩余时间计算器
   */
  remainingTimeCalc: null,
  
  /**
   * 【P1-4 新增】进度验证器
   */
  progressValidator: null,

  data: {'''

content = content.replace(old_instances, new_instances)

# 3. 在 data 中添加验证状态字段
old_data_fields = '''    //【P0 新增】时间预估范围
    timeEstimateRange: '',
    timeEstimateConfidence: 0
  },'''

new_data_fields = '''    //【P0 新增】时间预估范围
    timeEstimateRange: '',
    timeEstimateConfidence: 0,
    //【P0-3 新增】平滑剩余时间
    smoothedRemainingTime: '',
    //【P1-4 新增】进度验证状态
    progressValidationStatus: 'normal',
    progressWarnings: []
  },'''

content = content.replace(old_data_fields, new_data_fields)

# 4. 在 onLoad 中初始化计算器
old_init = '''      //【P0 重构】使用智能时间预估器
      this.timeEstimator = new TimeEstimator();'''

new_init = '''      //【P0 重构】使用智能时间预估器
      this.timeEstimator = new TimeEstimator();
      
      //【P0-3 新增】初始化剩余时间计算器
      this.remainingTimeCalc = new RemainingTimeCalculator();
      
      //【P1-4 新增】初始化进度验证器
      this.progressValidator = new ProgressValidator();'''

content = content.replace(old_init, new_init)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已集成剩余时间计算器和进度验证器')
ENDSCRIPT