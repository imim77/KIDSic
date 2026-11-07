"""LocationService converts one database snapshot into map and list evidence."""
from KIDSic.db.uow.base import UnitOfWorkFactory
from KIDSic.dto.location import (
    LocationCollection, LocationFeature, LocationMetadata, LocationPoint,
    LocationProperties, LocationQuery,
)
from KIDSic.services.interfaces.location import LocationServiceInterface
from KIDSic.services.interfaces.presenters import EnrolmentPresenter, SubsidyPresenter


class LocationService(LocationServiceInterface):
    _required = ('name', 'location_name', 'address', 'city', 'provider_kind', 'district', 'location_role', 'sources')
    _optional = ('website_url', 'email', 'phone', 'distance_m')

    def __init__(self, uow_factory: UnitOfWorkFactory, subsidies: SubsidyPresenter, enrolment: EnrolmentPresenter):
        self._uow_factory = uow_factory
        self._subsidies = subsidies
        self._enrolment = enrolment

    async def list_locations(self, query: LocationQuery) -> LocationCollection:
        async with self._uow_factory() as uow:
            rows = await uow.locations.list_locations(query)
        features = [self._feature(dict(row)) for row in rows]
        mapped = sum(feature.geometry is not None for feature in features)
        return LocationCollection(features=features, metadata=LocationMetadata(
            total=len(features), mapped=mapped, unmapped=len(features) - mapped,
            scope=('radius' if query.near is not None
                   else 'bbox' if query.bbox is not None else 'city'),
        ))

    def _feature(self, row: dict) -> LocationFeature:
        location_id = str(row['location_id']) if row['location_id'] else None
        kindergarten_id = str(row['kindergarten_id'])
        return LocationFeature(
            id=location_id or f'seat:{kindergarten_id}', geometry=self._point(row),
            properties=LocationProperties(
                **{key: row[key] for key in self._required},
                **{key: row.get(key) for key in self._optional},
                location_id=location_id, kindergarten_id=kindergarten_id,
                areas=row.get('areas', []), historical_data=row.get('historical_data', []),
                field_sources=row.get('field_sources', {}),
                enrolment=self._enrolment.present(row.get('enrolment', [])),
                subsidy_policies=[self._subsidies.present(policy) for policy in row.get('subsidy_policies', [])]),
        )

    @staticmethod
    def _point(row: dict) -> LocationPoint | None:
        """_point maps a facility's coordinates, but a seat's only when a
        source attests both of them, so a guessed seat never looks verified."""
        sources = row.get('field_sources', {})
        if row['longitude'] is None or (row['location_role'] != 'facility' and not all(
                key in sources for key in ('longitude', 'latitude'))):
            return None
        return LocationPoint(coordinates=(row['longitude'], row['latitude']))
