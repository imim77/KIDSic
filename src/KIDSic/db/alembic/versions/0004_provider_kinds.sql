WITH reviewed(city,name_key,provider_kind,source_url) AS (VALUES
    ('varazdin','dv varazdin','municipal','https://varazdin.hr/djecji-vrtici/'),
    ('varazdin','dv bajka','private','https://varazdin.hr/djecji-vrtici/'),
    ('varazdin','dv djecji svijet','private','https://varazdin.hr/djecji-vrtici/'),
    ('varazdin','dv malo drvo','private','https://varazdin.hr/upload/2024/11/obrazlozenje_nacrta_proracuna_2025-2027_-_672b9864ddddb.pdf'),
    ('varazdin','dv pinokio','private','https://varazdin.hr/djecji-vrtici/'),
    ('varazdin','dv sreca','private','https://varazdin.hr/upload/2024/11/obrazlozenje_nacrta_proracuna_2025-2027_-_672b9864ddddb.pdf'),
    ('varazdin','dv vrtic panda','private','https://varazdin.hr/upload/2024/11/obrazlozenje_nacrta_proracuna_2025-2027_-_672b9864ddddb.pdf'),
    ('varazdin','dv zecic','private','https://varazdin.hr/djecji-vrtici/'),
    ('varazdin','dv zeko','private','https://varazdin.hr/djecji-vrtici/'),
    ('varazdin','dv cira cara','private','https://varazdin.hr/djecji-vrtici/'),
    ('varazdin','dv sveta ursula','religious','https://varazdin.hr/djecji-vrtici/'),
    ('zagreb','dv carobna kucica','private','https://www.zagreb.hr/UserDocsImages/arhiva/odgoj_obrazovanje_spot/POPIS%20VJERSKIH%20I%20PRIVATNIH%20DV_ZA%20WEB_kris.pdf'),
    ('zagreb','dv cvjetnjak','religious','https://www.zagreb.hr/UserDocsImages/arhiva/odgoj_obrazovanje_spot/POPIS%20VJERSKIH%20I%20PRIVATNIH%20DV_ZA%20WEB_kris.pdf'),
    ('zagreb','dv drvo znanja','private','https://tltkindergarten.com/hr/'),
    ('zagreb','dv mali cvrcak','private','https://www.zagreb.hr/UserDocsImages/arhiva/odgoj_obrazovanje_spot/POPIS%20VJERSKIH%20I%20PRIVATNIH%20DV_ZA%20WEB_kris.pdf'),
    ('zagreb','dv mudre glavice','private','https://www.zagreb.hr/UserDocsImages/arhiva/odgoj_obrazovanje_spot/POPIS%20VJERSKIH%20I%20PRIVATNIH%20DV_ZA%20WEB_kris.pdf'),
    ('zagreb','dv ruzicnjak','private','https://rino-institut.hr/ruzicnjak-klinci-rinci/'),
    ('zagreb','dv zvjezdica','private','https://cas.hr/vrtic/'),
    ('zagreb','dv andela merici','religious','https://www.zagreb.hr/UserDocsImages/arhiva/odgoj_obrazovanje_spot/POPIS%20VJERSKIH%20I%20PRIVATNIH%20DV_ZA%20WEB_kris.pdf'),
    ('zagreb','dv frfi','private','https://www.zagreb.hr/UserDocsImages/arhiva/odgoj_obrazovanje_spot/POPIS%20VJERSKIH%20I%20PRIVATNIH%20DV_ZA%20WEB_kris.pdf'),
    ('zagreb','dv mirjam weiller','religious','https://www.zagreb.hr/UserDocsImages/arhiva/odgoj_obrazovanje_spot/POPIS%20VJERSKIH%20I%20PRIVATNIH%20DV_ZA%20WEB_kris.pdf'),
    ('zagreb','dv vitica','private','https://www.zagreb.hr/UserDocsImages/arhiva/odgoj_obrazovanje_spot/POPIS%20VJERSKIH%20I%20PRIVATNIH%20DV_ZA%20WEB_kris.pdf')
), candidate AS (
    SELECT k.id,COALESCE(m.key,CASE
        WHEN k.seat_county='Varaždinska županija' AND k.seat_settlement_key='varazdin'
            THEN 'varazdin'
        WHEN k.seat_county='Grad Zagreb' THEN 'zagreb' END) AS city,
        trim(regexp_replace(regexp_replace(translate(lower(k.name),'čćđšž','ccdsz'),
            '\mdjecji\s+vrtic\M','dv','g'),'[^[:alnum:]_]+',' ','g')) AS name_key
    FROM kindergarten k LEFT JOIN municipality m ON m.id=k.seat_municipality_id
    WHERE k.provider_kind='unknown'
), classified AS (
    SELECT c.id,COALESCE(r.provider_kind,'other') AS provider_kind,r.source_url
    FROM candidate c LEFT JOIN reviewed r ON r.city=c.city AND r.name_key=c.name_key
    WHERE r.provider_kind IS NOT NULL OR (c.city IN ('varazdin','zagreb')
        AND c.name_key LIKE ANY(ARRAY['drustvo %','glazbaonica %','hrvatski skijaski klub %','institut %','judo klub %','klizacko koturaljkaski klub %','kosarkaski klub %','kraci program %','kreativna udruga %','muski rukometni klub %','plesna udruga %','plesni studio %','program %','ritmicko plesna udruga %','sportska udruga %','sportsko %','sportski %','studio %','taekwondo klub %','tenis klub %','tjelovjezbeno drustvo %','tkd %','udruga %','uduga %','univerzalna sportska skola %','ustanova upravljanje sportskim objektima%']))
)
UPDATE kindergarten k SET provider_kind=c.provider_kind,
    provenance=jsonb_set(k.provenance,'{provider_kind}',
        COALESCE(k.provenance->'provider_kind',k.provenance->'name','{}'::jsonb) ||
        jsonb_build_object('migration','0004_provider_kinds',
            'previous_kind',k.provider_kind,
            'previous_provenance',k.provenance->'provider_kind') ||
        CASE WHEN c.source_url IS NOT NULL THEN jsonb_build_object('source_url',c.source_url)
            ELSE '{}'::jsonb END)
FROM classified c WHERE k.id=c.id;
