#!/bin/bash

# =============================================================================
# startDiagnosis 云函数部署脚本
# =============================================================================
# 功能：自动化部署 startDiagnosis 云函数到微信云开发环境
# 使用：./scripts/deploy-startDiagnosis-cloudfunction.sh
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLOUDFUNCTION_DIR="${PROJECT_ROOT}/miniprogram/cloudfunctions/startDiagnosis"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印横幅
print_banner() {
    echo "========================================"
    echo "  startDiagnosis 云函数部署脚本"
    echo "========================================"
    echo ""
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        log_error "未找到 Node.js，请先安装 Node.js"
        exit 1
    fi
    
    # 检查 npm
    if ! command -v npm &> /dev/null; then
        log_error "未找到 npm，请先安装 npm"
        exit 1
    fi
    
    # 检查微信开发者工具 CLI（可选）
    if ! command -v cloudbase &> /dev/null; then
        log_warning "未找到微信云开发 CLI，将使用开发者工具 GUI 部署"
        log_info "如需使用命令行部署，请安装：npm install -g @cloudbase/cli"
    fi
    
    log_success "依赖检查完成"
}

# 检查云函数目录
check_cloudfunction_dir() {
    log_info "检查云函数目录..."
    
    if [ ! -d "$CLOUDFUNCTION_DIR" ]; then
        log_error "云函数目录不存在：$CLOUDFUNCTION_DIR"
        exit 1
    fi
    
    if [ ! -f "$CLOUDFUNCTION_DIR/index.js" ]; then
        log_error "云函数入口文件不存在：$CLOUDFUNCTION_DIR/index.js"
        exit 1
    fi
    
    if [ ! -f "$CLOUDFUNCTION_DIR/package.json" ]; then
        log_error "package.json 不存在：$CLOUDFUNCTION_DIR/package.json"
        exit 1
    fi
    
    log_success "云函数目录检查完成"
}

# 安装依赖
install_dependencies() {
    log_info "安装云函数依赖..."
    
    cd "$CLOUDFUNCTION_DIR"
    
    # 清理 node_modules（可选）
    if [ -d "node_modules" ] && [ "$1" == "--clean" ]; then
        log_info "清理旧的 node_modules..."
        rm -rf node_modules package-lock.json
    fi
    
    # 安装依赖
    npm install --production
    
    log_success "依赖安装完成"
}

# 验证配置
validate_config() {
    log_info "验证云函数配置..."
    
    # 检查 API 地址配置
    if grep -q "https://your-domain.com" "$CLOUDFUNCTION_DIR/index.js"; then
        log_warning "检测到默认 API 地址 'https://your-domain.com'"
        log_warning "生产环境部署前请修改为实际域名"
        echo ""
        echo "请在以下文件中修改 API_BASE_URL_PROD："
        echo "  $CLOUDFUNCTION_DIR/index.js"
        echo ""
        read -p "是否继续部署？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "部署已取消"
            exit 0
        fi
    fi
    
    log_success "配置验证完成"
}

# 使用微信开发者工具 CLI 部署（如果可用）
deploy_with_cli() {
    if command -v cloudbase &> /dev/null; then
        log_info "使用微信云开发 CLI 部署..."
        
        cd "$CLOUDFUNCTION_DIR"
        
        # 登录（如果未登录）
        if ! cloudbase whoami &> /dev/null; then
            log_info "请先登录微信云开发..."
            cloudbase login
        fi
        
        # 部署云函数
        cloudbase fn deploy startDiagnosis --install-dependency
        
        log_success "云函数部署完成"
        return 0
    fi
    
    return 1
}

