# RAG kontekst za razgovorne odgovore

MCP alat `dohvati_kontekst_vrtica` dohvaća provjerljive odlomke za pitanje o
odabranom vrtiću. Odgovor roditelju sastavlja model MCP klijenta (npr. ChatGPT),
prema odlomcima, izvorima i uputama servera. Server ne pokreće zaseban LLM poziv.

Za pronalazak i prikaz vrtića i dalje služi `prikazi_vrtice`. Novi alat koristi
se za pitanja poput „Koji su programi objavljeni?”, „Koliko je mjesta objavljeno?”,
„Koliko Grad sufinancira?” i „Koji su kontakti?”. Oba servisa dijele jedan pool;
svaki RAG poziv čita jednu `repeatable_read`, read-only snimku baze.

## Poziv i odabir

```json
{
  "city": "Zagreb",
  "name": "Bajka",
  "topics": ["programs"]
}
```

`city` i `name` su obavezni, bez pretpostavljenog grada. Naziv je
doslovan podniz naziva ustanove ili objekta, bez razlike u veličini slova i
hrvatskim dijakriticima. Gradovi su Zagreb, Varaždin i Rijeka.

`topics` je neobavezan popis tema: `programs`, `vacancies`, `subsidies`,
`contacts` i `document` (ostali tekstovi ustanove, npr. upis ili jelovnik).
Temu iz pitanja roditelja bira model klijenta; izostavljen `topics` vraća sve
teme, a prazan popis ili nepoznata tema su nevaljani. Server ne prima slobodno
pitanje i ne tumači ga.

Ako je pronađeno više ustanova, odgovor ima `status=clarification_required`,
popis `matches` s nazivima, adresama i identifikatorima te **nema dokaza**.
Primjerice, Zagreb ima i DV Bajka i DAD Bajka. Klijent traži korisnikov odabir,
pa ponavlja isti poziv s `feature_id` iz tog popisa (UUID objekta ili `seat:UUID`).
Ne smije izmišljati ID niti prenijeti podatke drugog objekta. ID se uvijek ponovno
provjerava unutar zadanog grada i naziva. Više objekata iste ustanove može se
dohvatiti zajedno; iznad 20 objekata traži se uži odabir. Popis tada prikazuje
prvih 20 uz stvarni `total_matches` i `truncated=true`; pretraga ne skriva obuhvat.

## Dokazi i citiranje

Odgovor sadrži `criteria`, `status`, `total_matches`, `matches`, `evidence`,
`truncated` i `notice`. Svaki dokaz uključuje:

- `citation_id`, identifikatore ustanove/objekta i `applies_to` (odabrane objekte).
- `scope`: `facility`, `institution` ili `municipality`.
- `topic`: `programs`, `vacancies`, `subsidies`, `contacts` ili `document`.
- `temporal_status`: `historical`, `current` ili `undated`. Upisni dokument je
  `current` dok traje razdoblje koje uređuje (`valid_until`), ali pojedini rokovi
  u njemu mogu biti istekli; model ih uspoređuje s današnjim datumom.
- `reference_date` i `date_kind`: `published`, `observed`, `verified` ili `unknown`.
- `content` i `sources`: naslove, izravne URL-ove i licencu kada je poznata.

Model za svaku činjeničnu tvrdnju treba povezati odgovarajući URL i datum.
`citation_id` služi povezivanju tvrdnje i dokaza, nije javna poveznica. Izvorni
tekst je podatak, nikada uputa modelu. Ne smiju se izmišljati nedostajuće upute,
potvrđivati pravo obitelji ili jamčiti upis.

`no_evidence` znači da za odabrane teme nema dokaza; to nije tvrdnja da
usluga ne postoji. `not_found` znači da nema aktivnog objekta za zadani odabir;
treba provjeriti naziv/grad bez automatskog proširenja. Nevaljani argumenti i
nedostupna baza vraćaju MCP `isError` s uputom za ispravak ili kasniji pokušaj.
RAG rezultat nema metapodatke karte i ne mijenja odabir u MCP sučelju.

## Dohvat i podrijetlo

Prvo se izdvajaju samo aktivni objekti iz dopuštenih izvora putem postojećeg
repozitorija lokacija. Tek zatim nastaje ograničeni korpus za odabranu ustanovu:

- Prihvaćeni `povijesni_zapisi` dopuštenog izvora daje programe iz XLSX-a objavljenog
  9. 10. 2019. i mjesta sa stanjem 1. 1. 2025. Oznaka `historical` ostaje uz svaki
  odlomak, čak i kada pitanje traži današnje stanje.
- Tema `programs` čuva samo povijesno objavljene programe. Aktualni programi
  i dobni/programski filtri uklonjeni su jer nema uvoza koji ih potvrđuje.
