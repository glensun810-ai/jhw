基础
名称	功能
wx.env	环境变量
wx.canIUse	判断小程序的API，回调，参数，组件等是否在当前版本可用
wx.base64ToArrayBuffer	将 Base64 字符串转成 ArrayBuffer 对象
wx.arrayBufferToBase64	将 ArrayBuffer 对象转成 Base64 字符串
系统	
名称	功能
wx.openSystemBluetoothSetting	跳转系统蓝牙设置页
wx.openAppAuthorizeSetting	跳转系统微信授权管理页
wx.getWindowInfo	获取窗口信息
wx.getSystemSetting	获取设备设置
wx.getSystemInfoSync	wx.getSystemInfo 的同步版本
wx.getSystemInfoAsync	异步获取系统信息
wx.getSystemInfo	获取系统信息
wx.getSkylineInfoSync	获取当前运行环境对于 Skyline 渲染引擎 的支持情况
wx.getSkylineInfo	获取当前运行环境对于 Skyline 渲染引擎 的支持情况
wx.getRendererUserAgent	获取 Webview 小程序的 UserAgent
wx.getDeviceInfo	获取设备基础信息
wx.getDeviceBenchmarkInfo	获取设备性能得分和机型档位数据
wx.getAppBaseInfo	获取微信APP基础信息
wx.getAppAuthorizeSetting	获取微信APP授权设置
更新	
名称	功能
wx.updateWeChatApp	更新客户端版本
wx.getUpdateManager	获取全局唯一的版本更新管理器，用于管理小程序更新
UpdateManager	UpdateManager 对象，用来管理更新，可通过 wx.getUpdateManager 接口获取实例
名称	功能
UpdateManager.applyUpdate	强制小程序重启并使用新版本
UpdateManager.onCheckForUpdate	监听向微信后台请求检查更新结果事件
UpdateManager.onUpdateFailed	监听小程序更新失败事件
UpdateManager.onUpdateReady	监听小程序有版本更新事件
生命周期	
名称	功能
wx.onApiCategoryChange	监听 API 类别变化事件
wx.offApiCategoryChange	移除 API 类别变化事件的监听函数
wx.getLaunchOptionsSync	获取小程序启动时的参数
wx.getEnterOptionsSync	获取本次小程序启动时的参数
wx.getApiCategory	获取当前 API 类别
应用级事件	
名称	功能
wx.postMessageToReferrerPage	向跳转的源页面发送消息
wx.postMessageToReferrerMiniProgram	向跳转的源小程序发送消息，源小程序可在 wx.onShow 或 wx.getEnterOptionsSync 中通过 extraData 接收消息
wx.onUnhandledRejection	监听未处理的 Promise 拒绝事件
wx.onThemeChange	监听系统主题改变事件
wx.onPageNotFound	监听小程序要打开的页面不存在事件
wx.onLazyLoadError	监听小程序异步组件加载失败事件
wx.onError	监听小程序错误事件
wx.onAudioInterruptionEnd	监听音频中断结束事件
wx.onAudioInterruptionBegin	监听音频因为受到系统占用而被中断开始事件
wx.onAppShow	监听小程序切前台事件
wx.onAppHide	监听小程序切后台事件
wx.offUnhandledRejection	移除未处理的 Promise 拒绝事件的监听函数
wx.offThemeChange	移除系统主题改变事件的监听函数
wx.offPageNotFound	移除小程序要打开的页面不存在事件的监听函数
wx.offLazyLoadError	移除小程序异步组件加载失败事件的监听函数
wx.offError	移除小程序错误事件的监听函数
wx.offAudioInterruptionEnd	移除音频中断结束事件的监听函数
wx.offAudioInterruptionBegin	移除音频因为受到系统占用而被中断开始事件的监听函数
wx.offAppShow	移除小程序切前台事件的监听函数
wx.offAppHide	移除小程序切后台事件的监听函数
路由事件	
名称	功能
wx.onBeforePageUnload	监听路由事件引起现有页面实例销毁时，页面实例销毁前的事件监听，详见 页面路由监听
wx.onBeforePageLoad	监听路由事件引起新的页面实例化时，页面实例化前的事件监听，详见 页面路由监听
wx.onBeforeAppRoute	监听路由事件下发后，执行路由逻辑前的事件监听，详见 页面路由监听
wx.onAppRouteDone	监听当前路由动画执行完成的事件监听，详见 页面路由监听
wx.onAppRoute	监听路由事件下发后，执行路由逻辑后的事件监听，详见 页面路由监听
wx.onAfterPageUnload	监听路由事件引起现有页面实例销毁时，页面实例销毁后的事件监听，详见 页面路由监听
wx.onAfterPageLoad	监听路由事件引起新的页面实例化时，页面实例化完成的事件监听，详见 页面路由监听
wx.offBeforePageUnload	移除路由事件的监听函数
wx.offBeforePageLoad	移除路由事件的监听函数
wx.offBeforeAppRoute	移除路由事件的监听函数
wx.offAppRouteDone	移除当前路由动画执行完成的事件的监听函数
wx.offAppRoute	移除路由事件的监听函数
wx.offAfterPageUnload	移除路由事件的监听函数
wx.offAfterPageLoad	移除路由事件的监听函数
调试	
名称	功能
wx.setEnableDebug	设置是否打开调试开关
wx.getRealtimeLogManager	获取实时日志管理器对象
wx.getLogManager	获取日志管理器对象
console	向调试面板中打印日志
名称	功能
console.debug	向调试面板中打印 debug 日志
console.error	向调试面板中打印 error 日志
console.group	在调试面板中创建一个新的分组
console.groupEnd	结束由 console.group 创建的分组
console.info	向调试面板中打印 info 日志
console.log	向调试面板中打印 log 日志
console.warn	向调试面板中打印 warn 日志
LogManager	日志管理器实例，可以通过 wx.getLogManager 获取
名称	功能
LogManager.debug	写 debug 日志
LogManager.info	写 info 日志
LogManager.log	写 log 日志
LogManager.warn	写 warn 日志
RealtimeLogManager	实时日志管理器实例，可以通过 wx.getRealtimeLogManager 获取
名称	功能
RealtimeLogManager.addFilterMsg	添加过滤关键字，暂不支持在插件使用
RealtimeLogManager.error	写 error 日志，暂不支持在插件使用
RealtimeLogManager.getCurrentState	实时日志会将一定时间间隔内缓存的日志聚合上报，如果该时间内缓存的内容超出限制，则会被丢弃
RealtimeLogManager.in	设置实时日志page参数所在的页面，暂不支持在插件使用
RealtimeLogManager.info	写 info 日志，暂不支持在插件使用
RealtimeLogManager.setFilterMsg	设置过滤关键字，暂不支持在插件使用
RealtimeLogManager.tag	获取给定标签的日志管理器实例，目前只支持在插件使用
RealtimeLogManager.warn	写 warn 日志，暂不支持在插件使用
RealtimeTagLogManager	给定标签的实时日志管理器实例，可以通过 RealtimeLogManager.tag 接口获取，目前只支持在插件使用
名称	功能
RealtimeTagLogManager.addFilterMsg	添加过滤关键字
RealtimeTagLogManager.error	写 error 日志
RealtimeTagLogManager.info	写 info 日志
RealtimeTagLogManager.setFilterMsg	设置过滤关键字
RealtimeTagLogManager.warn	写 warn 日志
性能	
名称	功能
wx.requestIdleCallback	注册一个函数，将在空闲时期被调用
wx.reportPerformance	小程序测速上报
wx.preloadWebview	预加载下个页面的 WebView
wx.preloadSkylineView	预加载下个页面所需要的 Skyline 运行环境
wx.preloadAssets	为视图层预加载媒体资源文件, 目前支持：font，image
wx.getPerformance	获取当前小程序性能相关的信息
wx.cancelIdleCallback	取消之前注册的指定回调函数
EntryList	EntryList 对象
名称	功能
EntryList.getEntries	该方法返回当前列表中的所有性能数据
EntryList.getEntriesByName	获取当前列表中所有名称为 [name] 且类型为 [entryType] 的性能数据
EntryList.getEntriesByType	获取当前列表中所有类型为 [entryType] 的性能数据
Performance	Performance 对象，用于获取性能数据及创建性能监听器
名称	功能
Performance.createObserver	创建全局性能事件监听器
Performance.getEntries	该方法返回当前缓冲区中的所有性能数据
Performance.getEntriesByName	获取当前缓冲区中所有名称为 [name] 且类型为 [entryType] 的性能数据
Performance.getEntriesByType	获取当前缓冲区中所有类型为 [entryType] 的性能数据
Performance.setBufferSize	设置缓冲区大小，默认缓冲 30 条性能数据
PerformanceEntry	单条性能数据
PerformanceObserver	PerformanceObserver 对象，用于监听性能相关事件
名称	功能
PerformanceObserver.disconnect	停止监听
PerformanceObserver.observe	开始监听
分包加载	
名称	功能
wx.preDownloadSubpackage	触发分包预下载
PreDownloadSubpackageTask	预下载分包任务实例，用于获取分包预下载状态
名称	功能
PreDownloadSubpackageTask.onProgressUpdate	监听分包加载进度变化事件
加密	
名称	功能
wx.getUserCryptoManager	获取用户加密模块
UserCryptoManager	用户加密模块
名称	功能
UserCryptoManager.getLatestUserKey	获取最新的用户加密密钥
UserCryptoManager.getRandomValues	获取密码学安全随机数

