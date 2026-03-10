#!/bin/bash
# 回滚脚本

set -e

BACKUP_VERSION=${1:-latest}

echo "=========================================="
echo "品牌诊断系统 - 回滚脚本"
echo "=========================================="
echo "回滚版本：$BACKUP_VERSION"
echo "=========================================="

# 1. 停止服务
echo "[1/5] 停止服务..."
sudo systemctl stop brand-diagnosis-backend

# 2. 找到备份
if [ "$BACKUP_VERSION" == "latest" ]; then
    BACKUP_DIR=$(ls -td /backup/brand_diagnosis/* 2>/dev/null | head -1)
    if [ -z "$BACKUP_DIR" ]; then
        echo "❌ 未找到备份"
        exit 1
    fi
else
    BACKUP_DIR="/backup/brand_diagnosis/$BACKUP_VERSION"
    if [ ! -d "$BACKUP_DIR" ]; then
        echo "❌ 备份不存在：$BACKUP_DIR"
        exit 1
    fi
fi

echo "回滚到：$BACKUP_DIR"

# 3. 恢复代码
echo "[2/5] 恢复代码..."
rm -rf /var/www/brand_diagnosis/backend_python
cp -r $BACKUP_DIR/backend_python /var/www/brand_diagnosis/

# 4. 启动服务
echo "[3/5] 启动服务..."
sudo systemctl start brand-diagnosis-backend

# 5. 健康检查
echo "[4/5] 健康检查..."
sleep 5
if curl -s http://localhost:5000/api/test | grep -q "success"; then
    echo "✅ 健康检查通过"
else
    echo "❌ 健康检查失败"
    exit 1
fi

echo "[5/5] 回滚完成..."

echo "=========================================="
echo "✅ 回滚完成！"
echo "=========================================="
echo "回滚版本：$BACKUP_VERSION"
echo "=========================================="
