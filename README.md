# GEO内容质量验证器

## 项目简介

GEO内容质量验证器是一款专为GEO（生成式引擎优化）服务商和企业设计的微信小程序工具，用于验证各大AI平台对品牌的认知准确度。通过多维度测试和评分系统，帮助用户量化品牌在AI中的表现，为优化策略提供数据支持。

## 项目特色

- **多平台支持**: 支持国内外主流AI平台（ChatGPT、Claude、通义千问、文心一言等）
- **自定义测试**: 支持用户自定义1-5个测试问题
- **量化评估**: 提供准确性、完整性、综合评分
- **实时反馈**: 即时显示测试结果和评分
- **分类管理**: 国内/海外AI平台分类展示

## 技术架构

### 前端
- 微信小程序原生框架
- WXML/WXSS/JavaScript

### 后端
- Python Flask框架
- RESTful API设计

## 功能特性

### 已实现功能
- [x] 微信登录集成
- [x] 品牌认知测试
- [x] 多AI平台支持（国内/海外分类）
- [x] 自定义问题输入（1-5个问题）
- [x] 实时测试进度显示
- [x] 详细结果展示
- [x] 评分系统（准确性/完整性/综合评分）

### AI平台支持
#### 国内平台
- 通义千问 (Qwen)
- 文心一言 (ERNIE Bot)
- 豆包 (Doubao)
- Kimi
- 元宝
- DeepSeek
- 讯飞星火 (Spark)

#### 海外平台
- ChatGPT
- Claude (Anthropic)
- Gemini (Google)
- Perplexity
- Grok (xAI)

## 项目结构

```
PythonProject/
├── config.py                 # 项目配置
├── main.py                   # 主启动文件
├── requirements.txt          # 依赖包列表
├── run.py                    # 运行脚本
├── README.md                 # 项目说明
├── docs/                     # 文档目录
│   └── technical_solution.md # 技术方案文档
├── wechat_backend/           # 后端代码
│   ├── __init__.py
│   ├── app.py
│   └── views.py
└── miniprogram/              # 微信小程序前端代码
    ├── app.js
    ├── app.json
    ├── sitemap.json
    ├── project.config.json
    └── pages/
        ├── index/
        │   ├── index.js
        │   ├── index.wxml
        │   ├── index.wxss
        │   └── index.json
        └── results/
            ├── results.js
            ├── results.wxml
            ├── results.wxss
            └── results.json
```

## 快速开始

### 环境准备
1. Python 3.8+
2. 微信开发者工具

### 后端启动
```bash
# 安装依赖
pip install -r requirements.txt

# 启动后端服务
python main.py
```

### 前端使用
1. 打开微信开发者工具
2. 导入 `miniprogram` 目录
3. 配置AppID（可使用测试号或自己的AppID）
4. 确保后端服务已启动
5. 点击"预览"或"调试"

## API接口

### 获取AI平台列表
```
GET /api/ai-platforms
```

### 执行品牌测试
```
POST /api/perform-brand-test
Content-Type: application/json

{
  "brandName": "测试品牌",
  "selectedModels": [
    {"name": "ChatGPT", "checked": true},
    {"name": "通义千问", "checked": true}
  ],
  "customQuestions": [
    "介绍一下测试品牌",
    "测试品牌的主要产品是什么"
  ]
}
```

## 开发计划

### 第一阶段：MVP版本 (已完成)
- [x] 核心测试功能
- [x] 多AI平台支持
- [x] 自定义问题功能
- [x] 评分系统

### 第二阶段：功能增强 (规划中)
- [ ] 真实AI平台API集成
- [ ] 用户系统
- [ ] 历史记录
- [ ] 数据可视化

### 第三阶段：商业化版本 (规划中)
- [ ] 付费订阅
- [ ] API开放
- [ ] 企业功能

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 许可证

MIT License

## 联系方式

如有问题或建议，请联系项目维护者。