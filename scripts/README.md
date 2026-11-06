# Pregledane dopune

Skripte ne dohvaćaju ništa s mreže. Svaka čita jednu lokalnu, ručno pregledanu
snimku i njome zamjenjuje trenutačno stanje izvora u jednoj transakciji. Zajedničke
korake (izvor, zapis, dokaz polja, RAG odlomak, zaključavanje i naredbeni
redak) dijele preko `reviewed_snapshot.py`.

Bez `--apply` skripta izvede cijeli uvoz nad bazom i zatim ga poništi. Tako
probni prolaz provjerava iste uvjete kao pravi upis. Obje varijante trebaju
`DATABASE_URL`.

# Varaždinski gradski vrtići

JSON snimke i cacheovi opisani u nastavku lokalni su generirani podaci i nisu
uključeni u Git. Mogu sadržavati izvorne kontakte i identifikatore iz CKAN-a.
Alati za ručni uvoz zahtijevaju lokalnu pregledanu snimku; redoviti CKAN uvoz
ne ovisi o tim datotekama.

`varazdin-municipal-nominatim.json` čuva službene adrese devet objekata
Dječjeg vrtića Varaždin, Nominatim odgovore i odluke o podudaranju.
Izvor adresa: https://djecjivrticvz.hr/objekti/.
OSM podaci: © OpenStreetMap contributors, ODbL 1.0.
OSM nazivi područja nisu potvrda službenih granica gradskih četvrti.

Pregled i upis (potreban `DATABASE_URL`):

```sh
uv run python scripts/import_varazdin.py
uv run python scripts/import_varazdin.py --apply
```

Uvoz povezuje devet objekata s postojećom ustanovom, koristi stabilne ID-eve
objekata i izvornih zapisa pri svakom pokretanju. Ne šalje nove
zahtjeve Nominatimu. `quarter`, `suburb` i `neighbourhood` čuvaju se u
`objekti.attributes`; `district` se ne zamjenjuje drugim geografskim pojmom.
Svih devet objekata ima geokodirane koordinate. Hrašćica koristi točno
podudaranje adresne točke Ruđera Boškovića 9A. Za Kućan službeni pročišćeni
statut navodi Varaždinsku 131b; ta je zgrada korištena umjesto škole na broju
131. Adresa za prikaz ostaje 131 prema stranici objekata, a adresa za
geokodiranje 131b čuva se u `attributes.geocoding_address` i izvornom zapisu.
Izvor: https://djecjivrticvz.hr/wp-content/uploads/2026/02/Statut-Djecjeg-vrtica-Varazdin-Procisceni-tekst-2024.pdf.
To su adresna podudaranja, a ne neovisno potvrđene oznake vrtića u OSM-u.
Korisnička dopuna postavlja oba polja područja na `Hračćica` za Hrašćicu i
`Kućan` za Kućan. Te su vrijednosti u bazi označene kao `manual_area`, imaju
zaseban korisnički izvor i čuvaju se pri ponovnom uvozu. Cijeli odgovor,
status provjere i izvor za svako polje ostaju zabilježeni.

Pretraga vraća `quarter` i `suburb` uz rezultat. `find_options(area='Banfica', …)`
filtrira objekte prije RAG dohvaćanja. Parser prepoznaje pohranjena područja
unutar traženog grada, česte padeže ženskih naziva te Centra i Đurka:

```sh
# Provjeri objekte alatom prikazi_vrtice: grad Varaždin, područje Banfica.
```

Dobna prikladnost ostaje `unknown` bez odgovarajućeg izvora programa. Za takve
rezultate servis vraća lokacijske podatke u `age_unknown`, a ne potvrđene dobne
preporuke. Uvoz dodaje leksičke geografske dokumente s OSM izvorima, bez
embeddinga i bez pretpostavki o slobodnim mjestima ili dobnim uvjetima.
MCP alat za kartu i razgovorni servis pretrage ostaju zasebna sučelja.

## Ostali varaždinski vrtići

`varazdin-other-directory.json` i `varazdin-other-nominatim.json` sadrže deset
ostalih vrtića. Drugi zapis čuva rezultate adresnih pretraga, odbačene
kandidate, izvore fizičkih lokacija i odabrane koordinate/područja.

```sh
uv run python scripts/import_other_varazdin.py
uv run python scripts/import_other_varazdin.py --apply
```

Svih deset ima koordinate i `suburb`; devet ima `quarter`. Zečić ima
`suburb: Brezje`, bez OSM vrijednosti za `quarter`. S devet gradskih objekata,
karta vraća 19 lokacija povezanih s 11 ustanova dječjih vrtića.

Adresna podudaranja predstavljaju adresne točke ili zgrade/komplekse, bez
jamstva da označavaju točan ulaz. OSM područja nisu službene gradske četvrti.
Bajka koristi adresu 16, a ne središte područja. Pinokio koristi puni naziv
ulice Ivana Trnskoga 21, uspoređen s oznakom na službenoj stranici; rezultati
u Bjelovaru odbačeni su. Za Zečić su odbačene istoimene adrese u Donjem
Kućanu i Jalkovcu, a Sveta Uršula koristi samostanski kompleks na broju 3.
Glavni izvori:

