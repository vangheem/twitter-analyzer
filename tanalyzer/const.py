import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy_aio import ASYNCIO_STRATEGY


HOME = str(Path.home())
DB_FILEPATH = os.path.join(HOME, '.twitter-analyzer.db')
DB_ENGINE = create_engine(
    'sqlite:///' + DB_FILEPATH, strategy=ASYNCIO_STRATEGY
)
