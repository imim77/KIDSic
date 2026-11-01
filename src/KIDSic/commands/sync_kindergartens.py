"""Import real CKAN JSON rows, retaining raw evidence and the last good snapshot."""
from KIDSic.commands.register_sources import SourceRegistrationCommand, run_cli
from KIDSic.services.dependency import DependencyService


class KindergartenSyncCommand(SourceRegistrationCommand):
    async def run(self, dry_run=False, source_keys=None):
        async with DependencyService(self._settings).source_service(
            with_database=not dry_run, source_keys=source_keys,
        ) as service:
            return await (service.preview_import() if dry_run else service.import_data())


def main(argv=None):
    run_cli(KindergartenSyncCommand, 'Import and activate kindergarten snapshots from CKAN JSON sources.', argv)


if __name__ == '__main__':
    main()
