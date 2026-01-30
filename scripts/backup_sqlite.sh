#!/bin/bash

# 配置部分
# 项目根目录（db.sqlite3 所在的目录）
DB_DIR="/opt/xmmcg/backend/xmmcg/"
# 备份存放目录
BACKUP_DIR="/var/back/xmmcg/"
# 数据库文件名
DB_NAME="db.sqlite3"
# 加上时间戳的文件名
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="db_backup_${DATE}.sqlite3"

# 确保备份目录存在
mkdir -p $BACKUP_DIR

# 1. 安全备份 (使用 sqlite3 命令行工具的 .backup 指令，它是原子操作，不会锁死数据库)
# 注意：你需要安装 sqlite3 客户端 (sudo apt install sqlite3)
sqlite3 "$DB_DIR/$DB_NAME" ".backup '$BACKUP_DIR/$BACKUP_NAME'"

# 2. 压缩备份文件 (可选，节省空间)
gzip "$BACKUP_DIR/$BACKUP_NAME"

# 3. 删除 30 天前的旧备份
find $BACKUP_DIR -name "db_backup_*.gz" -mtime +30 -delete

echo "Backup $BACKUP_NAME completed."
