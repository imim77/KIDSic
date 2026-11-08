"""Column names bridge dynamic domain-field updates and Croatian SQL storage."""

COLUMNS = {
    'kindergarten_id': 'id_vrtica',
    'geography_source_record_id': 'id_zapisa_geografskog_izvora',
    'name': 'naziv',
    'provider_kind': 'vrsta_pruzatelja',
    'email': 'e_posta',
    'phone': 'telefon',
    'website_url': 'mrezna_stranica',
    'provenance': 'podrijetlo',
    'address': 'adresa',
    'postal_code': 'postanski_broj',
    'settlement': 'naselje',
    'settlement_key': 'kljuc_naselja',
    'municipality_id': 'id_jedinice_lokalne_samouprave',
    'longitude': 'geografska_duzina',
    'latitude': 'geografska_sirina',
    'attributes': 'obiljezja',
    'district': 'gradska_cetvrt',
    'kind': 'vrsta',
}

TABLE_FIELDS = {
    'vrtici': (
        'id',
        'name',
        'provider_kind',
        'email',
        'phone',
        'website_url',
        'provenance',
        'oib',
    ),
    'objekti': (
        'id',
        'kindergarten_id',
        'name',
        'kind',
        'address',
        'postal_code',
        'settlement',
        'settlement_key',
        'district',
        'longitude',
        'latitude',
        'attributes',
        'provenance',
        'municipality_id',
    ),
    'sjedista_vrtica': (
        'kindergarten_id',
        'address',
        'postal_code',
        'settlement',
        'settlement_key',
        'municipality_id',
        'longitude',
        'latitude',
        'attributes',
        'geography_source_record_id',
    ),
}


def database_column(field: str) -> str:
    return COLUMNS.get(field, field)


def domain_projection(table: str, *, qualifier: str = '') -> str:
    prefix = qualifier + '.' if qualifier else ''
    return ','.join(prefix + database_column(field) + ' AS ' + field
                    for field in TABLE_FIELDS[table])
