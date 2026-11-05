"""Import reviewed official enrolment documents as RAG excerpts; --dry-run needs no database."""
import argparse
import asyncio
import json
import sys

from pydantic import ValidationError

from KIDSic.config.settings import Settings
from KIDSic.exceptions import KIDSicError
from KIDSic.services.dependency import DependencyService


class EnrolmentImportCommand:
    def __init__(self, settings):
        self._settings = settings

    async def run(self, dry_run=False):
        async with DependencyService(self._settings).enrolment_service(with_database=not dry_run) as service:
            return service.preview_import() if dry_run else await service.import_data()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Import reviewed official kindergarten enrolment documents.')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env(require_database=not args.dry_run)
        result = asyncio.run(EnrolmentImportCommand(settings).run(args.dry_run))
    except (OSError, KeyError):
        print('Enrolment import failed: check DATABASE_URL and connectivity.', file=sys.stderr)
        raise SystemExit(1) from None
    except (KIDSicError, ValueError, ValidationError) as error:
        print(f'Enrolment import failed: {error}', file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
