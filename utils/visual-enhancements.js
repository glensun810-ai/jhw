/**
 * 视觉增强工具
 * 提供动画效果、渐变色彩等视觉增强功能
 * 
 * 版本：v2.0
 * 日期：2026-02-21
 */

/**
 * 麦肯锡风格配色方案
 */
const MCKINSEY_COLORS = {
  // 主色
  primary: {
    light: '#2c3e50',
    main: '#1a1a2e',
    dark: '#0f1a2e'
  },
  // 辅助色
  secondary: {
    light: '#34495e',
    main: '#16213e',
    dark: '#0f172a'
  },
  // 强调色
  accent: {
    light: '#3498db',
    main: '#0f3460',
    dark: '#0a2342'
  },
  // 高亮色
  highlight: {
    light: '#ff6b6b',
    main: '#e94560',
    dark: '#c8324a'
  },
  // 成功色
  success: {
    light: '#2ecc71',
    main: '#10b981',
    dark: '#059669'
  },
  // 警告色
  warning: {
    light: '#f39c12',
    main: '#f59e0b',
    dark: '#d97706'
  },
  // 错误色
  error: {
    light: '#e74c3c',
    main: '#ef4444',
    dark: '#dc2626'
  },
  // 中性色
  neutral: {
    white: '#ffffff',
    light: '#f8fafc',
    main: '#64748b',
    dark: '#1e293b'
  }
};

/**
 * 渐变色方案
 */
const GRADIENTS = {
  // 主渐变
  primary: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
  // 强调渐变
  accent: 'linear-gradient(135deg, #0f3460 0%, #34495e 100%)',
  // 高亮渐变
  highlight: 'linear-gradient(135deg, #e94560 0%, #ff6b6b 100%)',
  // 成功渐变
  success: 'linear-gradient(135deg, #10b981 0%, #2ecc71 100%)',
  // 警告渐变
  warning: 'linear-gradient(135deg, #f59e0b 0%, #f39c12 100%)',
  // 错误渐变
  error: 'linear-gradient(135deg, #ef4444 0%, #e74c3c 100%)',
  // 背景渐变
  background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
  // 卡片渐变
  card: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)'
};

/**
 * 阴影方案
 */
const SHADOWS = {
  // 轻阴影
  light: '0 2rpx 8rpx rgba(0, 0, 0, 0.05)',
  // 标准阴影
  normal: '0 4rpx 12rpx rgba(0, 0, 0, 0.08)',
  // 重阴影
  heavy: '0 8rpx 24rpx rgba(0, 0, 0, 0.12)',
  // 悬浮阴影
  hover: '0 8rpx 32rpx rgba(0, 0, 0, 0.15)',
  // 发光阴影
  glow: '0 0 20rpx rgba(233, 69, 96, 0.3)',
  // 内阴影
  inner: 'inset 0 2rpx 8rpx rgba(0, 0, 0, 0.05)'
};

/**
 * 动画效果
 */
const ANIMATIONS = {
  // 淡入
  fadeIn: `
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
  `,
  // 淡出
  fadeOut: `
    @keyframes fadeOut {
      from { opacity: 1; }
      to { opacity: 0; }
    }
  `,
  // 滑入
  slideIn: `
    @keyframes slideIn {
      from {
        transform: translateY(-20rpx);
        opacity: 0;
      }
      to {
        transform: translateY(0);
        opacity: 1;
      }
    }
  `,
  // 脉冲
  pulse: `
    @keyframes pulse {
      0%, 100% {
        transform: scale(1);
        opacity: 1;
      }
      50% {
        transform: scale(1.05);
        opacity: 0.8;
      }
    }
  `,
  // 闪烁
  shimmer: `
    @keyframes shimmer {
      0% {
        background-position: -1000px 0;
      }
      100% {
        background-position: 1000px 0;
      }
    }
  `,
  // 旋转
  spin: `
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
  `,
  // 弹跳
  bounce: `
    @keyframes bounce {
      0%, 100% {
        transform: translateY(0);
      }
      50% {
        transform: translateY(-10rpx);
      }
    }
  `
};

/**
 * 缓动函数
 */
const EASING = {
  // 线性
  linear: 'linear',
  // 易入
  easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
  // 易出
  easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
  // 易入易出
  easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  // 弹跳
  bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)'
};

/**
 * 生成渐变背景
 */
function createGradient(type, angle = 135) {
  const gradient = GRADIENTS[type] || GRADIENTS.primary;
  return gradient.replace('135deg', `${angle}deg`);
}

/**
 * 生成阴影
 */
