AI Coding 新功能开发标准化 SOP
致 AI 工程师：在本项目中开发任何新功能时，必须严格遵守以下工作流。禁止跳过任何层级直接在 Page 中编写底层逻辑。

第一阶段：协议定义 (Config & Constant)
在动任何逻辑前，先定义配置。

URL 注册：在 /utils/config.js 的 API_ENDPOINTS 对象中添加新功能的后端路由。

常量定义：如果涉及状态（如：待审核、已通过），在 /constants/index.js 中定义枚举。

第二阶段：通讯层构建 (API Layer)
创建对应的 /api/ 文件。

文件命名：功能名小写（如 api/feedback.js）。

函数封装：从 ../utils/request 引入 post/get，封装业务函数。

必须包含 JSDoc：说明入参和出参的结构。

第三阶段：业务处理层 (Service Layer - 可选)
如果数据需要转换，不要在 Page 里做。

触发条件：

需要组合两个以上的 API 数据。

需要对后端返回的原始数组进行复杂的 filter/map/reduce。

需要对日期、金额进行非简单的格式化。

位置：放入 /services/。

第四阶段：页面集成 (UI Layer)
最后编写 pages/ 中的逻辑。

逻辑注入：在 Page 的 onLoad 或事件函数中调用 API/Service 函数。

UI 绑定：仅通过 this.setData 将最终加工好的数据渲染到视图。

错误处理：使用 try...catch 捕获异常，并给用户友好的提示（如 wx.showToast）。

样式编写：组件WXSS中只能使用类选择器，禁止使用标签选择器、ID选择器和属性选择器。

函数引用：禁止在同一文件中重复定义已从外部模块导入的函数，避免命名冲突。

🚩 违规自查清单 (Don'ts)
禁止：在 Page 中直接使用 wx.request。

禁止：在代码中出现类似 'http://127.0.0.1:5000' 的硬编码字符串。

禁止：在 API 层编写 if (status === 1) 等业务逻辑判断。

禁止：修改 utils/request.js 底层逻辑。

禁止：在组件WXSS中使用标签选择器、ID选择器和属性选择器。

禁止：在同一文件中重复定义已从外部模块导入的函数。

💡 建议您的下一个动作：
现在您的架构已经**“整装待发”**了。您可以尝试给 AI 下达一个具体的新任务来测试这套 SOP。例如：

任务指令：
“请阅读 DEVELOPMENT_SOP.md。现在我需要增加一个‘意见反馈’功能：

后端接口是 /api/feedback/submit，方法是 POST。

用户需要提交的内容包含：反馈类型（枚举值 1-3）、文字描述、联系方式。

请严格按照 SOP 流程，为我生成 config 配置、api 文件，并给出一个简单的 feedback 页面 JS 代码示例。”