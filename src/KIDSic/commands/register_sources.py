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


def run_cli(command_type, description, argv=None):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--dry-run', action='store_true', help='Validate without accessing the database.')
    parser.add_argument('--source', action='append', dest='source_keys',
                        choices=('national', 'zagreb-municipal', 'zagreb-other', 'varazdin-childminders'),
                        help='Select a source; repeat to select several. Default: all four.')
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env(require_database=not args.dry_run)
        result = asyncio.run(command_type(settings).run(args.dry_run, args.source_keys))
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