名称	功能
wx.env	环境变量
wx.canIUse	判断小程序的API，回调，参数，组件等是否在当前版本可用
wx.base64ToArrayBuffer	将 Base64 字符串转成 ArrayBuffer 对象
wx.arrayBufferToBase64	将 ArrayBuffer 对象转成 Base64 字符串
系统	
名称	功能
wx.openSystemBluetoothSetting	跳转系统蓝牙设置页
wx.openAppAuthorizeSetting	跳转系统微信授权管理页
wx.getWindowInfo	获取窗口信息
wx.getSystemSetting	获取设备设置
wx.getSystemInfoSync	wx.getSystemInfo 的同步版本
wx.getSystemInfoAsync	异步获取系统信息
wx.getSystemInfo	获取系统信息
wx.getSkylineInfoSync	获取当前运行环境对于 Skyline 渲染引擎 的支持情况
wx.getSkylineInfo	获取当前运行环境对于 Skyline 渲染引擎 的支持情况
wx.getRendererUserAgent	获取 Webview 小程序的 UserAgent
wx.getDeviceInfo	获取设备基础信息
wx.getDeviceBenchmarkInfo	获取设备性能得分和机型档位数据
wx.getAppBaseInfo	获取微信APP基础信息
wx.getAppAuthorizeSetting	获取微信APP授权设置
更新	
名称	功能
wx.updateWeChatApp	更新客户端版本
wx.getUpdateManager	获取全局唯一的版本更新管理器，用于管理小程序更新
UpdateManager	UpdateManager 对象，用来管理更新，可通过 wx.getUpdateManager 接口获取实例
名称	功能
UpdateManager.applyUpdate	强制小程序重启并使用新版本
UpdateManager.onCheckForUpdate	监听向微信后台请求检查更新结果事件
UpdateManager.onUpdateFailed	监听小程序更新失败事件
UpdateManager.onUpdateReady	监听小程序有版本更新事件
生命周期	
名称	功能
wx.onApiCategoryChange	监听 API 类别变化事件
wx.offApiCategoryChange	移除 API 类别变化事件的监听函数
wx.getLaunchOptionsSync	获取小程序启动时的参数
wx.getEnterOptionsSync	获取本次小程序启动时的参数
wx.getApiCategory	获取当前 API 类别
应用级事件	
名称	功能
wx.postMessageToReferrerPage	向跳转的源页面发送消息
wx.postMessageToReferrerMiniProgram	向跳转的源小程序发送消息，源小程序可在 wx.onShow 或 wx.getEnterOptionsSync 中通过 extraData 接收消息
wx.onUnhandledRejection	监听未处理的 Promise 拒绝事件
wx.onThemeChange	监听系统主题改变事件
wx.onPageNotFound	监听小程序要打开的页面不存在事件
wx.onLazyLoadError	监听小程序异步组件加载失败事件
wx.onError	监听小程序错误事件
wx.onAudioInterruptionEnd	监听音频中断结束事件
wx.onAudioInterruptionBegin	监听音频因为受到系统占用而被中断开始事件
wx.onAppShow	监听小程序切前台事件
wx.onAppHide	监听小程序切后台事件
wx.offUnhandledRejection	移除未处理的 Promise 拒绝事件的监听函数
wx.offThemeChange	移除系统主题改变事件的监听函数
wx.offPageNotFound	移除小程序要打开的页面不存在事件的监听函数
wx.offLazyLoadError	移除小程序异步组件加载失败事件的监听函数
wx.offError	移除小程序错误事件的监听函数
wx.offAudioInterruptionEnd	移除音频中断结束事件的监听函数
wx.offAudioInterruptionBegin	移除音频因为受到系统占用而被中断开始事件的监听函数
wx.offAppShow	移除小程序切前台事件的监听函数
wx.offAppHide	移除小程序切后台事件的监听函数
路由事件	
名称	功能
wx.onBeforePageUnload	监听路由事件引起现有页面实例销毁时，页面实例销毁前的事件监听，详见 页面路由监听
wx.onBeforePageLoad	监听路由事件引起新的页面实例化时，页面实例化前的事件监听，详见 页面路由监听
wx.onBeforeAppRoute	监听路由事件下发后，执行路由逻辑前的事件监听，详见 页面路由监听
wx.onAppRouteDone	监听当前路由动画执行完成的事件监听，详见 页面路由监听
wx.onAppRoute	监听路由事件下发后，执行路由逻辑后的事件监听，详见 页面路由监听
wx.onAfterPageUnload	监听路由事件引起现有页面实例销毁时，页面实例销毁后的事件监听，详见 页面路由监听
wx.onAfterPageLoad	监听路由事件引起新的页面实例化时，页面实例化完成的事件监听，详见 页面路由监听
wx.offBeforePageUnload	移除路由事件的监听函数
wx.offBeforePageLoad	移除路由事件的监听函数
wx.offBeforeAppRoute	移除路由事件的监听函数
wx.offAppRouteDone	移除当前路由动画执行完成的事件的监听函数
wx.offAppRoute	移除路由事件的监听函数
wx.offAfterPageUnload	移除路由事件的监听函数
wx.offAfterPageLoad	移除路由事件的监听函数
调试	
名称	功能
wx.setEnableDebug	设置是否打开调试开关
wx.getRealtimeLogManager	获取实时日志管理器对象
wx.getLogManager	获取日志管理器对象
console	向调试面板中打印日志
名称	功能
console.debug	向调试面板中打印 debug 日志
console.error	向调试面板中打印 error 日志
console.group	在调试面板中创建一个新的分组
console.groupEnd	结束由 console.group 创建的分组
console.info	向调试面板中打印 info 日志
console.log	向调试面板中打印 log 日志
console.warn	向调试面板中打印 warn 日志
LogManager	日志管理器实例，可以通过 wx.getLogManager 获取
名称	功能
LogManager.debug	写 debug 日志
LogManager.info	写 info 日志
LogManager.log	写 log 日志
LogManager.warn	写 warn 日志
RealtimeLogManager	实时日志管理器实例，可以通过 wx.getRealtimeLogManager 获取
名称	功能
RealtimeLogManager.addFilterMsg	添加过滤关键字，暂不支持在插件使用
RealtimeLogManager.error	写 error 日志，暂不支持在插件使用
RealtimeLogManager.getCurrentState	实时日志会将一定时间间隔内缓存的日志聚合上报，如果该时间内缓存的内容超出限制，则会被丢弃
RealtimeLogManager.in	设置实时日志page参数所在的页面，暂不支持在插件使用
RealtimeLogManager.info	写 info 日志，暂不支持在插件使用
RealtimeLogManager.setFilterMsg	设置过滤关键字，暂不支持在插件使用
RealtimeLogManager.tag	获取给定标签的日志管理器实例，目前只支持在插件使用
RealtimeLogManager.warn	写 warn 日志，暂不支持在插件使用
RealtimeTagLogManager	给定标签的实时日志管理器实例，可以通过 RealtimeLogManager.tag 接口获取，目前只支持在插件使用
名称	功能
RealtimeTagLogManager.addFilterMsg	添加过滤关键字
RealtimeTagLogManager.error	写 error 日志
RealtimeTagLogManager.info	写 info 日志
RealtimeTagLogManager.setFilterMsg	设置过滤关键字
RealtimeTagLogManager.warn	写 warn 日志
性能	
名称	功能
wx.requestIdleCallback	注册一个函数，将在空闲时期被调用
wx.reportPerformance	小程序测速上报
wx.preloadWebview	预加载下个页面的 WebView
wx.preloadSkylineView	预加载下个页面所需要的 Skyline 运行环境
wx.preloadAssets	为视图层预加载媒体资源文件, 目前支持：font，image
wx.getPerformance	获取当前小程序性能相关的信息
wx.cancelIdleCallback	取消之前注册的指定回调函数
EntryList	EntryList 对象
名称	功能
EntryList.getEntries	该方法返回当前列表中的所有性能数据
EntryList.getEntriesByName	获取当前列表中所有名称为 [name] 且类型为 [entryType] 的性能数据
EntryList.getEntriesByType	获取当前列表中所有类型为 [entryType] 的性能数据
Performance	Performance 对象，用于获取性能数据及创建性能监听器
名称	功能
Performance.createObserver	创建全局性能事件监听器
Performance.getEntries	该方法返回当前缓冲区中的所有性能数据
Performance.getEntriesByName	获取当前缓冲区中所有名称为 [name] 且类型为 [entryType] 的性能数据
Performance.getEntriesByType	获取当前缓冲区中所有类型为 [entryType] 的性能数据
Performance.setBufferSize	设置缓冲区大小，默认缓冲 30 条性能数据
PerformanceEntry	单条性能数据
PerformanceObserver	PerformanceObserver 对象，用于监听性能相关事件
名称	功能
PerformanceObserver.disconnect	停止监听
PerformanceObserver.observe	开始监听
分包加载	
名称	功能
wx.preDownloadSubpackage	触发分包预下载
PreDownloadSubpackageTask	预下载分包任务实例，用于获取分包预下载状态
名称	功能
PreDownloadSubpackageTask.onProgressUpdate	监听分包加载进度变化事件
加密	
名称	功能
wx.getUserCryptoManager	获取用户加密模块
UserCryptoManager	用户加密模块
名称	功能
UserCryptoManager.getLatestUserKey	获取最新的用户加密密钥
UserCryptoManager.getRandomValues	获取密码学安全随机数
路由

