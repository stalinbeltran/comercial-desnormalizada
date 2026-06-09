import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()


def _make_engine(prefix: str):
    host     = os.environ[f"{prefix}HOST"]
    port     = os.environ[f"{prefix}PORT"]
    user     = os.environ[f"{prefix}USER"]
    password = os.environ[f"{prefix}PASSWORD"]
    db       = os.environ[f"{prefix}NAME"]
    url = (
        f"mysql+mysqlconnector://{user}:{password}"
        f"@{host}:{port}/{db}?charset=utf8mb4"
    )
    return create_engine(
        url,
        pool_recycle=3600,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


engine_origen  = _make_engine("DB_")
engine_destino = _make_engine("DB_DESN_")
CHUNK_SIZE     = int(os.getenv("ETL_CHUNK_SIZE", 5_000))
