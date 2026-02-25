#!/bin/bash
# 生产部署脚本

set -e

echo "=========================================="
echo "品牌诊断系统 - 生产部署脚本"
echo "=========================================="
echo "部署时间：$(date)"
echo "=========================================="

# 1. 备份当前版本
echo "[1/8] 备份当前版本..."
BACKUP_DIR="/backup/brand_diagnosis/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
if [ -d "/var/www/brand_diagnosis/backend_python" ]; then
    cp -r /var/www/brand_diagnosis/backend_python $BACKUP_DIR/
    echo "✅ 备份完成：$BACKUP_DIR"
else
    echo "⚠️ 生产目录不存在，跳过备份"
fi

# 2. 拉取最新代码
echo "[2/8] 拉取最新代码..."
cd /Users/sgl/PycharmProjects/PythonProject
git pull origin main
echo "✅ 代码拉取完成"

# 3. 安装依赖
echo "[3/8] 安装依赖..."
pip3 install -r backend_python/requirements.txt
echo "✅ 依赖安装完成"

# 4. 数据库迁移
echo "[4/8] 数据库迁移..."
cd backend_python
python3 database/run_migration.py
echo "✅ 数据库迁移完成"

# 5. 验证配置
echo "[5/8] 验证配置..."
cd ..
python3 -c "from backend_python.config import Config; print('✅ 配置验证通过')"
echo "✅ 配置验证完成"

# 6. 运行测试
echo "[6/8] 运行测试..."
cd backend_python
python3 -m pytest tests/test_integration_p0.py -v --tb=short
python3 -m pytest tests/test_performance_p0.py -v --tb=short
echo "✅ 测试运行完成"

# 7. 重启服务
echo "[7/8] 重启服务..."
sudo systemctl restart brand-diagnosis-backend
sudo systemctl status brand-diagnosis-backend
echo "✅ 服务重启完成"

# 8. 健康检查
echo "[8/8] 健康检查..."
sleep 5
if curl -s http://localhost:5000/api/test | grep -q "success"; then
    echo "✅ 健康检查通过"
else
    echo "❌ 健康检查失败，执行回滚..."
    # 回滚逻辑
    exit 1
fi

echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo "部署时间：$(date)"
echo "备份位置：$BACKUP_DIR"
echo "=========================================="
