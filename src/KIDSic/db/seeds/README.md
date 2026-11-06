# Gradsko sufinanciranje

[Snimka od 4. studenoga 2026.](2026-11-04_municipal_subsidies.sql) sadrži devet
skupova pravila sa službenih gradskih stranica i službenih glasila. Svaki zapis
sadrži izvore i mjesta u dokumentima. Ne dodaje se API, kalkulator ni prikaz.

Nakon `alembic upgrade head` i uvoza gradova Zagreb, Varaždin i Rijeka:

```sh
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f src/KIDSic/db/seeds/2026-11-04_municipal_subsidies.sql
```

SQL zapis radi u jednoj transakciji. Ponovljeno izvršavanje ažurira istu snimku
i čuva identitete. Nedostajući grad prekida cijeli upis. Ne mijenja objekte,
kontakte, koordinate ni postojeće izvore imenika. Buduće promjene zahtijevaju
novi ključ snimke i zatvaranje prethodnog razdoblja; ne prepisivati povijest.

Tablica `pravila_sufinanciranja` povezuje grad s tipovima pružatelja.
Za budući prikaz kod fizičkog objekta povezati `objekti.municipality_id` s
`municipality_id` politike i `vrtici.provider_kind` s `provider_kinds`.
Kod prikaza samo sjedišta koristi se `sjedista_vrtica.municipality_id`.
To daje moguće pravilo; ugovor ustanove i pravo pojedine obitelji moraju se
provjeriti zasebno. `unknown` i `other` ne nasljeđuju subvencije javnih vrtića.

Format `rules.schema_version=1` je opisni:

- `*_cents`: cijeli eurocenti po djetetu mjesečno, osim gdje je navedena dnevna osnovica.
- `city_subsidy_cents`, `parent_fee_*` i `economic_price_*` imaju različito značenje.
- `rates`, `eligibility` i `reliefs`: tarife, uvjeti i olakšice; nisu programski izrazi.
- `pending_change`: prijedlog koji se ne smije koristiti kao važeća tarifa.
- `NULL` iznos znači nepoznato, a ne besplatno; status `partial` traži dodatnu potvrdu.
- `valid_until` je uključiv. `NULL` granica znači da nije potvrđena; ne znači trajno pravo.
- `verified_on` označava dan provjere. Prije aktualnog prikaza ponovno provjeriti izvor.

Varaždin: gradski roditeljski udjeli 90/50/25 € i privatne/vjerske subvencije
360/400/425 €, s pravilima za istodobno upisanu djecu i posebne okolnosti.
**Iznos za dadilje nije potvrđen**: odluka iz 9/24 upućuje na zaseban zaključak;
ne pretpostavljamo da automatski vrijedi cjenik privatnih vrtića.

Zagreb: privatni/vjerski vrtići i dadilje 352,54–412,26 €, ovisno o prihodima.
Dodatnih 180 € već je uključeno. Gradski vrtići imaju odvojene roditeljske tarife
za cjelodnevni i poludnevni program te obiteljske olakšice. Državna sredstva
nisu pribrojena gradskoj subvenciji.

Rijeka: drugi osnivači 335 € jaslice / 275 € vrtić, od rujna 2026. do kolovoza
2027.; gradske roditeljske tarife 48/54/70 € za cjelodnevni program. Pragovi
prihoda izraženi su propisanim udjelom prosječne plaće RH, bez nagađanja
aktualne eurske protuvrijednosti. Dadilje 260 €; 310 € ostaje prijedlog u
savjetovanju do 6. studenoga 2026. Godišnji gradski limit djece za dadilje nije
potvrđen broj i ne predstavlja broj djece u jednoj obitelji.

# Upisni dokumenti

[Snimka od 5. studenoga 2026.](2026-11-05_zagreb_enrolment.json) sadrži odlomke
triju službenih izvora Grada Zagreba za gradske vrtiće:

