# xmmcg-net

这是 XMMCG 比赛专用网站的源代码仓库。
：我能在不懂一行vue的情况下写出一个网站吗？
：可以，但是我要死了

--
**技术栈**：前端Vue.js + Element Plus（控件样式），后端Django + Pillow库处理图片。部署使用debian服务器+常规的gunicron作为WSGI + nginx转发。（不过我被nginx折磨得要死）

## 环境变量配置

项目使用 **python-decouple** 管理敏感配置信息，避免将密钥硬编码在代码中。

### 配置文件位置
项目支持两个环境变量文件（按优先级）：
1. **`login_credentials.env`**（项目根目录） - 用于存储敏感的登录凭证
2. **`.env`**（项目根目录） - 用于其他环境变量

### 必需配置项

在项目根目录创建 `login_credentials.env` 文件，包含以下内容：

```env
# Django 密钥（生产环境必须更改）
SECRET_KEY=your-secret-key-here

# Majdata.net API 凭证
MAJDATA_USERNAME=xmmcg5
MAJDATA_PASSWD_HASHED=your-hashed-password-here
```

### 可选配置项

```env
# 调试模式（生产环境设为 False）
DEBUG=True

# 允许的主机（逗号分隔）
ALLOWED_HOSTS=localhost,127.0.0.1

# Majdata.net 集成开关
ENABLE_CHART_FORWARD_TO_MAJDATA=True

# Majdata.net API 地址（默认值可不设置）
MAJDATA_BASE_URL=https://majdata.net/api3/api/
MAJDATA_LOGIN_URL=https://majdata.net/api3/api/account/Login
MAJDATA_UPLOAD_URL=https://majdata.net/api3/api/maichart/upload
```

### 获取配置值

所有配置在 [backend/xmmcg/xmmcg/settings.py](backend/xmmcg/xmmcg/settings.py) 中已自动加载：

```python
from decouple import config, Csv

# 带默认值的配置
DEBUG = config('DEBUG', default=False, cast=bool)

# 必需配置（无默认值，缺失时报错）
SECRET_KEY = config('SECRET_KEY')

# CSV 列表配置
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
```

### 安全提示

⚠️ **重要**：
- `.env` 和 `login_credentials.env` 已添加到 `.gitignore`，**请勿提交到版本控制**
- 生产环境必须修改 `SECRET_KEY` 和 `MAJDATA_PASSWD_HASHED`
- 使用以下命令生成新密钥：
  ```bash
  python backend/xmmcg/manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```

## 快速开始

### 后端设置

```bash
cd backend/xmmcg
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 前端设置

```bash
cd front
npm install
npm run dev
```

详细文档请参阅：
- [后端 README](backend/xmmcg/README.md) - Django 项目说明
- [前端 README](front/README.md) - Vue 3 项目说明
- [BIDDING_SYSTEM_GUIDE.md](BIDDING_SYSTEM_GUIDE.md) - 竞标系统详细说明
- [COMPETITION_PHASE_SYSTEM.md](COMPETITION_PHASE_SYSTEM.md) - 比赛阶段管理
- [PEER_REVIEW_SYSTEM.md](PEER_REVIEW_SYSTEM.md) - 同行评审系统

这是xmmcg比赛专用网站xmmcgnet的源代码仓库。
---

部署注意
