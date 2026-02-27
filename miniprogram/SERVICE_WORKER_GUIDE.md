# Service Worker 离线缓存使用文档

## 概述

本项目已集成 Service Worker 离线缓存功能，为小程序提供以下能力：

- **离线访问**：在网络不可用时仍能访问缓存的页面和数据
- **资源预加载**：首次访问后缓存核心资源，提升后续加载速度
- **智能缓存策略**：根据资源类型自动选择合适的缓存策略
- **缓存版本管理**：自动清理旧版本缓存，确保资源更新

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                     小程序应用                           │
├─────────────────────────────────────────────────────────┤
│  app.js (Service Worker 注册和管理)                      │
│    ├── registerServiceWorker()                          │
│    ├── sendServiceWorkerMessage()                       │
│    ├── clearCache()                                     │
│    └── precacheUrls()                                   │
├─────────────────────────────────────────────────────────┤
│  config/cacheConfig.js (缓存配置)                        │
│    ├── 缓存版本管理                                      │
│    ├── 缓存策略配置                                      │
│    └── API 白名单/黑名单                                  │
├─────────────────────────────────────────────────────────┤
│  utils/cacheManager.js (缓存管理工具)                     │
│    ├── set/get/remove                                   │
│    ├── setBatch/getBatch/removeBatch                    │
│    └── info/refresh/has                                 │
└─────────────────────────────────────────────────────────┤
                      ↓ Service Worker
┌─────────────────────────────────────────────────────────┐
│  service-worker.js (Service Worker 核心)                  │
│    ├── 静态资源缓存 (Cache-First)                        │
│    ├── API 响应缓存 (Stale-While-Revalidate)             │
│    └── 缓存清理和更新                                    │
└─────────────────────────────────────────────────────────┘
```

## 缓存策略

### 1. 静态资源（Cache-First）

对于小程序页面、组件、样式等静态资源，采用**缓存优先**策略：

```
请求 → 检查缓存 → 有缓存？→ 返回缓存
                    ↓ 无缓存
                网络请求 → 缓存 → 返回