function createShadow(level, color = null) {
  const shadow = SHADOWS[level] || SHADOWS.normal;
  if (color) {
    return shadow.replace(/rgba\(0, 0, 0, [\d.]+\)/, color);
  }
  return shadow;
}

/**
 * 生成动画
 */
function createAnimation(type, duration = '0.3s', delay = '0s', iteration = '1') {
  return `${type} ${duration} ${EASING.easeOut} ${delay} ${iteration}`;
}

/**
 * 生成过渡效果
 */
function createTransition(properties = ['all'], duration = '0.3s', easing = 'easeOut') {
  const props = properties.join(', ');
  return `${props} ${duration} ${EASING[easing] || EASING.easeOut}`;
}

/**
 * 生成玻璃态效果
 */
function createGlassmorphism(blur = '20rpx', opacity = 0.1) {
  return `
    background: rgba(255, 255, 255, ${opacity});
    backdrop-filter: blur(${blur});
    -webkit-backdrop-filter: blur(${blur});
    border: 1rpx solid rgba(255, 255, 255, 0.1);
  `;
}

/**
 * 生成流光效果
 */
function createShimmerEffect(width = '100%', height = '100%') {
  return `
    background: linear-gradient(
      90deg,
      rgba(255, 255, 255, 0) 0%,
      rgba(255, 255, 255, 0.1) 50%,
      rgba(255, 255, 255, 0) 100%
    );
    background-size: ${width} ${height};
    animation: shimmer 2s infinite;
  `;
}

/**
 * 生成状态指示器样式
 */
function createStatusIndicator(status) {
  const statusColors = {
    success: MCKINSEY_COLORS.success.main,
    warning: MCKINSEY_COLORS.warning.main,
    error: MCKINSEY_COLORS.error.main,
    info: MCKINSEY_COLORS.accent.main
  };
  
  const color = statusColors[status] || MCKINSEY_COLORS.neutral.main;
  
  return `
    width: 16rpx;
    height: 16rpx;
    border-radius: 50%;
    background: ${color};
    box-shadow: 0 0 12rpx ${color};
    animation: pulse 2s ease-in-out infinite;
  `;
}

/**
 * 生成卡片样式
 */
function createCardStyle(variant = 'default') {
  const variants = {
    default: `
      background: ${GRADIENTS.card};
      border-radius: 16rpx;
      box-shadow: ${SHADOWS.normal};
      border: 1rpx solid rgba(0, 0, 0, 0.05);
    `,
    elevated: `
      background: ${GRADIENTS.card};
      border-radius: 16rpx;
      box-shadow: ${SHADOWS.heavy};
      border: none;
    `,
    outlined: `
      background: #fff;
      border-radius: 16rpx;
      box-shadow: none;
      border: 2rpx solid ${MCKINSEY_COLORS.accent.main};
    `,
    glass: `
      ${createGlassmorphism()}
      border-radius: 16rpx;
      box-shadow: ${SHADOWS.normal};
    `
  };
  
  return variants[variant] || variants.default;
}

/**
 * 生成按钮样式
 */
function createButtonStyle(variant = 'primary', size = 'medium') {
  const variants = {
    primary: `
      background: ${GRADIENTS.accent};
      color: #fff;
    `,
    secondary: `
      background: ${GRADIENTS.card};
      color: ${MCKINSEY_COLORS.primary.main};
      border: 2rpx solid ${MCKINSEY_COLORS.accent.main};
    `,
    success: `
      background: ${GRADIENTS.success};
      color: #fff;
    `,
    warning: `
      background: ${GRADIENTS.warning};
      color: #fff;
    `,
    error: `
      background: ${GRADIENTS.error};
      color: #fff;
    `
  };
  
  const sizes = {
    small: 'padding: 12rpx 24rpx; font-size: 24rpx;',
    medium: 'padding: 16rpx 32rpx; font-size: 28rpx;',
    large: 'padding: 20rpx 40rpx; font-size: 32rpx;'
  };
  
  return `
    ${variants[variant] || variants.primary}
    ${sizes[size] || sizes.medium}
    border-radius: 44rpx;
    border: none;
    transition: ${createTransition(['transform', 'box-shadow'])};
  `;
}

module.exports = {
  MCKINSEY_COLORS,
  GRADIENTS,
  SHADOWS,
  ANIMATIONS,
  EASING,
  createGradient,
  createShadow,
  createAnimation,
  createTransition,
  createGlassmorphism,
  createShimmerEffect,
  createStatusIndicator,
  createCardStyle,
  createButtonStyle
};
