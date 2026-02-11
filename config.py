import os

class Config:
    # WeChat Mini Program Configuration
    WECHAT_APP_ID = os.environ.get('WECHAT_APP_ID') or 'wx8876348e089bc261'
    WECHAT_APP_SECRET = os.environ.get('WECHAT_APP_SECRET') or '6d43225261bbfc9bfe3c68de9e069b66'
    WECHAT_TOKEN = os.environ.get('WECHAT_TOKEN') or 'your_default_token_here'

    # Server Configuration
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE') or None  # If not set, will use default logs/app.log
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', '10485760'))  # 10MB default
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', '5'))

    # WeChat API Endpoints
    WECHAT_TOKEN_URL = 'https://api.weixin.qq.com/cgi-bin/token'
    WECHAT_CODE_TO_SESSION_URL = 'https://api.weixin.qq.com/sns/jscode2session'
    WECHAT_ACCESS_TOKEN_URL = 'https://api.weixin.qq.com/cgi-bin/token'
    WECHAT_SEND_TEMPLATE_MSG_URL = 'https://api.weixin.qq.com/cgi-bin/message/wxopen/template/send'