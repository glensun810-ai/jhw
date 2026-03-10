#!/bin/bash
# 启动冒烟测试脚本

echo "🧪 启动冒烟测试..."

# 1. 后端启动验证
echo "1️⃣ 后端启动验证..."
cd backend_python
python3 -c "from wechat_backend.app import app; print('✅ 后端启动成功')" || exit 1

# 2. 前端编译验证
echo "2️⃣ 前端编译验证..."
node --check pages/index/index.js || exit 1
node --check pages/results/results.js || exit 1
echo "✅ 前端编译通过"

# 3. 数据库验证
echo "3️⃣ 数据库验证..."
python3 -c "
import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
tables = cursor.fetchall()
assert len(tables) >= 10, f'表数量不足：{len(tables)}'
print(f'✅ 数据库表数量：{len(tables)}')
"

# 4. AI 适配器验证
echo "4️⃣ AI 适配器验证..."
python3 -c "
from wechat_backend.ai_adapters.factory import AIAdapterFactory
models = AIAdapterFactory.get_available_models()
assert len(models) >= 7, f'AI 模型数量不足：{len(models)}'
print(f'✅ AI 模型数量：{len(models)}')
"

echo "✅ 所有启动验证通过！"
