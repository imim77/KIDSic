"""SourceRegistrationPlanner validates catalogue identity and permitted formats."""
from KIDSic.dto.source import PlannedSource, SourceDefinition
from KIDSic.dto.ckan import CkanPackage
from KIDSic.exceptions import SourceImportError


class SourceRegistrationPlanner:
    def select(self, definition: SourceDefinition, package: CkanPackage) -> PlannedSource:
        # A changed/absent licence requires review, not implicit approval.
        if package.license_id != 'open-license':
            raise SourceImportError(f'{definition.key}: expected Otvorena dozvola (open-license).')
        formats = {'json': {'json', 'application/json'}, 'csv': {'csv', 'text/csv'}}
        expected = formats[definition.resource_format]
        resources = [r for r in package.resources if r.state == 'active'
                     and (r.format or '').strip().casefold() in expected
                     and (definition.resource_id is None or r.id == definition.resource_id)]
        if len(resources) != 1:
            raise SourceImportError(f'{definition.key}: expected exactly one active {definition.resource_format.upper()} resource matching the configured identity.')
        resource = resources[0]
        return PlannedSource(definition, package, resource)

    def validate(self, sources: list[PlannedSource]) -> None:
        if not sources:
            raise SourceImportError('Select at least one source.')
        identities, urls = set(), set()
        for source in sources:
            identity = (source.definition.base_url.rstrip('/'), source.resource.id)
            if identity in identities or str(source.resource.url) in urls:
                raise SourceImportError('Multiple datasets identify the same resource.')
            identities.add(identity)
            urls.add(str(source.resource.url))
