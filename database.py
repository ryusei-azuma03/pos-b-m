# database.py
import os
import urllib.parse
import logging
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# .env ファイルを読み込む
load_dotenv()

# 環境変数から取得
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "pos_app_matsuda")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "password")

# パスワードをURLエンコード
encoded_password = urllib.parse.quote_plus(DB_PASS)

# ローカル環境とAzure環境で証明書パスを分岐
if os.path.exists(os.path.join(os.path.dirname(__file__), "certificates", "DigiCertGlobalRootG2.crt.pem")):
    CERT_PATH = os.path.join(os.path.dirname(__file__), "certificates", "DigiCertGlobalRootG2.crt.pem")
else:
    CERT_PATH = None

# 接続情報のログ出力
logger.info(f"DB接続情報:")
logger.info(f"HOST: {DB_HOST}")
logger.info(f"PORT: {DB_PORT}")
logger.info(f"NAME: {DB_NAME}")
logger.info(f"USER: {DB_USER}")

# Base クラスを定義
Base = declarative_base()

# ローカル環境用の接続設定
def get_database_url():
    if DB_HOST == "127.0.0.1":
        # ローカルMySQL接続
        return f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        # Azure MySQL接続
        return (
            f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
            f"?ssl_ca={CERT_PATH}&ssl_verify_cert=true"
        )

try:
    # Engine と SessionLocal を生成
    engine = create_engine(
        get_database_url(),
        echo=True,  # SQLログを出力
        connect_args=(
            {"ssl": {"ssl_ca": CERT_PATH}} if CERT_PATH else {}
        )
    )
    
    # セッションファクトリを作成
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # 接続テスト
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        logger.info(f"接続テスト結果: {result.scalar()}")

except Exception as e:
    logger.error(f"データベース接続エラー: {type(e)}")
    logger.error(f"エラー詳細: {e}")
    # ローカル環境でエラーが発生した場合、一時的なセッションを作成
    SessionLocal = sessionmaker()