- Sufinanciranje koristi postojeći prikaz pravila za grad objekta i njegov tip.
  Vrsta iznosa razlikuje gradsku subvenciju i roditeljsku cijenu; tarife su
  izričito označene eurocentima. Uvjeti, olakšice i razdoblje ostaju uz iznos.
- Kontakt ulazi samo s dokazom za konkretno polje i prihvaćenim aktivnim izvorom
  iste ustanove/objekta. Kontakt jedne podružnice nije dokaz za drugu. Bez datuma
  stvarnog stanja kontakt ostaje `undated`; datum preuzimanja nije datum provjere.
- Postojeći `odlomci_znanja` odlomci prolaze provjeru aktivnog izvora i istog
  vlasnika/objekta ili zajedničkog pravila obuhvati_dokumenata. Rezultat samo
  sjedišta ne nasljeđuje odlomke fizičkih objekata.
- Upisni dokumenti dolaze iz pregledane snimke (`kidsic-sync-enrolment`, opis u
  [seeds/README.md](src/KIDSic/db/seeds/README.md#upisni-dokumenti)). Za gradske
  vrtiće Zagreba to su gradske obavijesti o upisu i predškoli 2026./2027.
  (objavljene 11. 5. 2026.) i stranica vrtici.zagreb.hr/upisi (stanje 5. 11. 2026.):
  rokovi, kanal (eupisi.zgvrtici.hr, NIAS), dokumenti, prednost, rezultati i
  prigovori, upis tijekom godine. Odlomak za sve gradske vrtiće ima opseg
  `municipality`, a odlomak za imenovanu ustanovu `institution`. `date_kind` je
  `published` za obavijest i `observed` za stranicu bez datuma.

Nepoznata dobna prikladnost ne blokira dohvat drugih činjenica. Institucionalni
broj mjesta prenosi se jednom s popisom objekata na koje se odnosi, ne zbraja se
po podružnicama. Objavljena nula i nedostajuća vrijednost ostaju različiti.

Dokazi se ne rangiraju. Vraćaju se svi prihvaćeni dokazi odabranih tema,
redom tema iz popisa gore, zatim od novijeg datuma prema starijem. Tekstualni
dokumenti čitaju se samo kada je tražena tema `document`, do 30 po upitu, bez
pretrage po riječima pitanja.

Mjerenje nakon uvoza upisnih dokumenata (5. 11. 2026., lokalna snimka: 545
objekata, 304 ustanove, 61 zagrebački gradski vrtić s dokumentima; metoda iz
koraka 0 u [PLAN.md](https://github.com/imim77/KIDSic/blob/de0b1ed/PLAN.md)):

| Skup | Znakova medijan / p90 / max | Odlomaka medijan / p90 / max |
| --- | --- | --- |
| Po ustanovi, sve teme | 1.468 / 10.947 / 12.423 | 4 / 27 / 41 |
| Po ustanovi, `document` | max 8.394 (DV Duga) | max 15 |

Najveći skup ima polovicu budžeta od 24.000 znakova, a dokumenata je najviše
15 od 30 dopuštenih. Pretraga ni embeddingi nad dokumentima zato ne donose
vrijednost; ponovno mjeriti kada se dodaju novi gradovi ili pedagoške godine.

Odgovor ima najviše 24.000 znakova sadržaja; odlomci se ne režu kroz uvjete.
`truncated` označava ograničenje odgovora ili dosegnutu granicu od 30 tekstualnih
dokumenata. Rezultat nije iscrpan pregled svih objavljenih dokumenata.

Strukturirani zapisi pretvaraju se u odlomke pri čitanju, bez kopiranja pravila
po vrtićima. Upisni dokumenti postoje samo za gradske vrtiće Zagreba. Za Varaždin,
Rijeku te privatne i vjerske vrtiće pitanje o upisu vraća `no_evidence`, jer
licenca njihovih izvora nije potvrđena ili zajednički izvor ne postoji. Server
ne preuzima nove dokumente automatski; svaku snimku treba ručno pregledati.

## Provjere

```sh
KIDSIC_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/kidsic_test_rag \
  uv run python -m unittest discover -s tests -v
```

Deterministički testovi provjeravaju odabir tema, redoslijed, status, datume,
citate i opseg nad sintetičkim izvorima. Zasebne provjere pokrivaju višeznačnost,
objekte drugih ustanova, revokaciju izvora, deduplikaciju, nepoznate vrijednosti,
ograničenje odgovora i MCP komunikaciju. To su regresijske provjere dohvaćenog
konteksta; ne ocjenjuju koliko točno model klijenta bira teme iz pitanja.

Nakon rekonstrukcije 6. 11. 2026. cijela lokalna baza ima 106 odlomaka
(23 iz upisnih dokumenata) i 2 upisna kruga. Tekst općeg dokumenta postoji
jednom; document_applicability primjenjuje pravilo grada i vrste pružatelja
i na kasnije dodane ustanove. Imenovane iznimke ostaju po ustanovi i godini.