- https://varazdin.hr/djecji-vrtici/
- https://www.dvpinokio.hr/kontakt
- https://vrtic-zecic.hr/kontakt/

Društvo Naša djeca, Sportska abeceda i Junior uklonjeni su iz baze na
korisnikov zahtjev, zajedno sa svojim lokacijama i RAG zapisima. Izuzeti su
iz oba popisa za obogaćivanje. Nacionalni normalizator preskače njihova
imenovana varaždinska sjedišta kako ih sljedeća sinkronizacija ne bi vratila.
Stari odgovori na pojedinačne upite ostaju samo u lokalnom geokoderskom
cacheu i ne uvoze se kao objekti.

Uvoz sprema geografske dokumente za leksički RAG i provenijenciju svakog
polja. Ne dodaje programe, dobne uvjete ni embeddinge.

## Sjedišta obrta dadilja

`varazdin-childminders-nominatim.json` sadrži pregledane rezultate za svih 14
obrta iz CKAN izvora `varazdin-childminders`, uključujući cache pojedinačnih
upita, odbačene kandidate, dodatne izvore i razloge odabira. Podaci geokodiraju
registriranu adresu; ne potvrđuju zasebno mjesto rada ni točan ulaz.

```sh
uv run alembic -c src/KIDSic/db/alembic/alembic.ini upgrade head
uv run python scripts/import_childminder_geography.py
uv run python scripts/import_childminder_geography.py --apply
```

Svih 14 sjedišta ima koordinate; 12 ima `quarter`, 13 `suburb`, a 10
`neighbourhood`. Čarobna kućica ima naselje Hrašćica, bez OSM kvartovskih
vrijednosti. Kikići imaju `suburb: Brezje`, bez `quarter`; istoimena adresa
u Donjem Kućanu je odbačena. Čarobna šuma je izravno označena kao childcare
POI; Zeko je adresno podudaranje zgrade označene i kao Rođendaonica Medo
Brundo, bez pretpostavke da ta oznaka opisuje djelatnost obrta.

Za Balon snova izvorni CSV nema kućni broj. CompanyWall i Fininfo navode
Franje Račkog 17 za isti matični broj obrta. Za geokodiranje je korišten
broj 17, dok izvorna adresa sjedišta ostaje sačuvana. Izvori su u
`address_evidence_urls`, a puna adresa geokodiranja u atributima sjedišta.

Geografija se sprema u `sjedista_vrtica`: `longitude`, `latitude` i
`attributes`, uz FK `geography_source_record_id` prema izvornom zapisu.
Uvoz ne stvara retke u `objekti`, čuva postojeće ID-eve i zahtijeva
nepromijenjenu pregledanu adresu. Ponavljanje ažurira trenutačno stanje
izvora. Redoviti CKAN uvoz čuva geografiju, a SQL pogled i RAG
ignoriraju je ako se adresa promijeni ili geografski izvor postane neaktivan.

MCP prikaz nakon ovoga vraća 33 lokacije s koordinatama: 19 objekata vrtića i
14 sjedišta obrta. Sjedišta zadržavaju identitet `seat:<kindergarten_id>` i
na kartici imaju jasnu oznaku „Sjedište”.

## Riječki objekti vrtića

`rijeka-nominatim-cache.json` čuva jednokratne serijske adresne i imenovane
OSM pretrage; `rijeka-reviewed-geography.json` čuva pregledane odluke i
odbačene kandidate za svih 50 objekata izvora `rijeka-kindergartens`.
Obje datoteke su lokalne generirane snimke, izuzete iz Gita. Uvoz nema
mrežnih zahtjeva i nije ovisnost aplikacije tijekom korištenja.

```sh
uv run python scripts/import_rijeka_geography.py
uv run python scripts/import_rijeka_geography.py --apply
```

Pregled od 2026-11-04 potvrđuje 27 lokacija: točne adresne točke/zgrade i
imenovane vrtićke POI-je. Za preostala 23 objekta nema dovoljno preciznog
podudaranja; središta ulica i susjedni kućni brojevi nisu prihvaćeni.
Svih 27 potvrđenih lokacija ima OSM `suburb`, a 11 `neighbourhood`.
`quarter` nije izmišljen; oznake poput `Mjesni odbor Zamet` čuvaju se kao
OSM `suburb`, bez proglašavanja službenih granica ili zamjene `district`.

