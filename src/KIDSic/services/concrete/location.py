"""LocationService converts one database snapshot into map and list evidence."""
from KIDSic.dto.location import (
    LocationCollection, LocationFeature, LocationMetadata, LocationPoint,
    LocationProperties, LocationQuery,
)
from KIDSic.services.interfaces.location import LocationServiceInterface


class LocationService(LocationServiceInterface):
    def __init__(self, uow_factory):
        self._uow_factory = uow_factory

    async def list_locations(self, query: LocationQuery) -> LocationCollection:
        async with self._uow_factory() as uow:
            rows = await uow.locations.list_locations(query)
            features = []
            for row in rows:
                location_id = str(row['location_id']) if row['location_id'] else None
                kindergarten_id = str(row['kindergarten_id'])
                point = None
                seat_evidence = dict(row).get('field_sources', {})
                if row['longitude'] is not None and (row['location_role'] == 'facility' or
                        all(key in seat_evidence for key in ('longitude', 'latitude'))):
                    point = LocationPoint(coordinates=(row['longitude'], row['latitude']))
                features.append(LocationFeature(
                    id=location_id or f'seat:{kindergarten_id}', geometry=point,
                    properties=LocationProperties(**{
                        key: row[key] for key in (
                            'name', 'location_name', 'address', 'city', 'provider_kind',
                            'district', 'location_role', 'sources',
                        )
                    }, location_id=location_id, kindergarten_id=kindergarten_id,
                        field_sources=dict(row).get('field_sources', {})),
                ))
            mapped = sum(feature.geometry is not None for feature in features)
            return LocationCollection(features=features, metadata=LocationMetadata(
                total=len(features), mapped=mapped, unmapped=len(features) - mapped,
                scope='bbox' if query.bbox is not None else 'city',
            ))
