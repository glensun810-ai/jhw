#!/usr/bin/env python3
"""
系统诊断和自动修复脚本
针对macOS ARM64环境的特定问题进行诊断和修复
"""

import os
import sys
import subprocess
import json
from pathlib import Path

class SystemDiagnostics:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backend_path = self.project_root / 'backend_python'
        self.results = {}
        
    def check_python_environment(self):
        """检查Python环境"""
        print("🔍 检查Python环境...")
        
        # 检查Python版本
        python_version = sys.version
        print(f"✅ Python版本: {python_version}")
        
        # 检查架构
        import platform
        architecture = platform.machine()
        print(f"✅ 系统架构: {architecture}")
        
        # 检查是否为ARM64
        is_arm64 = architecture == 'arm64'
        print(f"{'✅' if is_arm64 else '⚠️'} ARM64架构: {is_arm64}")
        
        self.results['python'] = {
            'version': python_version,
            'architecture': architecture,
            'is_arm64': is_arm64
        }
        
    def check_dependencies(self):
        """检查依赖包"""
        print("\n🔍 检查依赖包...")
        
        required_packages = [
            'flask', 'werkzeug', 'flask_cors', 'python_dotenv',
            'google.generativeai', 'jwt', 'requests'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                if package == 'jwt':
                    import jwt
                    print(f"✅ PyJWT: {jwt.__version__}")
                else:
                    __import__(package)
                    print(f"✅ {package}")
            except ImportError:
                print(f"❌ {package} 未安装")
                missing_packages.append(package)
        
        self.results['dependencies'] = {
            'missing': missing_packages,
            'all_required_present': len(missing_packages) == 0
        }
        
        return len(missing_packages) == 0
    
    def check_environment_variables(self):
        """检查环境变量"""
        print("\n🔍 检查环境变量...")
        
        env_file = self.project_root / '.env'
        if not env_file.exists():
            print("❌ .env 文件不存在")
            self.results['env_file'] = {'exists': False}
            return False
        
        # 加载环境变量
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                env_content = f.read()
            
            # 检查关键配置
            required_vars = ['DEEPSEEK_API_KEY', 'SECRET_KEY', 'WECHAT_APP_ID']
            missing_vars = []
            
            for var in required_vars:
                if var not in env_content:
                    missing_vars.append(var)
                else:
                    print(f"✅ {var} 配置存在")
            
            self.results['env_vars'] = {
                'file_exists': True,
                'missing_vars': missing_vars,
                'all_vars_present': len(missing_vars) == 0
            }
            
            return len(missing_vars) == 0
            
        except Exception as e:
            print(f"❌ 环境变量文件读取失败: {e}")
            self.results['env_vars'] = {'error': str(e)}
            return False
    
    def check_backend_service(self):
        """检查后端服务状态"""
        print("\n🔍 检查后端服务...")
        
        # 检查后端目录
        if not self.backend_path.exists():
            print("❌ 后端目录不存在")
            self.results['backend'] = {'exists': False}
            return False
        
        # 检查关键文件
        required_files = ['run.py', 'config.py', 'requirements.txt']
        missing_files = []
        
        for file_name in required_files:
            file_path = self.backend_path / file_name
            if file_path.exists():
                print(f"✅ {file_name}")
            else:
                print(f"❌ {file_name} 不存在")
                missing_files.append(file_name)
        
        self.results['backend'] = {
            'path': str(self.backend_path),
            'missing_files': missing_files,
            'all_files_present': len(missing_files) == 0
        }
        
        return len(missing_files) == 0
    
    def auto_fix_issues(self):
        """自动修复发现的问题"""
        print("\n🔧 自动修复问题...")
        
        fixes_applied = []
        
        # 修复缺失的依赖包
        if not self.results.get('dependencies', {}).get('all_required_present', True):
            print("📦 安装缺失的依赖包...")
            try:
                requirements_file = self.backend_path / 'requirements.txt'
                if requirements_file.exists():
                    subprocess.run([
                        sys.executable, '-m', 'pip', 'install', '-r', 
                        str(requirements_file)
                    ], check=True)
                    print("✅ 依赖包安装完成")
                    fixes_applied.append("依赖包安装")
                else:
                    print("❌ requirements.txt 文件不存在，无法自动安装依赖")
            except Exception as e:
                print(f"❌ 依赖包安装失败: {e}")
        
        # 修复环境变量文件
        if not self.results.get('env_vars', {}).get('all_vars_present', True):
            print("📝 修复环境变量配置...")
            env_file = self.project_root / '.env'
            if env_file.exists():
                try:
                    # 备份原文件
                    backup_file = env_file.with_suffix('.bak')
                    env_file.rename(backup_file)
                    print(f"✅ 原配置文件已备份为: {backup_file.name}")
                    
                    # 创建新的环境变量文件
                    self.create_env_file(env_file)
                    print("✅ 新的环境变量文件已创建")
                    fixes_applied.append("环境变量文件修复")
                except Exception as e:
                    print(f"❌ 环境变量文件修复失败: {e}")
        
        self.results['fixes_applied'] = fixes_applied
        return fixes_applied
    
    def create_env_file(self, env_file_path):
        """创建环境变量文件"""
        env_content = """# 环境变量配置文件
# 请根据实际情况修改以下配置

# AI Platform API Keys
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
JUDGE_LLM_API_KEY=sk-your-judge-api-key-here
QWEN_API_KEY=sk-your-qwen-api-key-here
DOUBAO_API_KEY=your-doubao-api-key-here
CHATGPT_API_KEY=sk-your-chatgpt-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here
ZHIPU_API_KEY=your-zhipu-api-key-here

# 微信小程序配置
WECHAT_APP_ID=your-wechat-app-id
WECHAT_APP_SECRET=your-wechat-app-secret
WECHAT_TOKEN=your-wechat-token
EncodingAESKey=your-encoding-aes-key

# Flask配置
SECRET_KEY=your-secret-key-here
"""
        
        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
    
    def generate_report(self):
        """生成诊断报告"""
        print("\n" + "="*60)
        print("📊 诊断报告")
        print("="*60)
        
        # 保存详细报告
        report_file = self.project_root / 'system_diagnostics_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 详细报告已保存到: {report_file}")
        
        # 打印摘要
        print("\n📋 摘要:")
        print(f"  Python环境: {'正常' if self.results.get('python') else '异常'}")
        print(f"  依赖包: {'正常' if self.results.get('dependencies', {}).get('all_required_present') else '存在缺失'}")
        print(f"  环境变量: {'正常' if self.results.get('env_vars', {}).get('all_vars_present') else '配置不完整'}")
        print(f"  后端服务: {'正常' if self.results.get('backend', {}).get('all_files_present') else '文件缺失'}")
        
        fixes = self.results.get('fixes_applied', [])
        if fixes:
            print(f"\n🔧 已应用的修复: {', '.join(fixes)}")
        else:
            print("\n✅ 未发现问题需要修复")
    
    def run_diagnostics(self):
        """运行完整的系统诊断"""
        print("🚀 开始系统诊断...")
        print("="*60)
        
        # 执行各项检查
        self.check_python_environment()
        deps_ok = self.check_dependencies()
        env_ok = self.check_environment_variables()
        backend_ok = self.check_backend_service()
        
        # 自动修复问题
        if not (deps_ok and env_ok and backend_ok):
            self.auto_fix_issues()
        
        # 生成报告
        self.generate_report()
        
        print("\n" + "="*60)
        print("🏁 诊断完成")
        print("="*60)

def main():
    diagnostics = SystemDiagnostics()
    diagnostics.run_diagnostics()

if __name__ == '__main__':
    main()