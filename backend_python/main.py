from dotenv import load_dotenv
from wechat_backend import app

# Load environment variables from .env file
load_dotenv()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5001)  # 使用5001端口与前端保持一致