```

**适用资源：**
- `/pages/*` - 所有页面
- `/components/*` - 所有组件
- `/services/*` - 服务模块
- `/utils/*` - 工具模块
- `/config/*` - 配置文件

### 2. API 响应（Stale-While-Revalidate）

对于 API GET 请求，采用**过期数据 + 后台更新**策略：

```
请求 → 检查缓存 → 有缓存？→ 立即返回缓存
                    ↓          ↓ 后台更新缓存
                网络请求 ←──────┘
                    ↓
                更新缓存
```

**缓存规则：**
- ✅ 白名单 API 会被缓存（`/api/home`, `/api/history`, `/api/user` 等）
- ❌ 黑名单 API 不会被缓存（`/api/auth`, `/api/login`, `/api/diagnosis/*` 等）
- ❌ 非 GET 请求不会被缓存（POST/PUT/DELETE）

### 3. 缓存限制

| 缓存类型 | 最大数量 | 过期时间 |
|---------|---------|---------|
| API 缓存 | 50 条 | 5 分钟 |
| 用户数据 | 20 条 | 30 分钟 |
| 临时缓存 | 10 条 | 1 分钟 |
| 静态资源 | 不限 | 24 小时 |

## 使用指南

### 1. 自动注册（推荐）

Service Worker 会在小程序启动时自动注册，无需额外操作：

```javascript
// app.js onLaunch 中已自动调用
this.registerServiceWorker();
```

### 2. 手动缓存管理

#### 设置缓存

```javascript
const cacheManager = require('./utils/cacheManager');

// 基本用法
await cacheManager.set('user_profile', { name: '张三', age: 25 });

// 指定缓存类型和过期时间
await cacheManager.set('api_data', data, {
  type: 'api',           // 缓存类型：static/api/user/temp
  expiration: 10000      // 自定义过期时间（毫秒）
});
```

#### 获取缓存

```javascript
// 获取缓存（自动检查过期）
const data = await cacheManager.get('user_profile');

// 获取缓存（不检查过期）
const rawData = await cacheManager.get('user_profile', {
  checkExpiration: false
});
```

#### 删除缓存

```javascript
// 删除单个缓存
await cacheManager.remove('user_profile');

// 删除多个缓存
await cacheManager.removeBatch(['key1', 'key2', 'key3']);

// 清空所有缓存
await cacheManager.clear();
```

#### 批量操作

```javascript
// 批量设置
const items = [
  { key: 'key1', data: data1 },
  { key: 'key2', data: data2 }
];
const result = await cacheManager.setBatch(items);
console.log(`成功：${result.success}, 失败：${result.failed}`);

// 批量获取
const data = await cacheManager.getBatch(['key1', 'key2', 'key3']);
```

#### 缓存信息

```javascript
// 获取缓存元信息
const info = await cacheManager.info('user_profile');
console.log('缓存年龄:', info.age);          // 毫秒
console.log('剩余时间:', info.remaining);    // 毫秒
console.log('是否过期:', info.isExpired);
```

### 3. Service Worker 消息通信

#### 发送消息到 Service Worker

```javascript
// 在页面中通过 app 实例发送消息
const app = getApp();

app.sendServiceWorkerMessage({
  type: 'GET_CACHE_STATUS'
}, (status) => {
  console.log('缓存状态:', status);
});
```

#### 清除 Service Worker 缓存

```javascript
const app = getApp();

// 清除指定缓存
app.clearCache('wechat-app-api-v1.0.0', (result) => {
  console.log('清除完成:', result);
});

// 清除所有缓存
app.clearCache(null, (result) => {
  console.log('清除完成:', result);
});
```

#### 预缓存 URL

```javascript
const app = getApp();

// 预缓存指定页面
app.precacheUrls([
  '/pages/report/dashboard/index',
  '/pages/report/history/index'
], (result) => {
  console.log('预缓存完成:', result);
});
```

## 配置说明

### 修改缓存配置

编辑 `miniprogram/config/cacheConfig.js`：

```javascript
// 更新缓存版本（强制刷新所有缓存）
const CACHE_CONFIG = {
  version: 'v1.0.1',  // 修改此版本号
  // ...
};

// 添加 API 缓存白名单
const CACHE_CONFIG = {
  apiWhitelist: [
    '/api/home',
    '/api/history',
    '/api/new-endpoint'  // 添加新的 API
  ]
};

// 修改缓存过期时间
const CACHE_CONFIG = {
  expiration: {
    api: 10 * 60 * 1000,  // API 缓存改为 10 分钟
    user: 60 * 60 * 1000  // 用户数据改为 1 小时
  }
};
```

## 调试技巧

### 1. 查看缓存状态

```javascript
// 在小程序开发者工具控制台中运行
const app = getApp();
app.getCacheStatus();
```

### 2. 运行测试

```javascript
// 引入测试模块
const { manualTests } = require('./tests/serviceWorker.test');

// 运行测试
await manualTests.testBasicCache();
await manualTests.testCacheExpiration();
await manualTests.testBatchOperations();
await manualTests.testCacheStrategy();
```

### 3. 清除缓存调试

```javascript
// 方法 1：清除所有缓存
const app = getApp();
app.clearCache();

// 方法 2：清除 Service Worker
// 在开发者工具中：工具 → 清除缓存 → 清除所有数据

// 方法 3：更新缓存版本
// 修改 config/cacheConfig.js 中的 version
```

## 最佳实践

### 1. 缓存关键数据

```javascript
// 在数据加载成功后缓存
async function loadUserData() {
  // 先尝试缓存
  const cached = await cacheManager.get('user_data');
  if (cached) {
    return cached;
  }
  
  // 从网络加载
  const data = await wx.request({ url: '/api/user' });
  
  // 缓存结果
  await cacheManager.set('user_data', data, { type: 'user' });
  
  return data;
}
```

### 2. 处理离线场景

```javascript
// 检查网络状态
wx.getNetworkType({
  success: (res) => {
    if (res.networkType === 'none') {
      // 离线模式，使用缓存数据
      wx.showToast({
        title: '当前处于离线模式',
        icon: 'none'
      });
    }
  }
});
```

### 3. 缓存更新策略

```javascript
// 重要数据变更时清除相关缓存
async function updateUserProfile(newData) {
  // 更新服务器
  await wx.request({
    url: '/api/user/update',
    method: 'POST',
    data: newData
  });
  
  // 清除用户数据缓存
  await cacheManager.remove('user_data');
  await cacheManager.remove('user_profile');
  
  // 重新加载最新数据
  await loadUserData();
}
```

## 常见问题

### Q: 缓存什么时候会被清除？

A: 缓存会在以下情况被清除：
1. 缓存版本更新时（修改 `config/cacheConfig.js` 中的 `version`）
2. 缓存过期时（根据配置的过期时间）
3. 缓存数量超过限制时（FIFO 淘汰）
4. 手动调用清除方法时

### Q: 如何确保用户看到最新数据？

A: 有以下几种方式：
1. 更新缓存版本号，强制刷新所有缓存
2. 在数据修改后清除相关缓存
3. 使用较短的缓存过期时间
4. 关键操作（如提交订单）不使用缓存

### Q: Service Worker 注册失败怎么办？

A: Service Worker 注册失败不会影响应用正常使用，只是没有离线缓存功能。可能原因：
1. 基础库版本过低（需要 2.30.0+）
2. 开发者工具环境问题
3. 真机调试环境限制

### Q: 如何测试离线功能？

A: 在开发者工具中：
1. 首次访问页面，缓存资源
2. 点击工具栏「工具」→「网络状态」→「离线」
3. 再次访问页面，验证是否能正常显示

## 更新日志

### v1.0.0 (2026-02-28)
- ✅ 初始版本
- ✅ 静态资源缓存
- ✅ API 响应缓存
- ✅ 缓存版本管理
- ✅ 缓存配置模块
- ✅ 缓存管理工具类
- ✅ 测试套件