| Izvor | Opseg | Datum |
| --- | --- | --- |
| [Obavijest o upisu 2026./2027.](https://vrtici.zagreb.hr/UserDocsImages/Upisi/Obavijest_upisi_dv_2627.pdf) (KLASA 601-01/26-001/249, URBROJ 251-07-11-26-1) | svi gradski vrtići; dio odlomaka samo imenovane ustanove | objavljeno 11. 5. 2026. |
| [Obavijest o upisu u program predškole 2026./2027.](https://vrtici.zagreb.hr/UserDocsImages/Upisi/Obavijest_upisi_pred%C5%A1kola_2627.pdf) (URBROJ 251-07-11-26-2) | 22 imenovana vrtića koji provode predškolu | objavljeno 11. 5. 2026. |
| [Upisi u gradske vrtiće](https://vrtici.zagreb.hr/upisi-u-gradske-vrtice-111/111) | svi gradski vrtići | stanje stranice 5. 11. 2026. |

Licenca: [Uvjeti korištenja www.zagreb.hr](https://www.zagreb.hr/uvjeti-koristenja/2048)
(29. 12. 2020.) dopuštaju preuzimanje i ponovnu uporabu izvornih dokumenata uz
navođenje izvora. Obavijesti su službeni tekstovi uprave objavljeni radi
informiranja javnosti, pa nisu zaštićene autorskim pravom (ZAPSP, NN 111/21,
čl. 18. st. 3.). `vrtici.zagreb.hr` nema vlastite uvjete korištenja.

Odlomci su prepisani cijeli, bez rezanja kroz uvjete i datume. Svaki dokument
ima URL, licencu, `reference_date` i `date_kind` (`published` za obavijesti,
`observed` za stranicu bez datuma) te `valid_until` (kraj pedagoške godine).
Dokument je `current` dok traje to razdoblje, ali rokovi unutar njega mogu
biti istekli. Za PDF-ove je zabilježen `sha256` preuzete datoteke.

Uvoz (`kidsic-sync-enrolment`) za svaki izvor ažurira `izvori_podataka` te stabilan `accepted` `izvorni_zapisi` za pojedini obuhvat, a odlomke u
`odlomci_znanja` bez `location_id`. Odlomak bez `institutions` vrijedi za sve
aktivne ustanove navedenih vrsta u gradu prema `obuhvati_dokumenata` pravilu
(opseg `municipality`), uključujući kasnije dodane ustanove. Tekst se ne kopira
po ustanovi. Imenovane
ustanove moraju se jednoznačno podudarati prema normaliziranom nazivu, inače
se prekida cijeli uvoz. Upisni zapisi ne dokazuju da je ustanova aktivna;
to određuju samo zapisi imenika. Opozvani izvor (`import_allowed=false`) ostaje
opozvan i pri ponovnom uvozu.

Uz odlomke, dokument može imati `calls`: strukturirane krugove upisa koji se
upisuju jednom u tablicu `upisni_krugovi`, s obuhvatom izvornog dokumenta. Obavijest daje glavni
rok 13. 5. 2026. 9:00 – 22. 5. 2026. 16:00 na eupisi.zgvrtici.hr, a DV Remetinec
i DV Ivane Brlić Mažuranić bilježi kao ustanove koje 2026./2027. ne provode
upise (`neprihvacanja_upisa`; API iz toga izvodi `accepting=false`). Stranica daje upis tijekom godine do 31. 8. 2027.
(kraj pedagoške godine) bez objavljenog početka. Koraci i dokumenti ostaju samo
u odlomcima, da se isti tekst ne održava dvaput.

Nije uvezeno, jer licenca nije potvrđena:

- **Varaždin**: [Natječaj za upis u DV „Varaždin” 2026./2027.](https://djecjivrticvz.hr/wp-content/uploads/2026/03/Natjecaj-za-upis-djece-u-pedagosku-godinu-2026-2027.pdf)
  (31. 3. 2026., rok 1.–30. 4. 2026., osobna predaja u Upravi vrtića). Stranica
  vrtića nema uvjete ponovne uporabe. Primjenjuje li se ZAPSP čl. 18. st. 3.
  na natječaj javne ustanove, treba potvrditi.
- **Rijeka**: [Uvjeti korištenja rijeka.hr](https://www.rijeka.hr/uvjeti-koristenja/)
  zabranjuju reprodukciju bez pisane suglasnosti. Službeni javni poziv za upis
  2026./2027. nije pronađen na rijeka.hr.
- Privatni i vjerski vrtići te obrti dadilja nemaju zajednički gradski izvor;
  za njih RAG vraća `no_evidence`.

Skup [Upisi u vrtiće u gradu Rijeka po godinama](https://data.gov.hr/ckan/dataset/upisi-u-vrtice)
(CC BY 4.0) sadrži samo broj upisane djece 2015.–2018., a ne postupak upisa.
Nova pedagoška godina dobiva novu snimku i nove ključeve obavijesti, a stare
ostaju za povijest. Stranica `zagreb-enrolment-page` zamjenjuje se novijim stanjem.


# Šibenik — pregledane lokacije i službene poveznice

[Snimka lokacija od 6. studenoga 2026.](2026-11-06_sibenik_locations.json)
čuva četiri izravne dopune baze: Brat Sunce, Osmijeh (Jelačićeva 13F), Sunce
(Brodarica) i Žižula. Sadrži točne DGU adresne točke, izvorni GML izdvojene
adrese, SHA256 arhive, postupak pretvorbe EPSG:3035 u EPSG:4326 i bilješku
provjere identiteta. Adrese/nazivi povezani su s nacionalnim registrom MZOM-a.
Oba skupa koriste Otvorenu dozvolu RH. Točke označavaju službene adrese;
nisu terenski izmjereni ulazi. Osmijehov objekt u Jelačićevoj nije zasebno
registrirano sjedište u Ulici Martina Kolunića 2A.

[Snimka službenih poveznica](2026-11-06_sibenik_official_references.json)
pokriva svih sedam trenutačno mapiranih objekata. Čuva URL-ove za programe,
radno vrijeme ili kontakt za njegovu potvrdu, datum i rezultat provjere.
Otvorena licenca vanjskog sadržaja nije potvrđena. Snimka ne sadrži preuzete
opise programa, satnice, cijene, dobne uvjete, brojeve skupina ni slobodna
mjesta. Pet objekata ima referencu na stranicu s radnim vremenom; Sunce i
Osmijeh imaju kontakt za potvrdu. Poveznica ne potvrđuje aktualnost sadržaja.

Ovo su podatkovne snimke već primijenjenih jednokratnih dopuna lokalne baze,
a ne migracije ni novi automatski uvoznici. Generirani UUID-ovi baze izostavljeni
su; ustanove/objekti opisani su nazivom i adresom. Za ponovnu primjenu prvo
jednoznačno provjeriti identitet, postojeće objekte i status izvora. Ne stvarati
duplikate ni ponovno omogućavati opozvane izvore. Postojeće adrese sjedišta,
OSM objekti i njihove koordinate ostaju sačuvani. Uvoz programa i satnica traži
zasebno potvrđen otvoreni izvor ili dopuštenje; nije dio ovih snimki.
