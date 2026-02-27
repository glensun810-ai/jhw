"""
数据库初始化脚本

执行方式：
    python scripts/init_database.py
"""

import sys
from pathlib import Path

# 添加项目路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 现在可以直接导入 wechat_backend 模块
from wechat_backend.models import init_task_status_db

def main():
    """初始化数据库"""
    print("开始初始化数据库...")
    init_task_status_db()
    print("✅ 数据库初始化完成！")

if __name__ == '__main__':
    main()
