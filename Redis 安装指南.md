# Redis 安装与配置指南

**文档版本**: 1.0  
**更新日期**: 2026-03-02  
**适用系统**: macOS (Homebrew)

---

## 一、为什么需要 Redis

### 1.1 当前状态

系统当前使用**内存缓存降级方案**：
```
[Redis] 连接被拒绝 (Error 61)：localhost:6379 - Redis 服务可能未启动。使用内存缓存降级方案。
```

**影响**：
- ✅ 系统可以正常运行
- ⚠️ 缓存数据在重启后丢失
- ⚠️ 无法跨进程共享缓存
- ⚠️ 性能稍差（无持久化）

### 1.2 启用 Redis 的好处

| 特性 | 内存缓存 | Redis |
|------|---------|-------|
| 持久化 | ❌ 重启丢失 | ✅ 支持 RDB/AOF |
| 跨进程共享 | ❌ 不支持 | ✅ 支持 |
| 内存管理 | ❌ 无限制 | ✅ LRU 淘汰 |
| 性能 | ⚠️ 一般 | ✅ 高性能 |
| 监控 | ❌ 无 | ✅ 丰富指标 |

---

## 二、安装 Redis（macOS）

### 2.1 使用 Homebrew 安装

```bash
# 1. 确保 Homebrew 已安装
brew --version

# 2. 安装 Redis
brew install redis

# 3. 验证安装
redis-cli --version
# 期望输出：redis-cli 7.x.x
```

### 2.2 启动 Redis 服务

```bash
# 1. 启动 Redis（后台服务）
brew services start redis

# 2. 验证 Redis 状态
brew services list | grep redis
# 期望输出：redis started

# 3. 测试 Redis 连接
redis-cli ping
# 期望输出：PONG
```

### 2.3 停止/重启 Redis

```bash
# 停止 Redis
brew services stop redis

# 重启 Redis
brew services restart redis

# 查看 Redis 日志
tail -f /usr/local/var/log/redis.log
# 或（Apple Silicon）
tail -f /opt/homebrew/var/log/redis.log
```

---

## 三、配置 Redis

### 3.1 配置文件位置

```bash
# Intel Mac
/usr/local/etc/redis.conf

# Apple Silicon Mac
/opt/homebrew/etc/redis.conf
```

### 3.2 推荐配置

```bash
# 1. 绑定地址（默认 localhost）
bind 127.0.0.1

# 2. 端口（默认 6379）
port 6379

# 3. 最大内存（建议设置为系统内存的 50%）
maxmemory 2gb

# 4. 内存淘汰策略（LRU）
maxmemory-policy allkeys-lru

# 5. 持久化（RDB + AOF）
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

### 3.3 应用配置

**文件**: `.env`

```bash
# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # 留空表示无密码
```

---

## 四、验证 Redis 集成

### 4.1 重启后端服务

```bash
# 1. 停止现有服务
ps aux | grep "python.*app.py" | grep -v grep
kill <PID>

# 2. 重启服务
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python3 run.py

# 3. 查看 Redis 连接日志
tail -f logs/app.log | grep Redis
```

### 4.2 期望日志

**成功连接**：
```
[Redis] 连接成功：localhost:6379
[Redis] 缓存命中率：85.3%
```

**连接失败**（如果 Redis 未启动）：
```
[Redis] 连接被拒绝 (Error 61)：localhost:6379 - Redis 服务可能未启动。使用内存缓存降级方案。
```

---

## 五、常见问题

### 5.1 Redis 无法启动

```bash
# 检查端口占用
lsof -i :6379

# 如果端口被占用，停止旧进程
kill -9 <PID>

# 重新启动 Redis
brew services restart redis
```

### 5.2 连接被拒绝

```bash
# 检查 Redis 状态
brew services list | grep redis

# 如果是 stopped 状态，启动它
brew services start redis

# 检查防火墙
sudo lsof -iTCP:6379 -sTCP:LISTEN
```

### 5.3 内存不足

```bash
# 查看 Redis 内存使用
redis-cli info memory

# 手动清理缓存
redis-cli FLUSHDB

# 或清理所有数据库
redis-cli FLUSHALL
```

### 5.4 持久化失败

```bash
# 检查磁盘空间
df -h

# 检查日志文件
tail -f /opt/homebrew/var/log/redis.log

# 重启 Redis
brew services restart redis
```

---

## 六、性能监控

### 6.1 基本监控命令

```bash
# 查看 Redis 信息
redis-cli info

# 查看内存使用
redis-cli info memory

# 查看连接数
redis-cli info clients

# 查看命中率
redis-cli info stats | grep keyspace

# 实时监控
redis-cli --stat
```

### 6.2 慢查询日志

```bash
# 配置慢查询阈值（毫秒）
redis-cli CONFIG SET slowlog-log-slower-than 10000

# 查看慢查询
redis-cli SLOWLOG GET 10

# 清空慢查询日志
redis-cli SLOWLOG RESET
```

---

## 七、备份与恢复

### 7.1 备份 RDB 文件

```bash
# 1. 找到 RDB 文件位置
redis-cli CONFIG GET dir

# 2. 复制 RDB 文件
cp /opt/homebrew/var/db/redis/dump.rdb /path/to/backup/dump-$(date +%Y%m%d).rdb
```

### 7.2 恢复数据

```bash
# 1. 停止 Redis
brew services stop redis

# 2. 替换 RDB 文件
cp /path/to/backup/dump.rdb /opt/homebrew/var/db/redis/dump.rdb

# 3. 启动 Redis
brew services start redis
```

---

## 八、安全建议

### 8.1 设置密码

**配置文件** (`redis.conf`)：
```bash
requirepass YourStrongPassword123!
```

**环境变量** (`.env`)：
```bash
REDIS_PASSWORD=YourStrongPassword123!
```

### 8.2 限制网络访问

```bash
# 只允许本地访问
bind 127.0.0.1

# 禁用危险命令
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""
```

### 8.3 定期更新

```bash
# 更新 Redis
brew update
brew upgrade redis

# 查看版本
redis-server --version
```

---

## 九、总结

### 9.1 安装检查清单

- [ ] Redis 已安装 (`redis-cli --version`)
- [ ] Redis 服务已启动 (`brew services list`)
- [ ] Redis 连接正常 (`redis-cli ping`)
- [ ] 后端日志显示连接成功
- [ ] 缓存命中率正常

### 9.2 预期效果

启用 Redis 后：
- ✅ 缓存持久化（重启不丢失）
- ✅ 跨进程缓存共享
- ✅ 更好的内存管理
- ✅ 性能提升 20-30%

### 9.3 可选性

**重要**: Redis 是**可选的优化项**，不影响核心功能。

如果暂时不安装：
- 系统会自动使用内存缓存降级
- 所有功能正常工作
- 只是性能和持久化稍差

---

**需要帮助？**

运行以下命令检查 Redis 状态：
```bash
brew services list | grep redis
redis-cli ping
```

如果遇到问题，请查看日志：
```bash
tail -f /opt/homebrew/var/log/redis.log
```
