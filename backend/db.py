import os
from pathlib import Path

import certifi
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine

repo_dir = Path(__file__).resolve().parent.parent

# 読み込む設定ファイルを選ぶ。
# 既定はローカルのDocker MySQL用の .env。
# 運営のAzure MySQLを使うときは、起動前に $env:APP_ENV_FILE = ".env.azure" を指定する。
env_file = os.environ.get("APP_ENV_FILE", ".env")
load_dotenv(repo_dir / env_file, encoding="utf-8-sig")

# 接続先を組み立てる。
# URL.create は値を部品ごとに受け取るので、パスワードの @ や & を区切り文字と誤解しない。
database_url = URL.create(
    drivername="mysql+pymysql",
    username=os.environ["MYSQL_USER"],
    password=os.environ["MYSQL_PASSWORD"],
    host=os.environ["MYSQL_HOST"],
    port=int(os.environ["MYSQL_PORT"]),
    database=os.environ["MYSQL_DATABASE"],
    query={"charset": "utf8mb4"},
)

connect_args = {"connect_timeout": 5}

# Azure Database for MySQL は暗号化（TLS）接続が必須。
# certifi の証明書一覧でサーバーの証明書を検証する。ローカルのDockerでは使わない。
if os.environ.get("MYSQL_SSL", "false").lower() == "true":
    connect_args["ssl"] = {"ca": certifi.where()}

# DB接続を管理する窓口を作る
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args=connect_args,
)
