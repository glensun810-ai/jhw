from flask import Flask, request, jsonify
import hashlib
import hmac
import json
import requests
from datetime import datetime
import os

from config import Config

# Initialize logging before other imports to capture all logs
from .logging_config import setup_logging
setup_logging(
    log_level=Config.LOG_LEVEL,
    log_file=Config.LOG_FILE,
    max_bytes=Config.LOG_MAX_BYTES,
    backup_count=Config.LOG_BACKUP_COUNT
)

# Import logger after setting up logging
from .logging_config import app_logger

# Initialize database
from .database import init_db
init_db()

# Configuration
APP_ID = Config.WECHAT_APP_ID
APP_SECRET = Config.WECHAT_APP_SECRET

# Global variable to store access token
access_token = None
token_expiration_time = None


def get_access_token():
    """Get access token from WeChat API"""
    global access_token, token_expiration_time

    # Check if token is still valid
    if access_token and token_expiration_time and datetime.now() < datetime.fromtimestamp(token_expiration_time):
        app_logger.debug("Using cached access token")
        return access_token

    # Request new access token
    params = {
        'grant_type': 'client_credential',
        'appid': APP_ID,
        'secret': APP_SECRET
    }

    app_logger.info(f"Requesting new access token for app_id: {APP_ID}")
    response = requests.get(Config.WECHAT_ACCESS_TOKEN_URL, params=params)
    data = response.json()

    if 'access_token' in data:
        access_token = data['access_token']
        expires_in = data.get('expires_in', 7200)  # Default to 2 hours
        token_expiration_time = datetime.now().timestamp() + expires_in - 300  # Refresh 5 min early
        app_logger.info("Successfully obtained new access token")
        return access_token
    else:
        app_logger.error(f"Failed to get access token: {data}")
        raise Exception(f"Failed to get access token: {data}")


app = Flask(__name__)
app.config.from_object(Config)

# Register the blueprint
from wechat_backend.views import wechat_bp
app.register_blueprint(wechat_bp)

@app.route('/')
def index():
    app_logger.info("Index endpoint accessed")
    return jsonify({
        'message': 'WeChat Mini Program Backend Server',
        'status': 'running',
        'app_id': APP_ID
    })

@app.route('/health')
def health_check():
    app_logger.debug("Health check endpoint accessed")
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/config', methods=['GET'])
def get_config():
    """Return basic configuration info"""
    app_logger.info("Configuration endpoint accessed")
    return jsonify({
        'app_id': APP_ID,
        'server_time': datetime.now().isoformat(),
        'status': 'active'
    })


if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host='127.0.0.1', port=5001)