"""AsyncpgLocationRepository reads active locations and source evidence together."""
from KIDSic.dao.interfaces.location import LocationRepository
from KIDSic.dto.location import LocationQuery
from KIDSic.dto.text import normalize


class AsyncpgLocationRepository(LocationRepository):
    def __init__(self, connection):
        self._connection = connection

    async def list_locations(self, query: LocationQuery):
        return await self._connection.fetch('''
          WITH active_record AS (
            SELECT r.kindergarten_id,r.location_id,
              jsonb_build_object('name',s.title,'url',s.url,'license',s.license,
                'reference_date',r.observed_on,'retrieved_at',r.fetched_at) AS evidence
            FROM source_record r JOIN data_source s ON s.id=r.source_id
            WHERE r.match_status='accepted' AND s.import_allowed
              AND s.active_batch_id=r.batch_id
          ), place AS (
            SELECT l.id AS location_id,l.kindergarten_id,l.name AS location_name,
              l.address,l.settlement,l.settlement_key,l.municipality_id,l.district,
              l.longitude,l.latitude,'facility' AS location_role,
              (SELECT jsonb_agg(DISTINCT r.evidence ORDER BY r.evidence)
               FROM active_record r WHERE r.location_id=l.id) AS sources
            FROM location l
            WHERE EXISTS (SELECT 1 FROM active_record r WHERE r.location_id=l.id)
            UNION ALL
            SELECT NULL,k.id,k.name,k.seat_address,k.seat_settlement,
              k.seat_settlement_key,k.seat_municipality_id,NULL,NULL,NULL,'seat',
              (SELECT jsonb_agg(DISTINCT r.evidence ORDER BY r.evidence)
               FROM active_record r WHERE r.kindergarten_id=k.id)
            FROM kindergarten k WHERE k.seat_settlement_key IS NOT NULL
              AND EXISTS (SELECT 1 FROM active_record r WHERE r.kindergarten_id=k.id)
              -- A facility outside the requested bounds still rules out a seat.
              AND NOT EXISTS (SELECT 1 FROM location l JOIN active_record r
                ON r.location_id=l.id WHERE l.kindergarten_id=k.id)
          )
          SELECT pl.location_id,pl.kindergarten_id,k.name,pl.location_name,
            pl.address,pl.settlement AS city,k.provider_kind,pl.district,
            pl.longitude,pl.latitude,pl.location_role,pl.sources
          FROM place pl JOIN kindergarten k ON k.id=pl.kindergarten_id
          LEFT JOIN municipality m ON m.id=pl.municipality_id
          WHERE (pl.settlement_key=$1 OR m.key=$1 OR $1=ANY(m.aliases))
            AND ($2='' OR strpos(lower(k.name),lower($2))>0
                       OR strpos(lower(pl.location_name),lower($2))>0)
            AND ($3::text IS NULL OR k.provider_kind=$3)
            AND ($4::float8[] IS NULL OR (
              pl.longitude BETWEEN $4[1] AND $4[3]
              AND pl.latitude BETWEEN $4[2] AND $4[4]))
          ORDER BY k.name,pl.location_name,pl.kindergarten_id,pl.location_id
        ''', normalize(query.city), query.q, query.provider_kind,
            list(query.bbox) if query.bbox is not None else None)