Školske zgrade na objavljenim adresama Topolina, Gabbiana, Kozale i Vala
predstavljaju adresno podudaranje, bez tvrdnje o zasebnom ulazu. Za Žirafu
Ante Mandića 50 označava kompleks Islamskog centra; rad vrtića na toj adresi
potvrđuje [službeni godišnji plan](https://zirafa-vrtic.com/wp-content/uploads/2024/10/GPP-DV-Zirafa-2024-2025.pdf).
To ne mijenja privatni tip pružatelja. Za Gardelin i Vežicu korišten je
imenovani vrtićki POI: OSM navodi obližnju ulicu bez broja, a službena CSV
adresa ostaje sačuvana. Drenova je imenovana OSM vrtićka zgrada u ulici
Stanka Frankovića, bez OSM broja. Krnjevo je prihvaćeno prema adresi Karasova
4, uz zabilježenu razliku naziva (`Vrtić Turnić`) u OSM-u.

Dodatni pregled koristi OSM izvadak od 5898 adresnih/vrtićkih elemenata
(`rijeka-osm-addresses-cache.json`) te pretragu naziva neovisno o kategoriji
(`rijeka-osm-names-cache.json`). Pronađena je imenovana zgrada `Vrtić
Podmurvice` u Cavtatskoj ulici, OSM way `1088777755`, pa je dodana 27. točka.
Mavrica sada koristi imenovani vrtićki POI `1118773461`, umjesto adresne
zgrade u istom kompleksu. Prethodni kandidat ostaje sačuvan u snimci.
Za svaki neriješeni objekt spremljen je konkretan razlog odbijanja:
primjerice Bujska ima 11/15/15a, ali ne 17; Braće Fučak ima 5a, ali ne 5c;
Rastočine imaju stambenu zgradu 5 bez potvrđenog vrtićkog ulaza 5/A.
Nema automatskog preslikavanja susjednih brojeva niti središta ulica.

Uvoz zahtijeva postojeću aktivnu CSV vezu, nepromijenjeni naziv/adresu i
identitete objekta/ustanove. Ne stvara ustanove ni lokacije. Koristi isti
advisory lock kao CKAN sinkronizacija, transakcijsku zamjenu stanja izvora,
izvorne odgovore i provenijenciju svakog geografskog polja. Ručne ispravke
područja i postojeći kontakti ostaju očuvani. Geografski RAG dokumenti ne
potvrđuju dobne uvjete, programe ili slobodna mjesta.

Ako kasniji CSV promijeni adresu, prethodni geografski `izvorni_zapisi` s
`reviewed_address` postaje kandidat za novi pregled: API tada ne prikazuje
staru točku, a područja i RAG ne koriste taj dokaz. Ponavljanje istog CSV-a
čuva pregledanu geografiju i identitete.

GIS/WMS nije korišten, u skladu s korisnikovim odabirom OSM izvora.
CSV zapis KBC Kantrida
ostaje za provjeru jer Grad sada govori o bivšoj bolnici na tom lokalitetu.
Izvori: [GIS katalog](https://data.rijeka.hr/dataset/gis-grad-rijeka),
[bivša bolnica Kantrida](https://www.rijeka.hr/rezultati-visekruznog-savjetovanja-o-buducoj-namjeni-kompleksa-bivse-djecje-bolnice-kantrida/).


## Šibenik

Prvo uvesti nacionalni registar, zatim pregledane fizičke objekte:

```sh
uv run kidsic-sync-kindergartens --source national
uv run python scripts/import_sibenik.py
uv run python scripts/import_sibenik.py --apply
```

Naredbe zahtijevaju `DATABASE_URL` u okruženju. Nacionalni registar pod
Otvorenom dozvolom RH daje ustanove, adrese sjedišta i kontakte. Šest zapisa
pripada Šibeniku/Brodarici; Hozana zadržava zagrebačko sjedište.
`sibenik-reviewed-locations.geojson` je verzionirana pregledana snimka iz
OSM-a (ODbL-1.0, © OpenStreetMap contributors), s izvornim oznakama, ID-evima,
SHA256 izvornog PBF-a i obrazloženjima prihvaćanja/isključivanja.
Prihvaćeni su Šibenski tići → Smilje, Vidici → Šibenska maslina i Blažena
Hozana → istoimena ustanova u Zagrebu. Četiri preostala OSM kandidata nemaju
potpunu potvrđenu adresu/identitet. Nisu uvezeni ni pretvoreni u sjedišta.

Uvoz koristi stabilne OSM identitete, provjerava aktivni nacionalni izvor i
nepromijenjenog vlasnika, poštuje `import_allowed`, čuva izvor svakog polja i
zamjenjuje stanje tek nakon uspješnog cijelog uvoza. Ponovljeni uvoz ne duplicira
objekte. Promijenjeno povezivanje zahtijeva pregled; prazan ili nevaljan uvoz
ne zamjenjuje posljednju dobru snimku. Povlačenje dopuštenja izvora skriva
njegove objekte preko postojećeg mehanizma aktivnih izvora.

Provjera identiteta ustanove nije dozvola za kopiranje sadržaja njezine stranice.
Programi, radno vrijeme, cijene i upisi nisu uključeni bez otvorenog izvora.
Pokrivenost fizičkih objekata trenutačno je tri, ne svi šibenski vrtići.
