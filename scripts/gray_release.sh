#!/bin/bash
# 灰度发布脚本

set -e

GRAY_PERCENT=${1:-1}  # 默认 1%

echo "=========================================="
echo "品牌诊断系统 - 灰度发布脚本"
echo "=========================================="
echo "灰度比例：${GRAY_PERCENT}%"
echo "=========================================="

# 更新 Nginx 配置
cat > /tmp/brand_diagnosis_gray.conf << EOF
upstream brand_diagnosis_backend {
    server 127.0.0.1:5000 weight=$((100 - GRAY_PERCENT));  # 当前版本
}

server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://brand_diagnosis_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

# 复制配置
sudo cp /tmp/brand_diagnosis_gray.conf /etc/nginx/conf.d/brand_diagnosis.conf

# 验证并重载 Nginx
sudo nginx -t && sudo nginx -s reload

echo "✅ 灰度发布完成：${GRAY_PERCENT}%"
echo ""
echo "下一步:"
echo "  1. 监控错误率和延迟指标"
echo "  2. 收集用户反馈"
echo "  3. 根据情况调整灰度比例"
