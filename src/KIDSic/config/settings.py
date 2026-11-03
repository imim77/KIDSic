"""Read infrastructure settings from the process environment."""
from dataclasses import dataclass
import math
import os
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    database_url: str
    pool_min_size: int = 1
    pool_max_size: int = 10
    ckan_base_url: str = 'https://data.gov.hr/ckan'
    ckan_zagreb_base_url: str = 'https://data.zagreb.hr'
    ckan_dataset_id: str = 'djecji-vrtici'
    ckan_zagreb_municipal_dataset_id: str = 'gradski_vrtici_grada_zagreba'
    ckan_zagreb_other_dataset_id: str = 'privatni-vjerski-obrti-gz-kontakt-podaci'
    ckan_varazdin_childminders_dataset_id: str = 'grad-varazdin-dadilje'
    ckan_varazdin_childminders_resource_id: str = '2bde0eae-1d20-41c5-aec4-711f2a485439'
    ckan_timeout: float = 15.0
    ckan_max_bytes: int = 10 * 1024 * 1024

    def __post_init__(self):
        if not self.database_url.startswith(('postgresql://', 'postgres://')):
            raise ValueError('DATABASE_URL must be a PostgreSQL URL.')
        if not 1 <= self.pool_min_size <= self.pool_max_size:
            raise ValueError('Invalid database pool size.')
        for value in (self.ckan_base_url, self.ckan_zagreb_base_url):
            url = urlsplit(value)
            if url.scheme not in {'http', 'https'} or not url.hostname or url.query or url.fragment:
                raise ValueError('Invalid CKAN base URL.')
        if not math.isfinite(self.ckan_timeout) or self.ckan_timeout <= 0:
            raise ValueError('CKAN_TIMEOUT must be positive and finite.')
        if self.ckan_max_bytes <= 0:
            raise ValueError('CKAN_MAX_BYTES must be positive.')
        if any(not value.strip() for value in (self.ckan_dataset_id,
                self.ckan_zagreb_municipal_dataset_id, self.ckan_zagreb_other_dataset_id,
                self.ckan_varazdin_childminders_dataset_id, self.ckan_varazdin_childminders_resource_id)):
            raise ValueError('CKAN dataset IDs must not be blank.')

    @classmethod
    def from_env(cls, *, require_database: bool = True):
        return cls(
            database_url=(os.environ['DATABASE_URL'] if require_database else
                          os.getenv('DATABASE_URL', 'postgresql://localhost/kidsic')),
            pool_min_size=int(os.getenv('DATABASE_POOL_MIN_SIZE', '1')),
            pool_max_size=int(os.getenv('DATABASE_POOL_MAX_SIZE', '10')),
            ckan_base_url=os.getenv('CKAN_BASE_URL', 'https://data.gov.hr/ckan'),
            ckan_zagreb_base_url=os.getenv('CKAN_ZAGREB_BASE_URL', 'https://data.zagreb.hr'),
            ckan_dataset_id=os.getenv('CKAN_DATASET_ID', 'djecji-vrtici'),
            ckan_zagreb_municipal_dataset_id=os.getenv('CKAN_ZAGREB_MUNICIPAL_DATASET_ID', 'gradski_vrtici_grada_zagreba'),
            ckan_zagreb_other_dataset_id=os.getenv('CKAN_ZAGREB_OTHER_DATASET_ID', 'privatni-vjerski-obrti-gz-kontakt-podaci'),
            ckan_varazdin_childminders_dataset_id=os.getenv('CKAN_VARAZDIN_CHILDMINDERS_DATASET_ID', 'grad-varazdin-dadilje'),
            ckan_varazdin_childminders_resource_id=os.getenv('CKAN_VARAZDIN_CHILDMINDERS_RESOURCE_ID', '2bde0eae-1d20-41c5-aec4-711f2a485439'),
            ckan_timeout=float(os.getenv('CKAN_TIMEOUT', '15')),
            ckan_max_bytes=int(os.getenv('CKAN_MAX_BYTES', str(10 * 1024 * 1024))),
        )
