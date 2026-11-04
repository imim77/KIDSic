"""Import licensed Zagreb snapshots without replacing current directory data."""
import argparse
import asyncio
import json
import sys

from KIDSic.config.settings import Settings
from KIDSic.config.historical import zagreb_historical_sources
from KIDSic.exceptions import KIDSicError
from KIDSic.services.dependency import DependencyService


class HistoricalImportCommand:
    def __init__(self, settings):
        self._settings = settings

    async def run(self, dry_run=False, source_keys=None):
        async with DependencyService(self._settings).historical_service(
            with_database=not dry_run, source_keys=source_keys) as service:
            return await (service.preview_import() if dry_run else service.import_data())


def main(argv=None):
    parser = argparse.ArgumentParser(description='Import historical Zagreb programs and vacancies.')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--source', action='append', dest='source_keys',
        choices=[d.source.key for d in zagreb_historical_sources('https://data.zagreb.hr')])
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env(require_database=not args.dry_run)
        result = asyncio.run(HistoricalImportCommand(settings).run(args.dry_run, args.source_keys))
    except (OSError, KeyError):
        print('Historical import failed: check DATABASE_URL and connectivity.', file=sys.stderr)
        raise SystemExit(1) from None
    except (KIDSicError, ValueError) as error:
        print(f'Historical import failed: {error}', file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
