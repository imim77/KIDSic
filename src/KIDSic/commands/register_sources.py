"""Register CKAN sources; --dry-run requires no PostgreSQL connection."""
import argparse
import asyncio
import json
import sys


from KIDSic.config.settings import Settings
from KIDSic.exceptions import KIDSicError, PersistenceError
from KIDSic.services.dependency import DependencyService


class SourceRegistrationCommand:
    def __init__(self, settings):
        self._settings = settings

    async def run(self, dry_run=False, source_keys=None):
        async with DependencyService(self._settings).source_service(
            with_database=not dry_run, source_keys=source_keys,
        ) as service:
            return await (service.preview_sources() if dry_run else service.register_sources())


def run_cli(command_type, description, argv=None, *, supports_removals=False):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--dry-run', action='store_true', help='Validate without accessing the database.')
    parser.add_argument('--source', action='append', dest='source_keys',
                        choices=('national', 'zagreb-municipal', 'zagreb-other', 'varazdin-childminders',
                                 'rijeka-kindergartens'),
                        help='Select a source; repeat to select several. Default: all five.')
    if supports_removals:
        parser.add_argument('--allow-removals', action='store_true',
                            help='Allow missing source keys to be deleted after reviewing the complete resource.')
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env(require_database=not args.dry_run)
        options = {'allow_removals': args.allow_removals} if supports_removals else {}
        result = asyncio.run(command_type(settings).run(args.dry_run, args.source_keys, **options))
    except (PersistenceError, OSError):
        print('Source operation failed: check connectivity, DATABASE_URL and Alembic migrations.', file=sys.stderr)
        raise SystemExit(1) from None
    except KeyError:
        print('Set DATABASE_URL before writing to the database.', file=sys.stderr)
        raise SystemExit(1) from None
    except (KIDSicError, ValueError) as error:
        print(f'Source operation failed: {error}', file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main(argv=None):
    run_cli(SourceRegistrationCommand, 'Register kindergarten and childminder CKAN sources.', argv)


if __name__ == '__main__':
    main()
