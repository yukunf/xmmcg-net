"""测试环境变量加载"""
import sys
sys.path.insert(0, 'd:\\code\\xmmcg\\backend\\xmmcg')

# 模拟 settings.py 的配置
from pathlib import Path
from decouple import config, Csv, Config, RepositoryEnv

BASE_DIR = Path(__file__).resolve().parent / 'backend' / 'xmmcg'

# 加载环境变量文件
env_path = BASE_DIR.parent.parent / 'login_credentials.env'
print(f"环境变量文件路径: {env_path}")
print(f"文件是否存在: {env_path.exists()}")

if env_path.exists():
    # 读取文件内容
    with open(env_path, 'r', encoding='utf-8') as f:
        print("\n文件内容:")
        print(f.read())
    
    # 创建新的 config 对象
    env_config = Config(RepositoryEnv(str(env_path)))
    
    # 测试读取
    try:
        username = env_config('MAJDATA_USERNAME')
        password = env_config('MAJDATA_PASSWD_HASHED')
        debug = env_config('DEBUG', default=False, cast=bool)
        
        print("\n✅ 环境变量加载成功:")
        print(f"  MAJDATA_USERNAME: {username}")
        print(f"  MAJDATA_PASSWD_HASHED: {password[:20]}...")
        print(f"  DEBUG: {debug}")
    except Exception as e:
        print(f"\n❌ 加载失败: {e}")
else:
    print("❌ 环境变量文件不存在")
