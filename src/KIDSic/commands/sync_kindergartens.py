"""Import real CKAN JSON/CSV rows, retaining raw evidence and the last good snapshot."""
from KIDSic.commands.register_sources import SourceRegistrationCommand, run_cli
from KIDSic.services.dependency import DependencyService


class KindergartenSyncCommand(SourceRegistrationCommand):
    async def run(self, dry_run=False, source_keys=None, *, allow_removals=False):
        async with DependencyService(self._settings).source_service(
            with_database=not dry_run, source_keys=source_keys,
        ) as service:
            return await (service.preview_import() if dry_run else
                          service.import_data(allow_removals=allow_removals))


def main(argv=None):
    run_cli(KindergartenSyncCommand, 'Import and activate kindergarten and childminder snapshots from CKAN JSON/CSV sources.',
            argv, supports_removals=True)


if __name__ == '__main__':
    main()