# 打印手动部署指南
print_manual_deployment_guide() {
    echo ""
    echo "========================================"
    echo "  手动部署指南"
    echo "========================================"
    echo ""
    echo "由于未检测到微信云开发 CLI，请使用以下方式手动部署："
    echo ""
    echo "1. 打开微信开发者工具"
    echo "2. 导入项目：$PROJECT_ROOT"
    echo "3. 在左侧文件树中找到："
    echo "   miniprogram/cloudfunctions/startDiagnosis"
    echo "4. 右键点击 'startDiagnosis' 文件夹"
    echo "5. 选择「上传并部署：云端安装依赖」"
    echo "6. 等待上传完成（约 10-30 秒）"
    echo ""
    echo "========================================"
    echo ""
}

# 打印测试指南
print_test_guide() {
    echo ""
    echo "========================================"
    echo "  测试指南"
    echo "========================================"
    echo ""
    echo "部署完成后，在微信开发者工具控制台执行以下代码测试："
    echo ""
    echo "wx.cloud.callFunction({"
    echo "  name: 'startDiagnosis',"
    echo "  data: {"
    echo "    brand_list: ['华为', '小米', 'OPPO'],"
    echo "    selectedModels: ["
    echo "      { name: 'doubao', checked: true },"
    echo "      { name: 'deepseek', checked: true }"
    echo "    ],"
    echo "    custom_question: '请分析华为的品牌优势和市场定位？'"
    echo "  }"
    echo "}).then(res => {"
    echo "  console.log('调用结果:', res);"
    echo "  if (res.result && res.result.success) {"
    echo "    console.log('✅ 云函数响应正常');"
    echo "    console.log('执行 ID:', res.result.execution_id);"
    echo "  } else {"
    echo "    console.error('❌ 云函数返回错误:', res.result?.error);"
    echo "  }"
    echo "}).catch(err => {"
    echo "  console.error('❌ 云函数调用失败:', err);"
    echo "});"
    echo ""
    echo "========================================"
    echo ""
}

# 打印日志查看指南
print_log_guide() {
    echo ""
    echo "========================================"
    echo "  日志查看指南"
    echo "========================================"
    echo ""
    echo "1. 登录微信云开发控制台："
    echo "   https://console.cloud.tencent.com/cloud"
    echo ""
    echo "2. 进入「云函数」->「云函数列表」"
    echo ""
    echo "3. 点击 'startDiagnosis' 云函数"
    echo ""
    echo "4. 查看「日志」标签页"
    echo ""
    echo "5. 筛选最近的调用记录，检查是否有错误"
    echo ""
    echo "========================================"
    echo ""
}

# 主函数
main() {
    print_banner
    
    # 解析命令行参数
    CLEAN_INSTALL=false
    SKIP_DEPS=false
    PRODUCTION=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean)
                CLEAN_INSTALL=true
                shift
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            --production)
                PRODUCTION=true
                shift
                ;;
            --help|-h)
                echo "用法：$0 [选项]"
                echo ""
                echo "选项:"
                echo "  --clean       清理 node_modules 后重新安装"
                echo "  --skip-deps   跳过依赖安装"
                echo "  --production  生产环境部署（会进行配置验证）"
                echo "  --help, -h    显示此帮助信息"
                echo ""
                exit 0
                ;;
            *)
                log_error "未知选项：$1"
                exit 1
                ;;
        esac
    done
    
    # 执行部署步骤
    check_dependencies
    check_cloudfunction_dir
    
    if [ "$SKIP_DEPS" != true ]; then
        if [ "$CLEAN_INSTALL" == true ]; then
            install_dependencies --clean
        else
            install_dependencies
        fi
    fi
    
    if [ "$PRODUCTION" == true ]; then
        validate_config
    fi
    
    # 尝试使用 CLI 部署
    if ! deploy_with_cli; then
        print_manual_deployment_guide
    fi
    
    print_test_guide
    print_log_guide
    
    log_success "部署脚本执行完成"
    echo ""
    echo "详细文档请查看："
    echo "  $PROJECT_ROOT/docs/2026-03-02-startDiagnosis 云函数部署指南.md"
    echo ""
}

# 执行主函数
main "$@"
