#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 修复集成问题

file_path = '/Users/sgl/PycharmProjects/PythonProject/pages/detail/index.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 检查是否已有实例化代码
if 'this.timeEstimator = new TimeEstimator()' in content:
    print("✅ 实例化代码已存在")
else:
    print("❌ 实例化代码不存在，需要添加")
    
    # 找到 onLoad 方法中的初始化位置
    old_init = "// 启动轮询\n      this.startPolling();"
    new_init = """// 启动轮询
      this.startPolling();
      
      //【P0 新增】初始化工具类实例
      this.timeEstimator = new TimeEstimator();
      this.remainingTimeCalc = new RemainingTimeCalculator();
      this.progressValidator = new ProgressValidator();
      this.stageEstimator = new StageEstimator();
      this.networkMonitor = new NetworkMonitor();
      this.progressNotifier = new ProgressNotifier();
      this.taskWeightProcessor = new TaskWeightProcessor();"""
    
    if old_init in content:
        content = content.replace(old_init, new_init)
        print("✅ 已添加工具类实例化代码")
    else:
        print("⚠️ 未找到初始化位置，需要手动检查")

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 集成修复完成")
