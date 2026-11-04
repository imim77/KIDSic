CKAN metadata fixtures were fetched on 2026-11-01 from the three `package_show`
endpoints configured in `SourceServiceFactory`. Only fields used by the client
and planner are retained. Resource IDs, URLs, formats and catalogue metadata are
real; row examples in `test_sources.py` are synthetic.

Implementation reference: imim77/FOIHireloom at
`8ba897db799e993aa43c7d488879efb3870218f2`, especially
`integrations/concrete/ckan.py`, `dto/ckan.py`,
`services/concrete/source_feed_registration.py` and
`commands/register_sources.py`. Its CKAN client is unchanged in the local
checkout at `ae794e24a3c16d1973a33fe72285dac4551505bb`.

Differences required here: resource IDs accept nonempty strings (MZOM uses a
slug); packages include attribution/licence metadata; a separate bounded JSON
download reads the actual kindergarten records. Registration still does not
download or import records. DataStore is not assumed to be enabled.

`ckan_childminders.json` and `varazdin_childminders.csv` are synthetic fixtures
for the Varaždin childminder resource. They test UTF-8 BOM, semicolon quoting,
leading-zero identifiers, whitespace and joint-trade OIBs. They contain no real
proprietors or contacts. The optional legacy Postman HTTP simulation explicitly
selects its original three JSON sources; the CSV path has separate HTTP-client
and database tests.

`ckan_rijeka.json` pins the official resource ID and CC-BY licence; its download
URL is synthetic. `rijeka.csv` uses published parent/facility names with
synthetic addresses. Tests encode its UTF-8 source text as Windows-1250 to
exercise the live CSV encoding without committing an opaque binary fixture.
