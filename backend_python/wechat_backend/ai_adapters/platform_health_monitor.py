"""
AI Platform Health Monitor - AI 平台健康监控器

功能：
1. 启动时检查所有 AI 平台的注册状态
2. 检测平台消失问题并发出告警
3. 提供详细的诊断信息
4. 防止平台消失问题复发

使用方法：
    from wechat_backend.ai_adapters.platform_health_monitor import PlatformHealthMonitor
    PlatformHealthMonitor.run_health_check()
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import os

from wechat_backend.logging_config import api_logger


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class PlatformHealth:
    """平台健康状态数据类"""
    platform: str
    adapter_registered: bool
    provider_registered: bool
    api_key_configured: bool
    status: HealthStatus
    message: str


class PlatformHealthMonitor:
    """
    AI 平台健康监控器
    
    监控所有 AI 平台的状态，确保 adapter 和 provider 都正确注册
    """
    
    # 所有期望的平台列表
    EXPECTED_PLATFORMS = [
        'doubao',      # 豆包
        'deepseek',    # DeepSeek
        'qwen',        # 通义千问
        'chatgpt',     # ChatGPT
        'gemini',      # Gemini
        'zhipu',       # 智谱 AI
        'wenxin',      # 文心一言
    ]
    
    # 国内平台（通常应该配置）
    DOMESTIC_PLATFORMS = ['doubao', 'deepseek', 'qwen']
    
    # 海外平台
    OVERSEAS_PLATFORMS = ['chatgpt', 'gemini', 'zhipu', 'wenxin']
    
    @classmethod
    def run_health_check(cls) -> Dict[str, Any]:
        """
        运行健康检查
        
        Returns:
            Dict: 健康检查结果
        """
        api_logger.info("=== AI Platform Health Check Started ===")
        
        results = {
            'status': HealthStatus.HEALTHY.value,
            'platforms': {},
            'summary': {
                'total': len(cls.EXPECTED_PLATFORMS),
                'healthy': 0,
                'degraded': 0,
                'unhealthy': 0,
                'adapter_only': 0,
                'provider_only': 0,
            },
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # 检查每个平台
        for platform in cls.EXPECTED_PLATFORMS:
            health = cls._check_platform(platform)
            results['platforms'][platform] = {
                'adapter_registered': health.adapter_registered,
                'provider_registered': health.provider_registered,
                'api_key_configured': health.api_key_configured,
                'status': health.status.value,
                'message': health.message
            }
            
            # 更新统计
            if health.status == HealthStatus.HEALTHY:
                results['summary']['healthy'] += 1
            elif health.status == HealthStatus.DEGRADED:
                results['summary']['degraded'] += 1
            else:
                results['summary']['unhealthy'] += 1
            
            if health.adapter_registered and not health.provider_registered:
                results['summary']['adapter_only'] += 1
            elif health.provider_registered and not health.adapter_registered:
                results['summary']['provider_only'] += 1
            
            # 生成警告和错误
            if health.status == HealthStatus.UNHEALTHY and platform in cls.DOMESTIC_PLATFORMS:
                error_msg = f"❌ {platform}: {health.message}"
                results['errors'].append(error_msg)
                # P1-HEALTH-2 修复：启动健康检查失败降级为 WARNING，因为不影响主流程
                api_logger.warning(error_msg)
            elif health.status == HealthStatus.DEGRADED:
                warn_msg = f"⚠️  {platform}: {health.message}"
                results['warnings'].append(warn_msg)
                api_logger.warning(warn_msg)
            elif health.status == HealthStatus.HEALTHY:
                api_logger.info(f"✅ {platform}: OK")
        
        # 生成整体状态
        if results['summary']['unhealthy'] > 0:
            results['status'] = HealthStatus.UNHEALTHY.value
        elif results['summary']['degraded'] > 0:
            results['status'] = HealthStatus.DEGRADED.value
        
        # 生成建议
        results['recommendations'] = cls._generate_recommendations(results)
        
        # 输出总结
        api_logger.info(f"=== Health Check Complete ===")
        api_logger.info(f"Status: {results['status']}")
        api_logger.info(f"Healthy: {results['summary']['healthy']}/{results['summary']['total']}")
        api_logger.info(f"Degraded: {results['summary']['degraded']}/{results['summary']['total']}")
        api_logger.info(f"Unhealthy: {results['summary']['unhealthy']}/{results['summary']['total']}")
        
        if results['recommendations']:
            api_logger.info("Recommendations:")
            for rec in results['recommendations']:
                api_logger.info(f"  - {rec}")
        
        return results
    
    @classmethod
    def _check_platform(cls, platform: str) -> PlatformHealth:
        """检查单个平台的健康状态"""
        adapter_registered = cls._check_adapter_registered(platform)
        provider_registered = cls._check_provider_registered(platform)
        api_key_configured = cls._check_api_key_configured(platform)
        
        # 判断状态
        if adapter_registered and provider_registered and api_key_configured:
            status = HealthStatus.HEALTHY
            message = "All components registered and configured"
        elif adapter_registered and provider_registered:
            status = HealthStatus.DEGRADED
            message = "API key not configured"
        elif adapter_registered and not provider_registered:
            status = HealthStatus.DEGRADED
            message = "Provider not registered (adapter OK)"
        elif not adapter_registered and provider_registered:
            status = HealthStatus.DEGRADED
            message = "Adapter not registered (provider OK)"
        else:
            status = HealthStatus.UNHEALTHY
            message = "Neither adapter nor provider registered"
        
        return PlatformHealth(
            platform=platform,
            adapter_registered=adapter_registered,
            provider_registered=provider_registered,
            api_key_configured=api_key_configured,
            status=status,
            message=message
        )
    
    @classmethod
    def _check_adapter_registered(cls, platform: str) -> bool:
        """检查 adapter 是否已注册"""
        try:
            from wechat_backend.ai_adapters.factory import AIAdapterFactory
            from wechat_backend.ai_adapters.base_adapter import AIPlatformType
            
            try:
                platform_type = AIPlatformType(platform)
                return AIAdapterFactory.is_platform_available(platform_type)
            except ValueError:
                # 平台类型不在枚举中
                return False
        except Exception as e:
            api_logger.error(f"Error checking adapter for {platform}: {e}")
            return False
    
    @classmethod
    def _check_provider_registered(cls, platform: str) -> bool:
        """检查 provider 是否已注册"""
        try:
            from wechat_backend.ai_adapters.provider_factory import ProviderFactory
            providers = ProviderFactory.get_available_providers()
            return platform in providers
        except Exception as e:
            api_logger.error(f"Error checking provider for {platform}: {e}")
            return False
    
    @classmethod
    def _check_api_key_configured(cls, platform: str) -> bool:
        """检查 API key 是否已配置"""
        try:
            from legacy_config import Config
            return Config.is_api_key_configured(platform)
        except Exception as e:
            api_logger.error(f"Error checking API key for {platform}: {e}")
            return False
    
    @classmethod
    def _generate_recommendations(cls, results: Dict[str, Any]) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        # 检查平台消失问题
        adapter_only_count = results['summary']['adapter_only']
        if adapter_only_count > 0:
            recommendations.append(
                f"⚠️  {adapter_only_count} platform(s) have adapter but no provider. "
                "Check provider_factory.py registration."
            )
        
        # 检查国内平台配置
        for platform in cls.DOMESTIC_PLATFORMS:
            platform_data = results['platforms'].get(platform, {})
            if platform_data.get('status') == HealthStatus.UNHEALTHY.value:
                recommendations.append(
                    f"❌ Critical: {platform} is unhealthy. "
                    "This is a domestic platform that should always be available."
                )
        
        # 检查海外平台配置
        unconfigured_overseas = []
        for platform in cls.OVERSEAS_PLATFORMS:
            platform_data = results['platforms'].get(platform, {})
            if not platform_data.get('api_key_configured', False):
                unconfigured_overseas.append(platform)
        
        if unconfigured_overseas:
            recommendations.append(
                f"ℹ️  {len(unconfigured_overseas)} overseas platform(s) not configured: "
                f"{', '.join(unconfigured_overseas)}. "
                "Add API keys to .env file if needed."
            )
        
        # 检查整体健康度
        healthy_ratio = results['summary']['healthy'] / results['summary']['total']
        if healthy_ratio < 0.5:
            recommendations.append(
                f"⚠️  Less than 50% of platforms are healthy. "
                "Review AI platform configuration urgently."
            )
        
        return recommendations
    
    @classmethod
    def get_platform_status_summary(cls) -> str:
        """
        获取平台状态摘要（用于启动日志）
        
        Returns:
            str: 格式化的状态摘要
        """
        try:
            from wechat_backend.ai_adapters.provider_factory import ProviderFactory
            from wechat_backend.ai_adapters.factory import AIAdapterFactory
            
            providers = ProviderFactory.get_available_providers()
            
            # 构建状态字符串
            status_parts = []
            for platform in cls.EXPECTED_PLATFORMS:
                has_adapter = cls._check_adapter_registered(platform)
                has_provider = platform in providers
                has_key = cls._check_api_key_configured(platform)
                
                if has_adapter and has_provider and has_key:
                    status_parts.append(f"✅ {platform}")
                elif has_adapter and has_provider:
                    status_parts.append(f"⚠️  {platform}(no key)")
                elif has_adapter:
                    status_parts.append(f"⚠️  {platform}(no provider)")
                else:
                    status_parts.append(f"❌ {platform}")
            
            return f"AI Platforms: {', '.join(status_parts)}"
        except Exception as e:
            return f"AI Platforms: Error checking status - {e}"


def run_startup_health_check():
    """
    在应用启动时运行健康检查

    这个函数应该在 app.py 或 run.py 的启动阶段调用
    
    【关键修改】：
    1. 检测到配置缺失时仅记录警告，不抛出异常
    2. 始终返回 True，允许后续流程继续运行
    3. 使用 INFO/WARNING 日志级别，避免 ERROR 阻塞
    """
    api_logger.info("Running startup AI platform health check...")

    try:
        results = PlatformHealthMonitor.run_health_check()
        
        # 统计未配置的平台
        unconfigured_platforms = []
        unhealthy_platforms = []
        
        for platform, health_data in results.get('platforms', {}).items():
            if not health_data.get('api_key_configured', False):
                unconfigured_platforms.append(platform)
            if health_data.get('status') == HealthStatus.UNHEALTHY.value:
                unhealthy_platforms.append(platform)

        # 【关键修改 1】：配置缺失仅记录 INFO，不阻塞启动
        if unconfigured_platforms:
            msg = (f"ℹ️  {len(unconfigured_platforms)} platform(s) not configured: "
                   f"{', '.join(unconfigured_platforms)}. "
                   f"Add API keys to .env if needed.")
            api_logger.info(msg)  # 使用 INFO 而不是 ERROR
        
        # 【关键修改 2】：不健康平台记录 WARNING，但不阻止启动
        if unhealthy_platforms:
            api_logger.warning(
                f"⚠️  {len(unhealthy_platforms)} platform(s) unhealthy: "
                f"{', '.join(unhealthy_platforms)}. System will proceed with reduced functionality."
            )

        # 打印状态摘要
        summary = PlatformHealthMonitor.get_platform_status_summary()
        api_logger.info(summary)

        # 【关键修改 3】：根据实际健康状态决定是否打印警告
        if unhealthy_platforms:
            api_logger.warning(
                f"⚠️  {len(unhealthy_platforms)} platform(s) unhealthy: "
                f"{', '.join(unhealthy_platforms)}. System will proceed with reduced functionality."
            )
            # 有不健康平台，返回警告状态
            api_logger.info(
                "AI Platform health check completed with warnings, "
                "system proceeding with available platforms."
            )
        elif unconfigured_platforms:
            # 仅未配置，但无不健康平台
            api_logger.info(
                "AI Platform health check completed. "
                "Some platforms not configured but system is functional."
            )
        else:
            # 所有平台都健康
            api_logger.info(
                "✅ AI Platform health check passed! All platforms are functional."
            )

        return {
            'success': True,  # 始终返回成功，允许启动
            'status': HealthStatus.DEGRADED.value if unconfigured_platforms else HealthStatus.HEALTHY.value,
            'results': results,
            'warnings': results.get('warnings', []) if unhealthy_platforms else [],
            'unconfigured_platforms': unconfigured_platforms,
            'unhealthy_platforms': unhealthy_platforms
        }
        
    except Exception as e:
        # 【关键修改 4】：即使健康检查异常，也仅记录 ERROR 并继续
        api_logger.error(f"Health check failed with exception: {e}")
        import traceback
        api_logger.error(f"Traceback: {traceback.format_exc()}")
        api_logger.warning("⚠️  Health check failed, but system will proceed anyway.")

        # 返回允许启动的结果 - 确保包含 status 键避免 KeyError
        return {
            'success': True,  # 即使异常也允许启动
            'status': 'unknown',  # 添加 status 键，避免 app.py 读取时 KeyError
            'results': None,
            'warnings': [f"Health check failed: {e}"],
            'unconfigured_platforms': [],
            'unhealthy_platforms': [],
            'error': str(e)
        }
