"""Read infrastructure settings from the process environment."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    pool_min_size: int = 1
    pool_max_size: int = 10

    def __post_init__(self):
        if not self.database_url.startswith(('postgresql://', 'postgres://')):
            raise ValueError('DATABASE_URL must be a PostgreSQL URL.')
        if not 1 <= self.pool_min_size <= self.pool_max_size:
            raise ValueError('Invalid database pool size.')

    @classmethod
    def from_env(cls):
        return cls(
            database_url=os.environ['DATABASE_URL'],
            pool_min_size=int(os.getenv('DATABASE_POOL_MIN_SIZE', '1')),
            pool_max_size=int(os.getenv('DATABASE_POOL_MAX_SIZE', '10')),
        )