路由
名称	功能
wx.switchTab	跳转到 tabBar 页面，并关闭其他所有非 tabBar 页面
wx.rewriteRoute	重写正在进行中的路由事件，详见 路由重写
wx.reLaunch	关闭所有页面，打开到应用内的某个页面
wx.redirectTo	关闭当前页面，跳转到应用内的某个页面
wx.navigateTo	保留当前页面，跳转到应用内的某个页面
wx.navigateBack	关闭当前页面，返回上一页面或多级页面
EventChannel	页面间事件通信通道
名称	功能
EventChannel.emit	触发一个事件
EventChannel.off	取消监听一个事件
EventChannel.on	持续监听一个事件
EventChannel.once	监听一个事件一次，触发后失效
自定义路由	
名称	功能
wx.router	router 对象，可以通过 wx.router 获取
基础	
名称	功能
router.addRouteBuilder	添加自定义路由配置
router.getRouteContext	获取页面对应的自定义路由上下文对象
router.removeRouteBuilder	移除自定义路由配置
跳转
名称	功能
wx.restartMiniProgram	重启当前小程序
wx.openOfficialAccountProfile	通过小程序打开公众号主页
wx.openOfficialAccountChat	通过小程序打开公众号会话界面
wx.openOfficialAccountArticle	通过小程序打开任意公众号文章（不包括临时链接等异常状态下的公众号文章），必须有点击行为才能调用成功
wx.openInquiriesTopic	通过小程序打开问一问话题
wx.openEmbeddedMiniProgram	打开半屏小程序
wx.onEmbeddedMiniProgramHeightChange	监听半屏小程序可视高度变化事件
wx.offEmbeddedMiniProgramHeightChange	移除半屏小程序可视高度变化事件的监听函数
wx.navigateToMiniProgram	打开另一个小程序
wx.navigateBackMiniProgram	返回到上一个小程序
wx.exitMiniProgram	退出当前小程序
聊天工具
名称	功能
wx.shareVideoToGroup	转发视频到聊天
wx.shareImageToGroup	转发图片到聊天
wx.shareFileToGroup	转发文件到聊天
wx.shareEmojiToGroup	转发表情到聊天
wx.shareAppMessageToGroup	转发小程序卡片到聊天
wx.selectGroupMembers	选择聊天室的成员，并返回选择成员的 group_openid
wx.openChatTool	进入聊天工具模式
wx.notifyGroupMembers	提醒用户完成任务，标题长度不超过 30 个字符，支持中英文和数字，中文算2个字符
wx.getChatToolInfo	获取聊天工具模式下的群聊信息
转发
名称	功能
wx.updateShareMenu	更新转发属性
wx.showShareMenu	设置右上角点开的详情界面中的分享按钮是否可用
wx.showShareImageMenu	打开分享图片弹窗，可以将图片发送给朋友、分享至朋友圈、收藏或下载
wx.shareVideoMessage	转发视频到聊天
wx.shareToOfficialAccount	支持拉起公众号图文发表页，用户可将图片与文字内容发表至公众号
wx.shareFileMessage	转发文件到聊天
wx.onCopyUrl	监听用户点击右上角菜单的「复制链接」按钮时触发的事件
wx.offCopyUrl	移除用户点击右上角菜单的「复制链接」按钮时触发的事件的全部监听函数
wx.hideShareMenu	隐藏当前页面的转发按钮
wx.getShareInfo	获取转发详细信息（主要是获取群ID）
wx.authPrivateMessage	验证私密消息
界面
名称	功能
交互	
名称	功能
wx.showToast	显示消息提示框
wx.showModal	显示模态对话框
wx.showLoading	显示 loading 提示框
wx.showActionSheet	显示操作菜单
wx.hideToast	隐藏消息提示框
wx.hideLoading	隐藏 loading 提示框
wx.enableAlertBeforeUnload	开启小程序页面返回询问对话框
wx.disableAlertBeforeUnload	关闭小程序页面返回询问对话框
导航栏	
名称	功能
wx.showNavigationBarLoading	在当前页面显示导航条加载动画
wx.setNavigationBarTitle	动态设置当前页面的标题
wx.setNavigationBarColor	设置页面导航条颜色
wx.hideNavigationBarLoading	在当前页面隐藏导航条加载动画
wx.hideHomeButton	隐藏返回首页按钮
背景	
名称	功能
wx.setBackgroundTextStyle	动态设置下拉背景字体、loading 图的样式
wx.setBackgroundColor	动态设置窗口的背景色
Tab Bar	
名称	功能
wx.showTabBarRedDot	显示 tabBar 某一项的右上角的红点
wx.showTabBar	显示 tabBar
wx.setTabBarStyle	动态设置 tabBar 的整体样式
wx.setTabBarItem	动态设置 tabBar 某一项的内容，2.7.0 起图片支持临时文件和网络文件
wx.setTabBarBadge	为 tabBar 某一项的右上角添加文本
wx.removeTabBarBadge	移除 tabBar 某一项右上角的文本
wx.hideTabBarRedDot	隐藏 tabBar 某一项的右上角的红点
wx.hideTabBar	隐藏 tabBar
字体	
名称	功能
wx.loadFontFace	动态加载网络字体
wx.loadBuiltInFontFace	加载内置字体
下拉刷新	
名称	功能
wx.stopPullDownRefresh	停止当前页面下拉刷新
wx.startPullDownRefresh	开始下拉刷新
滚动	
名称	功能
wx.pageScrollTo	将页面滚动到目标位置，支持选择器和滚动距离两种方式定位
ScrollViewContext	增强 ScrollView 实例，可通过 wx.createSelectorQuery 的 NodesRef.node 方法获取
名称	功能
ScrollViewContext.closeRefresh	关闭下拉刷新
ScrollViewContext.closeTwoLevel	关闭下拉二级
ScrollViewContext.scrollIntoView	滚动至指定位置
ScrollViewContext.scrollTo	滚动至指定位置
ScrollViewContext.triggerRefresh	触发下拉刷新
ScrollViewContext.triggerTwoLevel	触发下拉二级
动画	
名称	功能
wx.createAnimation	创建一个动画实例 animation
Animation	动画对象
名称	功能
Animation.backgroundColor	设置背景色
Animation.bottom	设置 bottom 值
Animation.export	导出动画队列
Animation.height	设置高度
Animation.left	设置 left 值
Animation.matrix	同 transform-function matrix
Animation.matrix3d	同 transform-function matrix3d
Animation.opacity	设置透明度
Animation.right	设置 right 值
Animation.rotate	从原点顺时针旋转一个角度
Animation.rotate3d	从 固定 轴顺时针旋转一个角度
Animation.rotateX	从 X 轴顺时针旋转一个角度
Animation.rotateY	从 Y 轴顺时针旋转一个角度
Animation.rotateZ	从 Z 轴顺时针旋转一个角度
Animation.scale	缩放
Animation.scale3d	缩放
Animation.scaleX	缩放 X 轴
Animation.scaleY	缩放 Y 轴
Animation.scaleZ	缩放 Z 轴
Animation.skew	对 X、Y 轴坐标进行倾斜
Animation.skewX	对 X 轴坐标进行倾斜
Animation.skewY	对 Y 轴坐标进行倾斜
Animation.step	表示一组动画完成
Animation.top	设置 top 值
Animation.translate	平移变换
Animation.translate3d	对 xyz 坐标进行平移变换
Animation.translateX	对 X 轴平移
Animation.translateY	对 Y 轴平移
Animation.translateZ	对 Z 轴平移
Animation.width	设置宽度
置顶	
名称	功能
wx.setTopBarText	动态设置置顶栏文字内容
自定义组件	
名称	功能
wx.nextTick	延迟一部分操作到下一个时间片再执行
菜单	
名称	功能
wx.onUserTriggerTranslation	监听用户触发小程序菜单中翻译功能的事件
wx.onUserOffTranslation	监听用户主动取消翻译的事件
wx.onMenuButtonBoundingClientRectWeightChange	监听菜单按钮（右上角胶囊按钮）的布局位置信息变化事件
wx.offUserTriggerTranslation	移除用户触发小程序菜单中翻译功能的事件的监听函数
wx.offUserOffTranslation	移除用户主动取消翻译的事件的监听函数
wx.offMenuButtonBoundingClientRectWeightChange	移除菜单按钮（右上角胶囊按钮）的布局位置信息变化事件的监听函数
wx.getMenuButtonBoundingClientRect	获取菜单按钮（右上角胶囊按钮）的布局位置信息
窗口	
名称	功能
wx.setWindowSize	设置窗口大小，该接口仅适用于 PC 平台，使用细则请参见指南
wx.onWindowStateChange	监听小程序窗口状态变化事件
wx.onWindowResize	监听窗口尺寸变化事件
wx.onParallelStateChange	监听小程序分栏状态变化事件
wx.offWindowStateChange	移除小程序窗口状态变化事件的监听函数
wx.offWindowResize	移除窗口尺寸变化事件的监听函数
wx.offParallelStateChange	移除小程序分栏状态变化事件的监听函数
wx.checkIsPictureInPictureActive	返回当前是否存在小窗播放（小窗在 video/live-player/live-pusher 下可用）
worklet 动画	
名称	功能
wx.worklet	worklet 对象，可以通过 wx.worklet 获取
基础	
名称	功能
worklet.cancelAnimation	取消由 SharedValue 驱动的动画
worklet.derived	衍生值 DerivedValue，可基于已有的 SharedValue 生成其它共享变量
worklet.scrollViewContext	ScrollView 实例，可在 worklet 函数内操作 scroll-view 组件
worklet.scrollViewContext.scrollTo	滚动至指定位置
worklet.shared	创建共享变量 SharedValue，用于跨线程共享数据和驱动动画
动画	
名称	功能
worklet.decay	基于滚动衰减的动画
worklet.Easing	Easing 模块实现了常见的动画缓动函数（动画效果参考 https://easings.net/ ），可从 wx.worklet 对象中读取
worklet.spring	基于物理的动画
worklet.timing	基于时间的动画
组合动画	
名称	功能
worklet.delay	延迟执行动画
worklet.repeat	重复执行动画
worklet.sequence	组合动画序列，依次执行传入的动画
工具函数	
名称	功能
worklet.runOnJS	worklet 函数运行在 UI 线程时，捕获的外部函数可能为 worklet 类型或普通函数，为了更明显的对其区分，要求必须使用 runOnJS 调回 JS 线程的普通函数
worklet.runOnUI	在 UI 线程执行 worklet 函数
网络
名称	功能
发起请求	
名称	功能
wx.request	发起 HTTPS 网络请求
RequestTask	网络请求任务对象
名称	功能
RequestTask.abort	中断请求任务
RequestTask.offChunkReceived	移除 Transfer-Encoding Chunk Received 事件的监听函数
RequestTask.offHeadersReceived	移除 HTTP Response Header 事件的监听函数
RequestTask.onChunkReceived	监听 Transfer-Encoding Chunk Received 事件
RequestTask.onHeadersReceived	监听 HTTP Response Header 事件
下载	
名称	功能
wx.downloadFile	下载文件资源到本地
DownloadTask	一个可以监听下载进度变化事件，以及取消下载任务的对象
名称	功能
DownloadTask.abort	中断下载任务
DownloadTask.offHeadersReceived	移除 HTTP Response Header 事件的监听函数
DownloadTask.offProgressUpdate	移除下载进度变化事件的监听函数
DownloadTask.onHeadersReceived	监听 HTTP Response Header 事件
DownloadTask.onProgressUpdate	监听下载进度变化事件
上传	
名称	功能
wx.uploadFile	将本地资源上传到服务器
UploadTask	一个可以监听上传进度变化事件，以及取消上传任务的对象
名称	功能
UploadTask.abort	中断上传任务
UploadTask.offHeadersReceived	移除 HTTP Response Header 事件的监听函数
UploadTask.offProgressUpdate	移除上传进度变化事件的监听函数
UploadTask.onHeadersReceived	监听 HTTP Response Header 事件
UploadTask.onProgressUpdate	监听上传进度变化事件
WebSocket	
名称	功能
wx.sendSocketMessage	通过 WebSocket 连接发送数据
wx.onSocketOpen	监听 WebSocket 连接打开事件
wx.onSocketMessage	监听 WebSocket 接收到服务器的消息事件
wx.onSocketError	监听 WebSocket 错误事件
wx.onSocketClose	监听 WebSocket 连接关闭事件
wx.connectSocket	创建一个 WebSocket 连接
wx.closeSocket	关闭 WebSocket 连接
SocketTask	WebSocket 任务，可通过 wx.connectSocket() 接口创建返回
名称	功能
SocketTask.close	关闭 WebSocket 连接
SocketTask.onClose	监听 WebSocket 连接关闭事件
SocketTask.onError	监听 WebSocket 错误事件
SocketTask.onMessage	监听 WebSocket 接收到服务器的消息事件
SocketTask.onOpen	监听 WebSocket 连接打开事件
SocketTask.send	通过 WebSocket 连接发送数据
mDNS	
名称	功能
wx.stopLocalServiceDiscovery	停止搜索 mDNS 服务
wx.startLocalServiceDiscovery	开始搜索局域网下的 mDNS 服务
wx.onLocalServiceResolveFail	监听 mDNS 服务解析失败的事件
wx.onLocalServiceLost	监听 mDNS 服务离开的事件
wx.onLocalServiceFound	监听 mDNS 服务发现的事件
wx.onLocalServiceDiscoveryStop	监听 mDNS 服务停止搜索的事件
wx.offLocalServiceResolveFail	移除 mDNS 服务解析失败的事件的监听函数
wx.offLocalServiceLost	移除 mDNS 服务离开的事件的监听函数
wx.offLocalServiceFound	移除 mDNS 服务发现的事件的监听函数
wx.offLocalServiceDiscoveryStop	移除 mDNS 服务停止搜索的事件的监听函数
TCP 通信	
名称	功能
wx.createTCPSocket	创建一个 TCP Socket 实例
TCPSocket	一个 TCP Socket 实例，默认使用 IPv4 协议
名称	功能
TCPSocket.bindWifi	将 TCP Socket 绑定到当前 wifi 网络，成功后会触发 onBindWifi 事件（仅安卓支持）
TCPSocket.close	关闭连接
TCPSocket.connect	在给定的套接字上启动连接
TCPSocket.offBindWifi	移除当一个 socket 绑定当前 wifi 网络成功时触发该事件的监听函数
TCPSocket.offClose	移除一旦 socket 完全关闭就发出该事件的监听函数
TCPSocket.offConnect	移除当一个 socket 连接成功建立的时候触发该事件的监听函数
TCPSocket.offError	移除当错误发生时触发的监听函数
TCPSocket.offMessage	移除当接收到数据的时触发该事件的监听函数
TCPSocket.onBindWifi	监听当一个 socket 绑定当前 wifi 网络成功时触发该事件
TCPSocket.onClose	监听一旦 socket 完全关闭就发出该事件
TCPSocket.onConnect	监听当一个 socket 连接成功建立的时候触发该事件
TCPSocket.onError	监听当错误发生时触发
TCPSocket.onMessage	监听当接收到数据的时触发该事件
TCPSocket.write	在 socket 上发送数据
UDP 通信	
名称	功能
wx.createUDPSocket	创建一个 UDP Socket 实例
UDPSocket	一个 UDP Socket 实例，默认使用 IPv4 协议
名称	功能
UDPSocket.bind	绑定一个系统随机分配的可用端口，或绑定一个指定的端口号
UDPSocket.close	关闭 UDP Socket 实例，相当于销毁
UDPSocket.connect	预先连接到指定的 IP 和 port，需要配合 write 方法一起使用
UDPSocket.offClose	移除关闭事件的监听函数
UDPSocket.offError	移除错误事件的监听函数
UDPSocket.offListening	移除开始监听数据包消息的事件的监听函数
UDPSocket.offMessage	移除收到消息的事件的监听函数
UDPSocket.onClose	监听关闭事件
UDPSocket.onError	监听错误事件
UDPSocket.onListening	监听开始监听数据包消息的事件
UDPSocket.onMessage	监听收到消息的事件
UDPSocket.send	向指定的 IP 和 port 发送消息
UDPSocket.setTTL	设置 IP_TTL 套接字选项，用于设置一个 IP 数据包传输时允许的最大跳步数
UDPSocket.write	用法与 send 方法相同，如果没有预先调用 connect 则与 send 无差异（注意即使调用了 connect 也需要在本接口填入地址和端口参数）
支付
名称	功能
wx.requestVirtualPayment	发起米大师虚拟支付
wx.requestPluginPayment	插件中发起支付
wx.requestPayment	发起微信支付
wx.requestMerchantTransfer	商家转账用户确认模式下，在微信客户端通过小程序拉起页面请求用户确认收款
wx.requestCommonPayment	发起通用支付
wx.openHKOfflinePayView	拉起WeChat Pay HK付款码
wx.createGlobalPayment	创建全球支付方式的对象
GlobalPayment	全球收银对象 GlobalPayment
名称	功能
GlobalPayment.abort	用户选择TPG的支付方式，界面会进入加载的Toast，等待开发者前往TPG完成预下单后携带预支付信息和交易单号调用 requestGlobalPayment，若开发者在
TPG预下单未成功或出现异常情况，可调用该接口主动终止TPG支付流程，界面加载的Toast将会隐藏，提示用户下单失败
GlobalPayment.openMethodPicker	拉起全球收银的支付方式选择面板
GlobalPayment.requestGlobalPayment	开发者调用 openMethodPicker 并在返回值 methodKey 中接受到用户选择了TPG的支付方式后，可调用此接口接入TPG的支付流程
数据缓存
名称	功能
wx.setStorageSync	将数据存储在本地缓存中指定的 key 中
wx.setStorage	将数据存储在本地缓存中指定的 key 中
wx.revokeBufferURL	根据 URL 销毁存在内存中的数据
wx.removeStorageSync	wx.removeStorage 的同步版本
wx.removeStorage	从本地缓存中移除指定 key
wx.getStorageSync	从本地缓存中同步获取指定 key 的内容
wx.getStorageInfoSync	wx.getStorageInfo 的同步版本
wx.getStorageInfo	异步获取当前storage的相关信息
wx.getStorage	从本地缓存中异步获取指定 key 的内容
wx.createBufferURL	根据传入的 buffer 创建一个唯一的 URL 存在内存中
wx.clearStorageSync	wx.clearStorage 的同步版本
wx.clearStorage	清理本地数据缓存
wx.batchSetStorageSync	将数据批量存储在本地缓存中指定的 key 中
wx.batchSetStorage	将数据批量存储在本地缓存中指定的 key 中
wx.batchGetStorageSync	从本地缓存中同步批量获取指定 key 的内容
wx.batchGetStorage	从本地缓存中异步批量获取指定 key 的内容
数据预拉取和周期性更新	
名称	功能
wx.setBackgroundFetchToken	设置自定义登录态，在周期性拉取数据时带上，便于第三方服务器验证请求合法性
wx.onBackgroundFetchData	监听收到 backgroundFetch 数据事件
wx.getBackgroundFetchToken	获取设置过的自定义登录态
wx.getBackgroundFetchData	拉取 backgroundFetch 客户端缓存数据
缓存管理器	
名称	功能
wx.createCacheManager	创建缓存管理器
CacheManager	缓存管理器
名称	功能
CacheManager.addRule	添加规则
CacheManager.addRules	批量添加规则，规则写法可参考 CacheManager.addRule
CacheManager.clearCaches	清空所有缓存
CacheManager.clearRules	清空所有规则，同时会删除对应规则下所有缓存
CacheManager.deleteCache	删除缓存
CacheManager.deleteCaches	批量删除缓存
CacheManager.deleteRule	删除规则，同时会删除对应规则下所有缓存
CacheManager.deleteRules	批量删除规则，同时会删除对应规则下所有缓存
CacheManager.match	匹配命中的缓存规则，一般需要和 request 事件搭配使用
CacheManager.off	取消事件监听
CacheManager.on	监听事件
CacheManager.start	开启缓存，仅在 mode 为 none 时生效，调用后缓存管理器的 state 会置为 1
CacheManager.stop	关闭缓存，仅在 mode 为 none 时生效，调用后缓存管理器的 state 会置为 0
数据分析
名称	功能
wx.reportMonitor	自定义业务数据监控上报接口
wx.reportEvent	事件上报
wx.reportAnalytics	自定义分析数据上报接口
wx.getExptInfoSync	给定实验参数数组，获取对应的实验参数值
wx.getCommonConfig	给定实验参数数组，获取对应的实验参数值
画布
名称	功能
wx.createOffscreenCanvas	创建离屏 canvas 实例
wx.createCanvasContext	创建 canvas 的绘图上下文 CanvasContext 对象
wx.canvasToTempFilePath	把当前画布指定区域的内容导出生成指定大小的图片
wx.canvasPutImageData	将像素数据绘制到画布
wx.canvasGetImageData	获取 canvas 区域隐含的像素数据
Canvas	Canvas 实例，可通过 SelectorQuery 获取
名称	功能
Canvas.cancelAnimationFrame	取消由 requestAnimationFrame 添加到计划中的动画帧请求
Canvas.createImage	创建一个图片对象
Canvas.createImageData	创建一个 ImageData 对象
Canvas.createPath2D	创建 Path2D 对象
Canvas.getContext	该方法返回 Canvas 的绘图上下文
Canvas.requestAnimationFrame	在下次进行重绘时执行
Canvas.toDataURL	返回一个包含图片展示的 data URI 
CanvasContext	canvas 组件的绘图上下文
名称	功能
CanvasContext.arc	创建一条弧线
CanvasContext.arcTo	根据控制点和半径绘制圆弧路径
CanvasContext.beginPath	开始创建一个路径
CanvasContext.bezierCurveTo	创建三次方贝塞尔曲线路径
CanvasContext.clearRect	清除画布上在该矩形区域内的内容
CanvasContext.clip	从原始画布中剪切任意形状和尺寸
CanvasContext.closePath	关闭一个路径
CanvasContext.createCircularGradient	创建一个圆形的渐变颜色
CanvasContext.createLinearGradient	创建一个线性的渐变颜色
CanvasContext.createPattern	对指定的图像创建模式的方法，可在指定的方向上重复元图像
CanvasContext.draw	将之前在绘图上下文中的描述（路径、变形、样式）画到 canvas 中
CanvasContext.drawImage	绘制图像到画布
CanvasContext.fill	对当前路径中的内容进行填充
CanvasContext.fillRect	填充一个矩形
CanvasContext.fillText	在画布上绘制被填充的文本
CanvasContext.lineTo	增加一个新点，然后创建一条从上次指定点到目标点的线
CanvasContext.measureText	测量文本尺寸信息
CanvasContext.moveTo	把路径移动到画布中的指定点，不创建线条
CanvasContext.quadraticCurveTo	创建二次贝塞尔曲线路径
CanvasContext.rect	创建一个矩形路径
CanvasContext.restore	恢复之前保存的绘图上下文
CanvasContext.rotate	以原点为中心顺时针旋转当前坐标轴
CanvasContext.save	保存绘图上下文
CanvasContext.scale	在调用后，之后创建的路径其横纵坐标会被缩放
CanvasContext.setFillStyle	设置填充色
CanvasContext.setFontSize	设置字体的字号
CanvasContext.setGlobalAlpha	设置全局画笔透明度
CanvasContext.setLineCap	设置线条的端点样式
CanvasContext.setLineDash	设置虚线样式
CanvasContext.setLineJoin	设置线条的交点样式
CanvasContext.setLineWidth	设置线条的宽度
CanvasContext.setMiterLimit	设置最大斜接长度
CanvasContext.setShadow	设定阴影样式
CanvasContext.setStrokeStyle	设置描边颜色
CanvasContext.setTextAlign	设置文字的对齐
CanvasContext.setTextBaseline	设置文字的竖直对齐
CanvasContext.setTransform	使用矩阵重新设置（覆盖）当前变换的方法
CanvasContext.stroke	画出当前路径的边框
CanvasContext.strokeRect	画一个矩形(非填充)
CanvasContext.strokeText	给定的 (x, y) 位置绘制文本描边的方法
CanvasContext.transform	使用矩阵多次叠加当前变换的方法
CanvasContext.translate	对当前坐标系的原点 (0, 0) 进行变换
CanvasGradient	渐变对象
名称	功能
CanvasGradient.addColorStop	添加颜色的渐变点
Color	颜色
Image	图片对象
ImageData	ImageData 对象
OffscreenCanvas	离屏 canvas 实例，可通过 wx.createOffscreenCanvas 创建
名称	功能
OffscreenCanvas.createImage	创建一个图片对象
OffscreenCanvas.getContext	该方法返回 OffscreenCanvas 的绘图上下文
Path2D	Canvas 2D API 的接口 Path2D 用来声明路径，此路径稍后会被CanvasRenderingContext2D 对象使用
名称	功能
Path2D.addPath	添加路径到当前路径
Path2D.arc	添加一段圆弧路径
Path2D.arcTo	通过给定控制点添加一段圆弧路径
Path2D.bezierCurveTo	添加三次贝塞尔曲线路径
Path2D.closePath	闭合路径到起点
Path2D.ellipse	添加椭圆弧路径
Path2D.lineTo	添加直线路径
Path2D.moveTo	移动路径开始点
Path2D.quadraticCurveTo	添加二次贝塞尔曲线路径
Path2D.rect	添加方形路径
RenderingContext	Canvas 绘图上下文
媒体
名称	功能
地图	
名称	功能
wx.createMapContext	创建 map 上下文 MapContext 对象
MapContext	MapContext 实例，可通过 wx.createMapContext 获取
名称	功能
MapContext.addArc	添加弧线，途经点与夹角必须设置一个
MapContext.addCustomLayer	添加个性化图层
MapContext.addGroundOverlay	创建自定义图片图层，图片会随着地图缩放而缩放
MapContext.addMarkers	添加 marker
MapContext.addVisualLayer	添加可视化图层
MapContext.eraseLines	擦除或置灰已添加到地图中的线段
MapContext.executeVisualLayerCommand	执行可视化图层指令，结合 MapContext.on('visualLayerEvent') 监听事件使用
MapContext.fromScreenLocation	获取屏幕上的点对应的经纬度，坐标原点为地图左上角
MapContext.getCenterLocation	获取当前地图中心的经纬度
MapContext.getRegion	获取当前地图的视野范围
MapContext.getRotate	获取当前地图的旋转角
MapContext.getScale	获取当前地图的缩放级别
MapContext.getSkew	获取当前地图的倾斜角
MapContext.includePoints	缩放视野展示所有经纬度
MapContext.initMarkerCluster	初始化点聚合的配置，未调用时采用默认配置
MapContext.moveAlong	沿指定路径移动 marker，用于轨迹回放等场景
MapContext.moveToLocation	将地图中心移置当前定位点，此时需设置地图组件 show-location 为true
MapContext.on	监听地图事件
MapContext.openMapApp	拉起地图APP选择导航
MapContext.removeArc	删除弧线
MapContext.removeCustomLayer	移除个性化图层
MapContext.removeGroundOverlay	移除自定义图片图层
MapContext.removeMarkers	移除 marker
MapContext.removeVisualLayer	移除可视化图层
MapContext.setBoundary	限制地图的显示范围
MapContext.setCenterOffset	设置地图中心点偏移，向后向下为增长，屏幕比例范围(0.25~0.75)，默认偏移为[0.5, 0.5]
MapContext.setLocMarkerIcon	设置定位点图标，支持网络路径、本地路径、代码包路径
MapContext.toScreenLocation	获取经纬度对应的屏幕坐标，坐标原点为地图左上角
MapContext.translateMarker	平移marker，带动画
MapContext.updateGroundOverlay	更新自定义图片图层
图片	
名称	功能
wx.saveImageToPhotosAlbum	保存图片到系统相册
wx.previewMedia	预览图片和视频
wx.previewImage	在新页面中全屏预览图片
wx.getImageInfo	获取图片信息
wx.editImage	编辑图片接口
wx.cropImage	裁剪图片接口
wx.compressImage	压缩图片接口，可选压缩质量
wx.chooseMessageFile	从客户端会话选择文件
wx.chooseImage	从本地相册选择图片或使用相机拍照
视频	
名称	功能
wx.saveVideoToPhotosAlbum	保存视频到系统相册
wx.openVideoEditor	打开视频编辑器
wx.getVideoInfo	获取视频详细信息
wx.createVideoContext	创建 video 上下文 VideoContext 对象
wx.compressVideo	压缩视频接口
wx.chooseVideo	拍摄视频或从手机相册中选视频
wx.chooseMedia	拍摄或从手机相册中选择图片或视频
wx.checkDeviceSupportHevc	查询设备是否支持 H.265 编码
VideoContext	VideoContext 实例，可通过 wx.createVideoContext 获取
名称	功能
VideoContext.exitBackgroundPlayback	退出后台音频播放模式
VideoContext.exitCasting	退出投屏
VideoContext.exitFullScreen	退出全屏
VideoContext.exitPictureInPicture	退出小窗，该方法可在任意页面调用
VideoContext.hideStatusBar	隐藏状态栏，仅在iOS全屏下有效
VideoContext.pause	暂停视频
VideoContext.play	播放视频
VideoContext.playbackRate	设置倍速播放
VideoContext.reconnectCasting	重连投屏设备
VideoContext.requestBackgroundPlayback	进入后台音频播放模式
VideoContext.requestFullScreen	进入全屏
VideoContext.seek	跳转到指定位置
VideoContext.sendDanmu	发送弹幕
VideoContext.showStatusBar	显示状态栏，仅在iOS全屏下有效
VideoContext.startCasting	开始投屏, 拉起半屏搜索设备
VideoContext.stop	停止视频
VideoContext.switchCasting	切换投屏设备
音频	
名称	功能
wx.stopVoice	结束播放语音
wx.setInnerAudioOption	设置 InnerAudioContext 的播放选项
wx.playVoice	开始播放语音
wx.pauseVoice	暂停正在播放的语音
wx.getAvailableAudioSources	获取当前支持的音频输入源
wx.createWebAudioContext	创建 WebAudio 上下文
wx.createMediaAudioPlayer	创建媒体音频播放器对象 MediaAudioPlayer 对象，可用于播放视频解码器 VideoDecoder 输出的音频
wx.createInnerAudioContext	创建内部 audio 上下文 InnerAudioContext 对象
wx.createAudioContext	创建 audio 上下文 AudioContext 对象
AudioBuffer	AudioBuffer接口表示存在内存里的一段短小的音频资源，利用WebAudioContext.decodeAudioData方法从一个音频文件构建，或者利用 WebAudioContext.createBuffer从原始数据构建
名称	功能
AudioBuffer.copyFromChannel	从AudioBuffer的指定频道复制到数组终端
AudioBuffer.copyToChannel	从指定数组复制样本到audioBuffer的特定通道
AudioBuffer.getChannelData	返回一个 Float32Array，包含了带有频道的PCM数据，由频道参数定义（有0代表第一个频道）
AudioContext	AudioContext 实例，可通过 wx.createAudioContext 获取
名称	功能
AudioContext.pause	暂停音频
AudioContext.play	播放音频
AudioContext.seek	跳转到指定位置
AudioContext.setSrc	设置音频地址
AudioListener	空间音频监听器，代表在一个音频场景内唯一的位置和方向信息
AudioParam	AudioParam 接口代表音频相关的参数，通常是 AudioNode（例如 GainNode.gain）的参数
BufferSourceNode	音频源节点，通过 WebAudioContext.createBufferSource方法获得
名称	功能
BufferSourceNode.connect	连接到一个指定目标
BufferSourceNode.disconnect	与已连接的目标节点断开连接
BufferSourceNode.start	音频源开始播放
BufferSourceNode.stop	停止播放
InnerAudioContext	InnerAudioContext 实例，可通过 wx.createInnerAudioContext 接口获取实例
名称	功能
InnerAudioContext.destroy	销毁当前实例
InnerAudioContext.offCanplay	移除音频进入可以播放状态的事件的监听函数
InnerAudioContext.offEnded	移除音频自然播放至结束的事件的监听函数
InnerAudioContext.offError	移除音频播放错误事件的监听函数
InnerAudioContext.offPause	移除音频暂停事件的监听函数
InnerAudioContext.offPlay	移除音频播放事件的监听函数
InnerAudioContext.offSeeked	移除音频完成跳转操作的事件的监听函数
InnerAudioContext.offSeeking	移除音频进行跳转操作的事件的监听函数
InnerAudioContext.offStop	移除音频停止事件的监听函数
InnerAudioContext.offTimeUpdate	移除音频播放进度更新事件的监听函数
InnerAudioContext.offWaiting	移除音频加载中事件的监听函数
InnerAudioContext.onCanplay	监听音频进入可以播放状态的事件
InnerAudioContext.onEnded	监听音频自然播放至结束的事件
InnerAudioContext.onError	监听音频播放错误事件
InnerAudioContext.onPause	监听音频暂停事件
InnerAudioContext.onPlay	监听音频播放事件
InnerAudioContext.onSeeked	监听音频完成跳转操作的事件
InnerAudioContext.onSeeking	监听音频进行跳转操作的事件
InnerAudioContext.onStop	监听音频停止事件
InnerAudioContext.onTimeUpdate	监听音频播放进度更新事件
InnerAudioContext.onWaiting	监听音频加载中事件
InnerAudioContext.pause	暂停
InnerAudioContext.play	播放
InnerAudioContext.seek	跳转到指定位置
InnerAudioContext.stop	停止
MediaAudioPlayer	MediaAudioPlayer 实例，可通过 wx.createMediaAudioPlayer 接口获取实例
名称	功能
MediaAudioPlayer.addAudioSource	添加音频源
MediaAudioPlayer.destroy	销毁播放器
MediaAudioPlayer.removeAudioSource	移除音频源
MediaAudioPlayer.start	启动播放器
MediaAudioPlayer.stop	停止播放器
WebAudioContext	WebAudioContext 实例，通过wx.createWebAudioContext 接口获取该实例
名称	功能
WebAudioContext.close	关闭WebAudioContext
WebAudioContext.createAnalyser	创建一个 AnalyserNode 
WebAudioContext.createBiquadFilter	创建一个BiquadFilterNode
WebAudioContext.createBuffer	创建一个AudioBuffer，代表着一段驻留在内存中的短音频
WebAudioContext.createBufferSource	创建一个BufferSourceNode实例，通过AudioBuffer对象来播放音频数据
WebAudioContext.createChannelMerger	创建一个ChannelMergerNode
WebAudioContext.createChannelSplitter	创建一个ChannelSplitterNode
WebAudioContext.createConstantSource	创建一个ConstantSourceNode
WebAudioContext.createDelay	创建一个DelayNode
WebAudioContext.createDynamicsCompressor	创建一个DynamicsCompressorNode
WebAudioContext.createGain	创建一个GainNode
WebAudioContext.createIIRFilter	创建一个IIRFilterNode
WebAudioContext.createOscillator	创建一个OscillatorNode
WebAudioContext.createPanner	创建一个PannerNode
WebAudioContext.createPeriodicWave	创建一个PeriodicWaveNode
WebAudioContext.createScriptProcessor	创建一个ScriptProcessorNode
WebAudioContext.createWaveShaper	创建一个WaveShaperNode
WebAudioContext.decodeAudioData	异步解码一段资源为AudioBuffer
WebAudioContext.resume	同步恢复已经被暂停的WebAudioContext上下文
WebAudioContext.suspend	同步暂停WebAudioContext上下文
WebAudioContextNode	一类音频处理模块，不同的Node具备不同的功能，如GainNode(音量调整)等
背景音频	
名称	功能
wx.stopBackgroundAudio	停止播放音乐
wx.seekBackgroundAudio	控制音乐播放进度
wx.playBackgroundAudio	使用后台播放器播放音乐
wx.pauseBackgroundAudio	暂停播放音乐
wx.onBackgroundAudioStop	监听音乐停止事件
wx.onBackgroundAudioPlay	监听音乐播放事件
wx.onBackgroundAudioPause	监听音乐暂停事件
wx.getBackgroundAudioPlayerState	获取后台音乐播放状态
wx.getBackgroundAudioManager	获取全局唯一的背景音频管理器
BackgroundAudioManager	BackgroundAudioManager 实例，可通过 wx.getBackgroundAudioManager 获取
名称	功能
BackgroundAudioManager.onCanplay	监听背景音频进入可播放状态事件
BackgroundAudioManager.onEnded	监听背景音频自然播放结束事件
BackgroundAudioManager.onError	监听背景音频播放错误事件
BackgroundAudioManager.onNext	监听用户在系统音乐播放面板点击下一曲事件
BackgroundAudioManager.onPause	监听背景音频暂停事件
BackgroundAudioManager.onPlay	监听背景音频播放事件
BackgroundAudioManager.onPrev	监听用户在系统音乐播放面板点击上一曲事件
BackgroundAudioManager.onSeeked	监听背景音频完成跳转操作事件
BackgroundAudioManager.onSeeking	监听背景音频开始跳转操作事件
BackgroundAudioManager.onStop	监听背景音频停止事件
BackgroundAudioManager.onTimeUpdate	监听背景音频播放进度更新事件，只有小程序在前台时会回调
BackgroundAudioManager.onWaiting	监听音频加载中事件
BackgroundAudioManager.pause	暂停音乐
BackgroundAudioManager.play	播放音乐
BackgroundAudioManager.seek	跳转到指定位置
BackgroundAudioManager.stop	停止音乐
实时音视频	
名称	功能
wx.createLivePusherContext	创建 live-pusher 上下文 LivePusherContext 对象
wx.createLivePlayerContext	创建 live-player 上下文 LivePlayerContext 对象
LivePlayerContext	LivePlayerContext 实例，可通过 wx.createLivePlayerContext 获取
名称	功能
LivePlayerContext.exitBackgroundPlayback	退出后台音频播放模式
LivePlayerContext.exitCasting	退出投屏
LivePlayerContext.exitFullScreen	退出全屏
LivePlayerContext.exitPictureInPicture	退出小窗，该方法可在任意页面调用
LivePlayerContext.mute	静音
LivePlayerContext.pause	暂停
LivePlayerContext.play	播放
LivePlayerContext.reconnectCasting	重连投屏设备
LivePlayerContext.requestBackgroundPlayback	进入后台音频播放模式
LivePlayerContext.requestFullScreen	进入全屏
LivePlayerContext.resume	恢复
LivePlayerContext.snapshot	截图
LivePlayerContext.startCasting	开始投屏, 拉起半屏搜索设备
LivePlayerContext.stop	停止
LivePlayerContext.switchCasting	切换投屏设备
LivePusherContext	LivePusherContext 实例，可通过 wx.createLivePusherContext 获取
名称	功能
LivePusherContext.applyBlusherStickMakeup	添加腮红美妆特效
LivePusherContext.applyEyeBrowMakeup	添加眉毛美妆特效
LivePusherContext.applyEyeShadowMakeup	添加眼影美妆特效
LivePusherContext.applyFaceContourMakeup	添加修容美妆特效
LivePusherContext.applyFilter	添加滤镜效果
LivePusherContext.applyLipStickMakeup	添加口红美妆特效
LivePusherContext.applySticker	添加贴纸特效
LivePusherContext.clearFilters	清除所有滤镜效果
LivePusherContext.clearMakeups	清除所有美妆特效
LivePusherContext.clearStickers	清除所有贴纸特效
LivePusherContext.createOffscreenCanvas	创建一个能够承接 LivePusher 采集纹理的离屏 Canvas，客户端 8.0.31 版本开始支持
LivePusherContext.exitPictureInPicture	退出小窗，该方法可在任意页面调用
LivePusherContext.getMaxZoom	获取最大缩放级别
LivePusherContext.onCustomRendererEvent	开启自定义渲染时，开发者通过此方法订阅相关事件，客户端 8.0.31 版本开始支持
LivePusherContext.pause	暂停推流
LivePusherContext.pauseBGM	暂停背景音
LivePusherContext.playBGM	播放背景音
LivePusherContext.resume	恢复推流
LivePusherContext.resumeBGM	恢复背景音
LivePusherContext.sendMessage	发送SEI消息
LivePusherContext.setBGMVolume	设置背景音音量
LivePusherContext.setMICVolume	设置麦克风音量
LivePusherContext.setZoom	设置缩放级别
LivePusherContext.snapshot	快照
LivePusherContext.start	开始推流，同时开启摄像头预览
LivePusherContext.startPreview	开启摄像头预览
LivePusherContext.stop	停止推流，同时停止摄像头预览
LivePusherContext.stopBGM	停止背景音
LivePusherContext.stopPreview	关闭摄像头预览
LivePusherContext.switchCamera	切换前后摄像头
LivePusherContext.toggleTorch	切换手电筒
录音	
名称	功能
wx.stopRecord	停止录音
wx.startRecord	开始录音
wx.getRecorderManager	获取全局唯一的录音管理器 RecorderManager
RecorderManager	全局唯一的录音管理器
名称	功能
RecorderManager.onError	监听录音错误事件
RecorderManager.onFrameRecorded	监听已录制完指定帧大小的文件事件
RecorderManager.onInterruptionBegin	监听录音因为受到系统占用而被中断开始事件
RecorderManager.onInterruptionEnd	监听录音中断结束事件
RecorderManager.onPause	监听录音暂停事件
RecorderManager.onResume	监听录音继续事件
RecorderManager.onStart	监听录音开始事件
RecorderManager.onStop	监听录音结束事件
RecorderManager.pause	暂停录音
RecorderManager.resume	继续录音
RecorderManager.start	开始录音
RecorderManager.stop	停止录音
相机	
名称	功能
wx.createCameraContext	创建 camera 上下文 CameraContext 对象
CameraContext	CameraContext 实例，可通过 wx.createCameraContext 获取
名称	功能
CameraContext.onCameraFrame	获取 Camera 实时帧数据
CameraContext.setZoom	设置缩放级别
CameraContext.startRecord	开始录像
CameraContext.stopRecord	结束录像
CameraContext.takePhoto	拍摄照片
CameraFrameListener	CameraContext.onCameraFrame() 返回的监听器
名称	功能
CameraFrameListener.start	开始监听帧数据
CameraFrameListener.stop	停止监听帧数据
富文本	
名称	功能
EditorContext	EditorContext 实例，可通过 wx.createSelectorQuery 获取
名称	功能
EditorContext.blur	编辑器失焦，同时收起键盘
EditorContext.clear	清空编辑器内容
EditorContext.deleteText	删除指定选取区的内容
EditorContext.format	修改样式
EditorContext.getBounds	获取指定选区的位置和大小
EditorContext.getContents	获取编辑器内容
EditorContext.getHistoryState	获取历史操作状态
EditorContext.getSelection	获取当前选区
EditorContext.getSelectionText	获取编辑器已选区域内的纯文本内容
EditorContext.insertCustomBlock	插入自定义区块
EditorContext.insertDivider	插入分割线
EditorContext.insertImage	插入图片
EditorContext.insertText	覆盖当前选区，设置一段文本
EditorContext.redo	恢复
EditorContext.removeFormat	清除当前选区的样式
EditorContext.scrollIntoView	使得编辑器光标处滚动到窗口可视区域内
EditorContext.setContents	初始化编辑器内容，html和delta同时存在时仅delta生效
EditorContext.setSelection	设置当前选区
EditorContext.undo	撤销
音视频合成	
名称	功能
wx.createMediaContainer	创建音视频处理容器，最终可将容器中的轨道合成一个视频
MediaContainer	可通过 wx.createMediaContainer 创建
名称	功能
MediaContainer.addTrack	将音频或视频轨道添加到容器
MediaContainer.destroy	将容器销毁，释放资源
MediaContainer.export	将容器内的轨道合并并导出视频文件
MediaContainer.extractDataSource	将传入的视频源分离轨道
MediaContainer.removeTrack	将音频或视频轨道从容器中移除
MediaTrack	可通过 MediaContainer.extractDataSource 返回
实时语音	
名称	功能
wx.updateVoIPChatMuteConfig	更新实时语音静音设置
wx.subscribeVoIPVideoMembers	订阅视频画面成员
wx.setEnable1v1Chat	开启双人通话
wx.onVoIPVideoMembersChanged	监听实时语音通话成员视频状态变化事件
wx.onVoIPChatStateChanged	监听房间状态变化事件
wx.onVoIPChatSpeakersChanged	监听实时语音通话成员通话状态变化事件
wx.onVoIPChatMembersChanged	监听实时语音通话成员在线状态变化事件
wx.onVoIPChatInterrupted	监听被动断开实时语音通话事件
wx.offVoIPVideoMembersChanged	移除实时语音通话成员视频状态变化事件的监听函数
wx.offVoIPChatStateChanged	移除房间状态变化事件的监听函数
wx.offVoIPChatSpeakersChanged	移除实时语音通话成员通话状态变化事件的监听函数
wx.offVoIPChatMembersChanged	移除实时语音通话成员在线状态变化事件的监听函数
wx.offVoIPChatInterrupted	移除被动断开实时语音通话事件的监听函数
wx.joinVoIPChat	加入 (创建) 实时语音通话，更多信息可见 实时语音指南
wx.join1v1Chat	加入（创建）双人通话
wx.exitVoIPChat	退出（销毁）实时语音通话
画面录制器	
名称	功能
wx.createMediaRecorder	创建 WebGL 画面录制器，可逐帧录制在 WebGL 上渲染的画面并导出视频文件
MediaRecorder	可通过 wx.createMediaRecorder 创建
名称	功能
MediaRecorder.destroy	销毁录制器
MediaRecorder.off	取消监听录制事件
MediaRecorder.on	注册监听录制事件的回调函数
MediaRecorder.pause	暂停录制
MediaRecorder.requestFrame	请求下一帧录制，在 callback 里完成一帧渲染后开始录制当前帧
MediaRecorder.resume	恢复录制
MediaRecorder.start	开始录制
MediaRecorder.stop	结束录制
视频解码器	
名称	功能
wx.createVideoDecoder	创建视频解码器，可逐帧获取解码后的数据
VideoDecoder	可通过 wx.createVideoDecoder 创建
名称	功能
VideoDecoder.getFrameData	获取下一帧的解码数据
VideoDecoder.off	取消监听录制事件
VideoDecoder.on	注册监听录制事件的回调函数
VideoDecoder.remove	移除解码器
VideoDecoder.seek	跳到某个时间点解码
VideoDecoder.start	开始解码
VideoDecoder.stop	停止解码
位置
名称	功能
wx.stopLocationUpdate	关闭监听实时位置变化，前后台都停止消息接收
wx.startLocationUpdateBackground	开启小程序在前后台时均可接收位置消息，后台包括离开小程序后继续使用微信（微信仍在前台）、离开微信（微信在后台）两个场景，需引导用户开启授权
wx.startLocationUpdate	开启小程序进入前台时接收位置消息
wx.openLocation	使用微信内置地图查看位置
wx.onLocationChangeError	监听持续定位接口返回失败时触发
wx.onLocationChange	监听实时地理位置变化事件，需结合 wx.startLocationUpdateBackground、wx.startLocationUpdate使用
wx.offLocationChangeError	移除持续定位接口返回失败时触发
wx.offLocationChange	移除实时地理位置变化事件的监听函数
wx.getLocation	获取当前的地理位置、速度
wx.getFuzzyLocation	获取当前的模糊地理位置
wx.choosePoi	打开POI列表选择位置，支持模糊定位（精确到市）和精确定位混选
wx.chooseLocation	打开地图选择位置
文件
名称	功能
wx.saveFileToDisk	保存文件系统的文件到用户磁盘，仅在 PC 端支持
wx.openDocument	新开页面打开文档
wx.getFileSystemManager	获取全局唯一的文件管理器
FileStats	每个 FileStats 对象包含 path 和 Stats
FileSystemManager	文件管理器，可通过 wx.getFileSystemManager 获取
名称	功能
FileSystemManager.access	判断文件/目录是否存在
FileSystemManager.accessSync	FileSystemManager.access 的同步版本
FileSystemManager.appendFile	在文件结尾追加内容
FileSystemManager.appendFileSync	FileSystemManager.appendFile 的同步版本
FileSystemManager.close	关闭文件
FileSystemManager.closeSync	同步关闭文件
FileSystemManager.copyFile	复制文件
FileSystemManager.copyFileSync	FileSystemManager.copyFile 的同步版本
FileSystemManager.fstat	获取文件的状态信息
FileSystemManager.fstatSync	同步获取文件的状态信息
FileSystemManager.ftruncate	对文件内容进行截断操作
FileSystemManager.ftruncateSync	对文件内容进行截断操作
FileSystemManager.getFileInfo	获取该小程序下的 本地临时文件 或 本地缓存文件 信息
FileSystemManager.getSavedFileList	获取该小程序下已保存的本地缓存文件列表
FileSystemManager.mkdir	创建目录
FileSystemManager.mkdirSync	FileSystemManager.mkdir 的同步版本
FileSystemManager.open	打开文件，返回文件描述符
FileSystemManager.openSync	同步打开文件，返回文件描述符
FileSystemManager.read	读文件
FileSystemManager.readCompressedFile	读取指定压缩类型的本地文件内容
FileSystemManager.readCompressedFileSync	同步读取指定压缩类型的本地文件内容
FileSystemManager.readdir	读取目录内文件列表
FileSystemManager.readdirSync	FileSystemManager.readdir 的同步版本
FileSystemManager.readFile	读取本地文件内容
FileSystemManager.readFileSync	FileSystemManager.readFile 的同步版本
FileSystemManager.readSync	读文件
FileSystemManager.readZipEntry	读取压缩包内的文件
FileSystemManager.removeSavedFile	删除该小程序下已保存的本地缓存文件
FileSystemManager.rename	重命名文件
FileSystemManager.renameSync	FileSystemManager.rename 的同步版本
FileSystemManager.rmdir	删除目录
FileSystemManager.rmdirSync	FileSystemManager.rmdir 的同步版本
FileSystemManager.saveFile	保存临时文件到本地
FileSystemManager.saveFileSync	FileSystemManager.saveFile 的同步版本
FileSystemManager.stat	获取文件 Stats 对象
FileSystemManager.statSync	FileSystemManager.stat 的同步版本
FileSystemManager.truncate	对文件内容进行截断操作
FileSystemManager.truncateSync	对文件内容进行截断操作 (truncate 的同步版本)
FileSystemManager.unlink	删除文件
FileSystemManager.unlinkSync	FileSystemManager.unlink 的同步版本
FileSystemManager.unzip	解压文件
FileSystemManager.write	写入文件
FileSystemManager.writeFile	写文件
FileSystemManager.writeFileSync	FileSystemManager.writeFile 的同步版本
FileSystemManager.writeSync	同步写入文件
ReadResult	文件读取结果
Stats	描述文件状态的对象
名称	功能
Stats.isDirectory	判断当前文件是否一个目录
Stats.isFile	判断当前文件是否一个普通文件
WriteResult	文件写入结果
开放接口
名称	功能
登录	
名称	功能
wx.pluginLogin	该接口仅在小程序插件中可调用，调用接口获得插件用户标志凭证（code）
wx.login	调用接口获取登录凭证（code）
wx.checkSession	检查登录态 session_key 是否过期
账号信息	
名称	功能
wx.getAccountInfoSync	获取当前账号信息
用户信息	
名称	功能
wx.getUserProfile	获取用户信息
wx.getUserInfo	获取用户信息
UserInfo	用户信息
授权	
名称	功能
wx.authorizeForMiniProgram	仅小程序插件中能调用该接口，用法同 wx.authorize
wx.authorize	提前向用户发起授权请求
设置	
名称	功能
wx.openSetting	调起客户端小程序设置界面，返回用户设置的操作结果
wx.getSetting	获取用户的当前设置
AuthSetting	用户授权设置信息，详情参考权限
SubscriptionsSetting	订阅消息设置
收货地址	
名称	功能
wx.chooseAddress	获取用户收货地址
卡券	
名称	功能
wx.openCard	查看微信卡包中的卡券
wx.addCard	批量添加卡券
发票	
名称	功能
wx.chooseInvoiceTitle	选择用户的发票抬头
wx.chooseInvoice	选择用户已有的发票
生物认证	
名称	功能
wx.startSoterAuthentication	开始 SOTER 生物认证
wx.checkIsSupportSoterAuthentication	获取本机支持的 SOTER 生物认证方式
wx.checkIsSoterEnrolledInDevice	获取设备内是否录入如指纹等生物信息的接口
微信运动	
名称	功能
wx.shareToWeRun	分享数据到微信运动
wx.getWeRunData	获取用户过去三十一天微信运动步数
订阅消息	
名称	功能
wx.requestSubscribeMessage	调起客户端小程序订阅消息界面，返回用户订阅消息的操作结果
wx.requestSubscribeDeviceMessage	订阅设备消息接口，调用后弹出授权框，用户同意后会允许开发者给用户发送订阅模版消息
微信红包	
名称	功能
wx.showRedPackage	拉取h5领取红包封面页
微信小店	
名称	功能
wx.openStoreOrderDetail	打开微信小店订单详情页
wx.openStoreCouponDetail	打开微信小店优惠券详情页
收藏	
名称	功能
wx.addVideoToFavorites	收藏视频
wx.addFileToFavorites	收藏文件
用工关系	
名称	功能
wx.requestSubscribeEmployeeMessage	在用户已绑定与该小程序的用工关系后，可拉起用户关系消息订阅列表
wx.checkEmployeeRelation	检查小程序用工关系功能和用户之间的绑定关系
wx.bindEmployeeRelation	拉起小程序用工关系功能绑定弹窗，用户允许后可同步拉起用户关系消息订阅列表
我的小程序	
名称	功能
wx.checkIsAddedToMyMiniProgram	检查小程序是否被添加至 「我的小程序」
人脸检测	
名称	功能
wx.requestFacialVerify	对用户实名信息进行基于生物识别的人脸核身验证
wx.checkIsSupportFacialRecognition	检查当前设备是否支持人脸识别能力
车牌	
名称	功能
wx.chooseLicensePlate	选择车牌号
视频号	
名称	功能
wx.reserveChannelsLive	预约视频号直播
wx.openChannelsUserProfile	打开视频号主页
wx.openChannelsLiveNoticeInfo	打开视频号直播预告半屏
wx.openChannelsLive	打开视频号直播
wx.openChannelsEvent	打开视频号活动页
wx.openChannelsActivity	打开视频号视频
wx.getChannelsShareKey	获取视频号直播卡片/视频卡片的分享来源，仅当卡片携带了分享信息、同时用户已授权该小程序获取视频号分享信息且启动场景值为 1177、1184、1195、1208 时可用
wx.getChannelsLiveNoticeInfo	获取视频号直播预告信息
wx.getChannelsLiveInfo	获取视频号直播信息
音视频通话	
名称	功能
wx.requestDeviceVoIP	请求用户授权与设备（组）间进行音视频通话
wx.getDeviceVoIPList	查询当前用户授权的音视频通话设备（组）信息
微信群	
名称	功能
wx.getGroupEnterInfo	获取微信群聊场景下的小程序启动信息
隐私信息授权	
名称	功能
wx.requirePrivacyAuthorize	模拟隐私接口调用，并触发隐私弹窗逻辑
wx.openPrivacyContract	跳转至隐私协议页面
wx.onNeedPrivacyAuthorization	监听隐私接口需要用户授权事件
wx.getPrivacySetting	查询隐私授权情况
微信客服	
名称	功能
wx.openCustomerServiceChat	打开微信客服，页面产生点击事件后才可调用
微信表情	
名称	功能
wx.openStickerSetView	打开表情专辑
wx.openStickerIPView	打开表情IP合辑
wx.openSingleStickerView	打开单个表情
设备
名称	功能
蓝牙-通用	
名称	功能
wx.stopBluetoothDevicesDiscovery	停止搜寻附近的蓝牙外围设备
wx.startBluetoothDevicesDiscovery	开始搜寻附近的蓝牙外围设备
wx.openBluetoothAdapter	初始化蓝牙模块
wx.onBluetoothDeviceFound	监听搜索到新设备的事件
wx.onBluetoothAdapterStateChange	监听蓝牙适配器状态变化事件
wx.offBluetoothDeviceFound	移除搜索到新设备的事件的全部监听函数
wx.offBluetoothAdapterStateChange	移除蓝牙适配器状态变化事件的全部监听函数
wx.makeBluetoothPair	蓝牙配对接口，仅安卓支持
wx.isBluetoothDevicePaired	查询蓝牙设备是否配对，仅安卓支持
wx.getConnectedBluetoothDevices	根据主服务 UUID 获取已连接的蓝牙设备
wx.getBluetoothDevices	获取在蓝牙模块生效期间所有搜索到的蓝牙设备
wx.getBluetoothAdapterState	获取本机蓝牙适配器状态
wx.closeBluetoothAdapter	关闭蓝牙模块
蓝牙-低功耗中心设备	
名称	功能
wx.writeBLECharacteristicValue	向蓝牙低功耗设备特征值中写入二进制数据
wx.setBLEMTU	协商设置蓝牙低功耗的最大传输单元 (Maximum Transmission Unit, MTU)
wx.readBLECharacteristicValue	读取蓝牙低功耗设备特征值的二进制数据
wx.onBLEMTUChange	监听蓝牙低功耗的最大传输单元变化事件（仅安卓触发）
wx.onBLEConnectionStateChange	监听蓝牙低功耗连接状态改变事件
wx.onBLECharacteristicValueChange	监听蓝牙低功耗设备的特征值变化事件
wx.offBLEMTUChange	移除蓝牙低功耗的最大传输单元变化事件的监听函数
wx.offBLEConnectionStateChange	移除蓝牙低功耗连接状态改变事件的监听函数
wx.offBLECharacteristicValueChange	移除蓝牙低功耗设备的特征值变化事件的全部监听函数
wx.notifyBLECharacteristicValueChange	启用蓝牙低功耗设备特征值变化时的 notify 功能，订阅特征
wx.getBLEMTU	获取蓝牙低功耗的最大传输单元
wx.getBLEDeviceServices	获取蓝牙低功耗设备所有服务 (service)
wx.getBLEDeviceRSSI	获取蓝牙低功耗设备的信号强度 (Received Signal Strength Indication, RSSI)
wx.getBLEDeviceCharacteristics	获取蓝牙低功耗设备某个服务中所有特征 (characteristic)
wx.createBLEConnection	连接蓝牙低功耗设备
wx.closeBLEConnection	断开与蓝牙低功耗设备的连接
蓝牙-低功耗外围设备	
名称	功能
wx.onBLEPeripheralConnectionStateChanged	监听当前外围设备被连接或断开连接事件
wx.offBLEPeripheralConnectionStateChanged	移除当前外围设备被连接或断开连接事件的监听函数
wx.createBLEPeripheralServer	建立本地作为蓝牙低功耗外围设备的服务端，可创建多个
BLEPeripheralServer	外围设备的服务端
名称	功能
BLEPeripheralServer.addService	添加服务
BLEPeripheralServer.close	关闭当前服务端
BLEPeripheralServer.offCharacteristicReadRequest	移除已连接的设备请求读当前外围设备的特征值事件的监听函数
BLEPeripheralServer.offCharacteristicSubscribed	移除特征订阅事件的监听函数
BLEPeripheralServer.offCharacteristicUnsubscribed	移除取消特征订阅事件的监听函数
BLEPeripheralServer.offCharacteristicWriteRequest	移除已连接的设备请求写当前外围设备的特征值事件的监听函数
BLEPeripheralServer.onCharacteristicReadRequest	监听已连接的设备请求读当前外围设备的特征值事件
BLEPeripheralServer.onCharacteristicSubscribed	监听特征订阅事件，仅 iOS 支持
BLEPeripheralServer.onCharacteristicUnsubscribed	监听取消特征订阅事件，仅 iOS 支持
BLEPeripheralServer.onCharacteristicWriteRequest	监听已连接的设备请求写当前外围设备的特征值事件
BLEPeripheralServer.removeService	移除服务
BLEPeripheralServer.startAdvertising	开始广播本地创建的外围设备
BLEPeripheralServer.stopAdvertising	停止广播
BLEPeripheralServer.writeCharacteristicValue	往指定特征写入二进制数据值，并通知已连接的主机，从机的特征值已发生变化，该接口会处理是走回包还是走订阅
蓝牙-信标(Beacon)	
名称	功能
wx.stopBeaconDiscovery	停止搜索附近的 Beacon 设备
wx.startBeaconDiscovery	开始搜索附近的 Beacon 设备
wx.onBeaconUpdate	监听 Beacon 设备更新事件，仅能注册一个监听
wx.onBeaconServiceChange	监听 Beacon 服务状态变化事件，仅能注册一个监听
wx.offBeaconUpdate	移除 Beacon 设备更新事件的全部监听函数
wx.offBeaconServiceChange	移除 Beacon 服务状态变化事件的全部监听函数
wx.getBeacons	获取所有已搜索到的 Beacon 设备
BeaconInfo	Beacon 设备
NFC 读写	
名称	功能
wx.removeSecureElementPass	删除设备中的某一张卡
wx.getSecureElementPasses	获取设备中的所有卡信息
wx.getNFCAdapter	获取 NFC 实例
wx.canAddSecureElementPass	判断设备是否支持添加该支付卡
wx.addPaymentPassGetCertificateData	拉起ApplePay添加卡流程，从PassKit获取证书、nonce与nonce签名
wx.addPaymentPassFinish	通知客户端开卡成功
IsoDep	IsoDep 标签
名称	功能
IsoDep.close	断开连接
IsoDep.connect	连接 NFC 标签
IsoDep.getHistoricalBytes	获取复位信息
IsoDep.getMaxTransceiveLength	获取最大传输长度
IsoDep.isConnected	检查是否已连接
IsoDep.setTimeout	设置超时时间
IsoDep.transceive	发送数据
MifareClassic	MifareClassic 标签
名称	功能
MifareClassic.close	断开连接
MifareClassic.connect	连接 NFC 标签
MifareClassic.getMaxTransceiveLength	获取最大传输长度
MifareClassic.isConnected	检查是否已连接
MifareClassic.setTimeout	设置超时时间
MifareClassic.transceive	发送数据
MifareUltralight	MifareUltralight 标签
名称	功能
MifareUltralight.close	断开连接
MifareUltralight.connect	连接 NFC 标签
MifareUltralight.getMaxTransceiveLength	获取最大传输长度
MifareUltralight.isConnected	检查是否已连接
MifareUltralight.setTimeout	设置超时时间
MifareUltralight.transceive	发送数据
Ndef	Ndef 标签
名称	功能
Ndef.close	断开连接
Ndef.connect	连接 NFC 标签
Ndef.isConnected	检查是否已连接
Ndef.offNdefMessage	取消监听 Ndef 消息
Ndef.onNdefMessage	监听 Ndef 消息
Ndef.setTimeout	设置超时时间
Ndef.writeNdefMessage	重写 Ndef 标签内容
NfcA	NfcA 标签
名称	功能
NfcA.close	断开连接
NfcA.connect	连接 NFC 标签
NfcA.getAtqa	获取ATQA信息
NfcA.getMaxTransceiveLength	获取最大传输长度
NfcA.getSak	获取SAK信息
NfcA.isConnected	检查是否已连接
NfcA.setTimeout	设置超时时间
NfcA.transceive	发送数据
NFCAdapter	
名称	功能
NFCAdapter.getIsoDep	获取IsoDep实例，实例支持ISO-DEP (ISO 14443-4)标准的读写
NFCAdapter.getMifareClassic	获取MifareClassic实例，实例支持MIFARE Classic标签的读写
NFCAdapter.getMifareUltralight	获取MifareUltralight实例，实例支持MIFARE Ultralight标签的读写
NFCAdapter.getNdef	获取Ndef实例，实例支持对NDEF格式的NFC标签上的NDEF数据的读写
NFCAdapter.getNfcA	获取NfcA实例，实例支持NFC-A (ISO 14443-3A)标准的读写
NFCAdapter.getNfcB	获取NfcB实例，实例支持NFC-B (ISO 14443-3B)标准的读写
NFCAdapter.getNfcF	获取NfcF实例，实例支持NFC-F (JIS 6319-4)标准的读写
NFCAdapter.getNfcV	获取NfcV实例，实例支持NFC-V (ISO 15693)标准的读写
NFCAdapter.offDiscovered	移除 NFC Tag的监听函数
NFCAdapter.onDiscovered	监听 NFC Tag
NFCAdapter.startDiscovery	
NFCAdapter.stopDiscovery	
NfcB	NfcB 标签
名称	功能
NfcB.close	断开连接
NfcB.connect	连接 NFC 标签
NfcB.getMaxTransceiveLength	获取最大传输长度
NfcB.isConnected	检查是否已连接
NfcB.setTimeout	设置超时时间
NfcB.transceive	发送数据
NfcF	NfcF 标签
名称	功能
NfcF.close	断开连接
NfcF.connect	连接 NFC 标签
NfcF.getMaxTransceiveLength	获取最大传输长度
NfcF.isConnected	检查是否已连接
NfcF.setTimeout	设置超时时间
NfcF.transceive	发送数据
NfcV	NfcV 标签
名称	功能
NfcV.close	断开连接
NfcV.connect	连接 NFC 标签
NfcV.getMaxTransceiveLength	获取最大传输长度
NfcV.isConnected	检查是否已连接
NfcV.setTimeout	设置超时时间
NfcV.transceive	发送数据
Wi-Fi	
名称	功能
wx.stopWifi	关闭 Wi-Fi 模块
wx.startWifi	初始化 Wi-Fi 模块
wx.setWifiList	设置 wifiList 中 AP 的相关信息
wx.onWifiConnectedWithPartialInfo	监听连接上 Wi-Fi 的事件
wx.onWifiConnected	监听连接上 Wi-Fi 的事件
wx.onGetWifiList	监听获取到 Wi-Fi 列表数据事件
wx.offWifiConnectedWithPartialInfo	移除连接上 Wi-Fi 的事件的监听函数
wx.offWifiConnected	移除连接上 Wi-Fi 的事件的监听函数
wx.offGetWifiList	移除获取到 Wi-Fi 列表数据事件的监听函数
wx.getWifiList	请求获取 Wi-Fi 列表
wx.getConnectedWifi	获取已连接中的 Wi-Fi 信息
wx.connectWifi	连接 Wi-Fi
WifiInfo	Wifi 信息
日历	
名称	功能
wx.addPhoneRepeatCalendar	向系统日历添加重复事件
wx.addPhoneCalendar	向系统日历添加事件
联系人	
名称	功能
wx.chooseContact	拉起手机通讯录，选择联系人
wx.addPhoneContact	添加手机通讯录联系人
无障碍	
名称	功能
wx.checkIsOpenAccessibility	检测是否开启视觉无障碍功能
电量	
名称	功能
wx.onBatteryInfoChange	监听电池信息变化事件，目前只支持监听省电模式的切换
wx.offBatteryInfoChange	移除电池信息变化事件的监听函数
wx.getBatteryInfoSync	wx.getBatteryInfo 的同步版本
wx.getBatteryInfo	获取设备电池信息
剪贴板	
名称	功能
wx.setClipboardData	设置系统剪贴板的内容
wx.getClipboardData	获取系统剪贴板的内容
NFC 主机卡模拟	
名称	功能
wx.stopHCE	关闭 NFC 模块
wx.startHCE	初始化 NFC 模块
wx.sendHCEMessage	发送 NFC 消息
wx.onHCEMessage	监听接收 NFC 设备消息事件
wx.offHCEMessage	移除接收 NFC 设备消息事件的监听函数
wx.getHCEState	判断当前设备是否支持 HCE 能力
网络	
名称	功能
wx.onNetworkWeakChange	监听弱网状态变化事件
wx.onNetworkStatusChange	监听网络状态变化事件
wx.offNetworkWeakChange	移除弱网状态变化事件的监听函数
wx.offNetworkStatusChange	移除网络状态变化事件的监听函数
wx.getNetworkType	获取网络类型
wx.getLocalIPAddress	获取局域网IP地址
加密	
名称	功能
wx.getRandomValues	获取密码学安全随机数
屏幕	
名称	功能
wx.setVisualEffectOnCapture	设置截屏/录屏时屏幕表现
wx.setScreenBrightness	设置屏幕亮度
wx.setKeepScreenOn	设置是否保持常亮状态
wx.onUserCaptureScreen	监听用户主动截屏事件
wx.onScreenRecordingStateChanged	监听用户录屏事件
wx.onGeneratePoster	监听用户截屏之后需要开发者生成自定义海报事件，在点击转发截图按钮时触发
wx.offUserCaptureScreen	用户主动截屏事件
wx.offScreenRecordingStateChanged	移除用户录屏事件的监听函数
wx.offGeneratePoster	用户截屏之后需要开发者生成自定义海报事件
wx.getScreenRecordingState	查询用户是否在录屏
wx.getScreenBrightness	获取屏幕亮度
键盘	
名称	功能
wx.onKeyUp	监听小程序全局键盘按键弹起事件
wx.onKeyDown	监听小程序全局键盘按键按下事件
wx.onKeyboardHeightChange	监听键盘高度变化事件
wx.offKeyUp	移除小程序全局键盘按键弹起事件的监听函数
wx.offKeyDown	移除小程序全局键盘按键按下事件的监听函数
wx.offKeyboardHeightChange	移除键盘高度变化事件的监听函数
wx.hideKeyboard	在input、textarea等focus拉起键盘之后，手动调用此接口收起键盘
wx.getSelectedTextRange	在input、textarea等focus之后，获取输入框的光标位置
电话	
名称	功能
wx.makePhoneCall	拨打电话
加速计	
名称	功能
wx.stopAccelerometer	停止监听加速度数据
wx.startAccelerometer	开始监听加速度数据
wx.onAccelerometerChange	监听加速度数据事件
wx.offAccelerometerChange	移除加速度数据事件的监听函数
罗盘	
名称	功能
wx.stopCompass	停止监听罗盘数据
wx.startCompass	开始监听罗盘数据
wx.onCompassChange	监听罗盘数据变化事件
wx.offCompassChange	移除罗盘数据变化事件的监听函数
设备方向	
名称	功能
wx.stopDeviceMotionListening	停止监听设备方向的变化
wx.startDeviceMotionListening	开始监听设备方向的变化
wx.onDeviceMotionChange	监听设备方向变化事件
wx.offDeviceMotionChange	移除设备方向变化事件的监听函数
陀螺仪	
名称	功能
wx.stopGyroscope	停止监听陀螺仪数据
wx.startGyroscope	开始监听陀螺仪数据
wx.onGyroscopeChange	监听陀螺仪数据变化事件
wx.offGyroscopeChange	移除陀螺仪数据变化事件的监听函数
内存	
名称	功能
wx.onMemoryWarning	监听内存不足告警事件
wx.offMemoryWarning	移除内存不足告警事件的监听函数
扫码	
名称	功能
wx.scanCode	调起客户端扫码界面进行扫码
短信	
名称	功能
wx.sendSms	拉起手机发送短信界面
振动	
名称	功能
wx.vibrateShort	使手机发生较短时间的振动（15 ms）
wx.vibrateLong	使手机发生较长时间的振动（400 ms)
AI
名称	功能
AI 推理	
名称	功能
wx.getInferenceEnvInfo	获取通用AI推理引擎版本
wx.createInferenceSession	创建 AI 推理 Session
InferenceSession	推理 Session 实例，通过wx.createInferenceSession 接口获取该实例
名称	功能
InferenceSession.destroy	销毁 InferenceSession 实例
InferenceSession.offError	取消监听模型加载失败事件
InferenceSession.offLoad	取消监听模型加载完成事件
InferenceSession.onError	监听模型加载失败事件
InferenceSession.onLoad	监听模型加载完成事件
InferenceSession.run	运行推断
Tensor	Tensor
Tensors	Tensors 是 key-value 形式的对象，对象的 key 会作为 input/output name，对象的 value 则是 Tensor
视觉算法	
名称	功能
wx.isVKSupport	判断支持版本
wx.createVKSession	创建 vision kit 会话对象
VKBodyAnchor	人体 anchor
VKCamera	相机对象
名称	功能
VKCamera.getProjectionMatrix	获取投影矩阵
VKDepthAnchor	depth anchor
VKFaceAnchor	人脸 anchor
VKFrame	vision kit 会话对象
名称	功能
VKFrame.getCameraBuffer	获取当前帧 rgba buffer
VKFrame.getCameraJpgBuffer	获取当前帧的 jpg 信息Buffer
VKFrame.getCameraTexture	获取当前帧纹理，目前只支持 YUV 纹理
VKFrame.getDepthBuffer	获取每帧的深度图信息Buffer
VKFrame.getDisplayTransform	获取纹理调整矩阵
VKFrame.getLegSegmentBuffer	获取每帧的腿部分割信息Buffer，安卓微信 8.0.43，iOS微信 8.0.43 开始支持
VKHandAnchor	手势 anchor
VKMarkerAnchor	marker anchor
VKOCRAnchor	OCR anchor
VKOSDAnchor	OSD anchor
VKPlaneAnchor	平面 anchor，只有 v2 版本支持
VKSession	vision kit 会话对象
名称	功能
VKSession.addMarker	添加一个 marker，要求调 wx.createVKSession 时传入的 track.marker 为 true
VKSession.addOSDMarker	添加一个 OSD marker（one-shot detection marker），要求调 wx.createVKSession 时传入的 track.OSD 为 true
VKSession.cancelAnimationFrame	取消由 requestAnimationFrame 添加到计划中的动画帧请求
VKSession.destroy	销毁会话
VKSession.detectBody	静态图像人体关键点检测
VKSession.detectDepth	深度识别
VKSession.detectFace	静态图像人脸关键点检测
VKSession.detectHand	静态图像手势关键点检测
VKSession.getAllMarker	获取所有 marker，要求调 wx.createVKSession 时传入的 track.marker 为 true
VKSession.getAllOSDMarker	获取所有 OSD marker，要求调 wx.createVKSession 时传入的 track.OSD 为 true
VKSession.getVKFrame	获取帧对象，每调用一次都会触发一次帧分析过程
VKSession.hitTest	触摸检测，v1 版本只支持单平面（即 hitTest 生成一次平面后，后续 hitTest 均不会再生成平面，而是以之前生成的平面为基础进行检测）
VKSession.off	取消监听会话事件
VKSession.on	监听会话事件
VKSession.removeMarker	删除一个 marker，要求调 wx.createVKSession 时传入的 track.marker 为 true
VKSession.removeOSDMarker	删除一个 OSD marker，要求调 wx.createVKSession 时传入的 track.OSD 为 true
VKSession.requestAnimationFrame	在下次进行重绘时执行
VKSession.runOCR	静态图像OCR检测
VKSession.setDepthOccRange	更新 深度遮挡 Occ范围，要求调 wx.createVKSession 时传入 {track: {depth: {mode: 2} } }
VKSession.start	开启会话
VKSession.stop	停止会话
VKSession.update3DMode	更新三维识别相关配置，要求调 wx.createVKSession 时使用 face / hand / body
VKSession.updateMaskMode	设置裁剪相关配置，要求调 wx.createVKSession 时使用 shoe
VKSession.updateOSDThreshold	更新 OSD 识别精确度，要求调 wx.createVKSession 时传入的 track.OSD 为 true
人脸检测	
名称	功能
wx.stopFaceDetect	停止人脸检测
wx.initFaceDetect	初始化人脸检测
wx.faceDetect	人脸检测，使用前需要通过 wx.initFaceDetect 进行一次初始化，推荐使用相机接口返回的帧数据
Worker
名称	功能
wx.createWorker	创建一个 Worker 线程
Worker	Worker 实例，主线程中可通过 wx.createWorker 接口获取，worker 线程中可通过全局变量 worker 获取
名称	功能
Worker.getCameraFrameData	获取摄像头当前帧图像，返回ArrayBuffer数据
Worker.onError	监听 Worker 线程错误事件
Worker.onMessage	监听主线程/Worker 线程向当前线程发送的消息的事件
Worker.onProcessKilled	监听 worker线程被系统回收事件（开启 useExperimentalWorker 后，当iOS系统资源紧张时，ExperimentalWorker 线程存在被系统回收的可能，开发者可监听此事件并重新创建一个worker）
Worker.postMessage	向主线程/Worker 线程发送的消息
Worker.terminate	结束当前 Worker 线程
Worker.testOnProcessKilled	用于模拟 iOS ExperimentalWorker 线程被系统回收事件，以便于调试
WXML
名称	功能
wx.createSelectorQuery	返回一个 SelectorQuery 对象实例
wx.createIntersectionObserver	创建并返回一个 IntersectionObserver 对象实例
IntersectionObserver	IntersectionObserver 对象，用于推断某些节点是否可以被用户看见、有多大比例可以被用户看见
名称	功能
IntersectionObserver.disconnect	停止监听
IntersectionObserver.observe	指定目标节点并开始监听相交状态变化情况
IntersectionObserver.relativeTo	使用选择器指定一个节点，作为参照区域之一
IntersectionObserver.relativeToViewport	指定页面显示区域作为参照区域之一
MediaQueryObserver	MediaQueryObserver 对象，用于监听页面 media query 状态的变化，如界面的长宽是不是在某个指定的范围内
名称	功能
MediaQueryObserver.disconnect	停止监听
MediaQueryObserver.observe	开始监听页面 media query 变化情况
NodesRef	用于获取 WXML 节点信息的对象
名称	功能
NodesRef.boundingClientRect	添加节点的布局位置的查询请求
NodesRef.context	添加节点的 Context 对象查询请求
NodesRef.fields	获取节点的相关信息
NodesRef.node	获取 Node 节点实例
NodesRef.ref	获取 Node 节点的 Ref 对象，可用于 worklet 函数内操作节点
NodesRef.scrollOffset	添加节点的滚动位置查询请求
SelectorQuery	查询节点信息的对象
名称	功能
SelectorQuery.exec	执行所有的请求
SelectorQuery.in	将选择器的选取范围更改为自定义组件 component 内
SelectorQuery.select	在当前页面下选择第一个匹配选择器 selector 的节点
SelectorQuery.selectAll	在当前页面下选择匹配选择器 selector 的所有节点
SelectorQuery.selectViewport	选择显示区域
第三方平台
名称	功能
wx.getExtConfigSync	wx.getExtConfig 的同步版本
wx.getExtConfig	获取第三方平台自定义的数据字段
广告
名称	功能
wx.getShowSplashAdStatus	获取封面广告组件展示状态
wx.createRewardedVideoAd	创建激励视频广告组件
wx.createInterstitialAd	创建插屏广告组件
InterstitialAd	插屏广告组件
名称	功能
InterstitialAd.destroy	销毁插屏广告实例
InterstitialAd.load	加载插屏广告
InterstitialAd.offClose	移除插屏广告关闭事件的监听函数
InterstitialAd.offError	移除插屏错误事件的监听函数
InterstitialAd.offLoad	移除插屏广告加载事件的监听函数
InterstitialAd.onClose	监听插屏广告关闭事件
InterstitialAd.onError	监听插屏错误事件
InterstitialAd.onLoad	监听插屏广告加载事件
InterstitialAd.show	显示插屏广告
RewardedVideoAd	激励视频广告组件
名称	功能
RewardedVideoAd.destroy	销毁激励视频广告实例
RewardedVideoAd.load	加载激励视频广告
RewardedVideoAd.offClose	移除用户点击 关闭广告 按钮的事件的监听函数
RewardedVideoAd.offError	移除激励视频错误事件的监听函数
RewardedVideoAd.offLoad	移除激励视频广告加载事件的监听函数
RewardedVideoAd.onClose	监听用户点击 关闭广告 按钮的事件
RewardedVideoAd.onError	监听激励视频错误事件
RewardedVideoAd.onLoad	监听激励视频广告加载事件
RewardedVideoAd.show	显示激励视频广告
Skyline
名称	功能
DraggableSheetContext	DraggableSheet 实例，可通过 wx.createSelectorQuery 的 NodesRef.node 方法获取
名称	功能
DraggableSheetContext.scrollTo	滚动到指定位置
OpenContainer	OpenContainer 实例，可通过 SelectorQuery 获取
Snapshot	Snapshot 实例，可通过 SelectorQuery 获取
名称	功能
Snapshot.takeSnapshot	对 snapshot 组件子树进行截图



