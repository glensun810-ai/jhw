#!/bin/bash

# 文件系统加密实施脚本
# 支持 macOS (FileVault), Linux (eCryptfs), Windows (BitLocker)

set -e

echo "=========================================="
echo "🔐 文件系统加密实施脚本"
echo "=========================================="
echo ""

# 检测操作系统
OS=$(uname -s)
echo "检测到操作系统：$OS"
echo ""

case $OS in
    Darwin)
        # macOS - FileVault
        echo "🍎 macOS 系统 - FileVault 加密"
        echo ""
        
        # 检查 FileVault 状态
        echo "检查 FileVault 状态..."
        if fdesetup status 2>/dev/null | grep -q "FileVault is On"; then
            echo "✅ FileVault 已启用"
        else
            echo "⚠️  FileVault 未启用"
            echo ""
            echo "启用 FileVault 的步骤:"
            echo "1. 打开 系统偏好设置 > 安全性与隐私 > FileVault"
            echo "2. 点击锁图标并输入管理员密码"
            echo "3. 点击'启用 FileVault'"
            echo "4. 选择解锁方式 (iCloud 账户或本地恢复密钥)"
            echo ""
            echo "或使用命令行启用 (需要管理员权限):"
            echo "  sudo fdesetup enable -user $(whoami)"
            echo ""
            read -p "是否现在启用 FileVault? (y/n): " confirm
            if [ "$confirm" = "y" ]; then
                sudo fdesetup enable -user $(whoami)
                echo "✅ FileVault 启用成功"
            else
                echo "⏭️  跳过 FileVault 启用"
            fi
        fi
        ;;
    
    Linux)
        # Linux - eCryptfs
        echo "🐧 Linux 系统 - eCryptfs 加密"
        echo ""
        
        # 检查 eCryptfs 是否安装
        if command -v mount.ecryptfs &> /dev/null; then
            echo "✅ eCryptfs 已安装"
        else
            echo "⚠️  eCryptfs 未安装"
            echo ""
            read -p "是否安装 eCryptfs? (y/n): " confirm
            if [ "$confirm" = "y" ]; then
                # 根据发行版安装
                if command -v apt-get &> /dev/null; then
                    sudo apt-get update
                    sudo apt-get install -y ecryptfs-utils
                    echo "✅ eCryptfs 安装成功 (Debian/Ubuntu)"
                elif command -v yum &> /dev/null; then
                    sudo yum install -y ecryptfs-utils
                    echo "✅ eCryptfs 安装成功 (RHEL/CentOS)"
                else
                    echo "❌ 无法自动安装，请手动安装 ecryptfs-utils"
                fi
            fi
        fi
        
        echo ""
        echo "加密数据库目录的步骤:"
        echo "1. 创建加密目录:"
        echo "   mkdir -p ~/encrypted_db"
        echo "   mount -t ecryptfs ~/encrypted_db ~/encrypted_db"
        echo ""
        echo "2. 移动数据库文件到加密目录:"
        echo "   mv /path/to/backend_python/database.db ~/encrypted_db/"
        echo ""
        echo "3. 创建符号链接:"
        echo "   ln -s ~/encrypted_db/database.db /path/to/backend_python/database.db"
        echo ""
        ;;
    
    CYGWIN*|MINGW*|MSYS*)
        # Windows - BitLocker
        echo "🪟 Windows 系统 - BitLocker 加密"
        echo ""
        
        # 检查 BitLocker 状态
        echo "检查 BitLocker 状态..."
        if manage-bde -status 2>/dev/null | grep -q "Protection On"; then
            echo "✅ BitLocker 已启用"
        else
            echo "⚠️  BitLocker 未启用"
            echo ""
            echo "启用 BitLocker 的步骤:"
            echo "1. 打开 控制面板 > 系统和安全 > BitLocker 驱动器加密"
            echo "2. 点击'启用 BitLocker'"
            echo "3. 选择解锁方式 (TPM 或 USB 密钥)"
            echo "4. 保存恢复密钥"
            echo ""
            echo "或使用 PowerShell 启用 (需要管理员权限):"
            echo "  Enable-BitLocker -MountPoint 'C:' -EncryptionMethod Aes256 -TpmProtector"
            echo ""
            read -p "是否现在启用 BitLocker? (y/n): " confirm
            if [ "$confirm" = "y" ]; then
                powershell -Command "Enable-BitLocker -MountPoint 'C:' -EncryptionMethod Aes256 -TpmProtector"
                echo "✅ BitLocker 启用成功"
            else
                echo "⏭️  跳过 BitLocker 启用"
            fi
        fi
        ;;
    
    *)
        echo "❌ 不支持的操作系统：$OS"
        echo ""
        echo "手动加密建议:"
        echo "1. 使用 VeraCrypt (跨平台): https://www.veracrypt.fr/"
        echo "2. 创建加密容器"
        echo "3. 将数据库文件放入加密容器"
        ;;
esac

echo ""
echo "=========================================="
echo "✅ 文件系统加密指导完成"
echo "=========================================="
echo ""
echo "下一步:"
echo "1. 根据上述指导启用文件系统加密"
echo "2. 验证加密状态"
echo "3. 继续实施应用层加密"
echo ""
