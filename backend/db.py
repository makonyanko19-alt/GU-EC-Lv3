import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine

# repo直下の.envを読み込む
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path, encoding="utf-8-sig")

# 接続先を組み立てる
database_url = URL.create(
    drivername="mysql+pymysql",
    username=os.environ["MYSQL_USER"],
    password=os.environ["MYSQL_PASSWORD"],
    host=os.environ["MYSQL_HOST"],
    port=int(os.environ["MYSQL_PORT"]),
    database=os.environ["MYSQL_DATABASE"],
    query={"charset": "utf8mb4"},
)

# DB接続を管理する窓口を作る
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)
