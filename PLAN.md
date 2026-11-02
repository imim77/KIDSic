# PLAN — KIDSic

## Gdje gradu najviše nedostaje dostupnih vrtićkih usluga?

Status: planirano; početni obuhvat je Grad Zagreb. Funkcionalnost nadograđuje postojeći uvoz imenika ustanova i gradskih objekata.

### Cilj i vrijednost

Povezati lokacije vrtićkih objekata, prometnu dostupnost i demografske podatke kako bi se izdvojila područja s mnogo male djece i slabijom dostupnošću vrtića. Gradu i javnosti omogućiti istraživanje gdje bi nova lokacija mogla poboljšati dostupnost.

Glavni demonstracijski trenutak: korisnik odabere novu lokaciju vrtića na karti, a aplikacija prikaže promjenu dostupnosti u odnosu na postojeće stanje, uz objašnjenje izračuna i njegovih ograničenja.

### Podaci koje povezujemo

- Postojeći nacionalni imenik i gradski skupovi: identitet ustanove, vrsta pružatelja i pripadajući objekti. Sjedište ustanove nije automatski lokacija pružanja usluge.
- [Geoportal Dječji vrtići](https://data.zagreb.hr/hr/dataset/geoportal-djecji-vrtici): lokacije i dostupni atributi objekata, nakon provjere sheme, koordinatnog sustava i uvjeta korištenja.
- [DZS — stanovništvo](https://podaci.dzs.hr/podaci/stanovnistvo/): stanovništvo prema dobi po zagrebačkim četvrtima iz Popisa 2021. Prije uvoza odabrati konkretnu tablicu te potvrditi dostupne dobne skupine i prostornu razinu.
- Službene granice četvrti koje odgovaraju prostornim jedinicama demografskog izvora; odabrati i dokumentirati konkretan izvor i licencu.
- [ZET — GTFS](https://www.zet.hr/gtfs2): stajališta i planirani vozni redovi za proširenje analize na javni prijevoz. Izračun treba uključiti i pješačke veze, čekanje i presjedanja.
- Potvrđeni kapaciteti po objektu i dobnoj skupini, ako se pribavi usporediv izvor. To je dodatna faza; objavljena slobodna mjesta nisu ukupni kapacitet.

Ustanove i objekte povezivati dostupnim stabilnim identifikatorima i provjerenim podudaranjima. Objekte prostorno povezati s granicama četvrti, a demografiju spojiti odgovarajućom šifrom prostorne jedinice. Nesigurna podudaranja izdvojiti za pregled.

### Korisnički tijek

1. Korisnik otvori kartu Zagreba i odabere dostupnu dobnu skupinu te način i prag dostupnosti.
2. Karta pokaže vrtićke objekte i područja s većim brojem djece i slabijom dostupnošću. Klik na četvrt otvara demografske podatke, rezultate izračuna i izvore.
3. Korisnik uključi scenarij i postavi hipotetski novi objekt na kartu.
4. Aplikacija usporedi postojeće stanje i scenarij: promjenu vremena ili udaljenosti do najbližeg objekta te područja kojima se dostupnost poboljšala.
5. Korisnik promijeni lokaciju ili prag dostupnosti i vidi kako to utječe na rezultat. Usporedba koristi iste izvore, polazišta i parametre.
6. Uz rezultat ostaju vidljivi pretpostavke, vremenska referenca svakog izvora i objašnjenje zašto je područje izdvojeno.

### Prva izvediva verzija

- Karta provjerenih objekata i demografskih pokazatelja po četvrtima, bez dvostrukog brojanja istog objekta iz različitih izvora.
- Odvojeno prikazati broj djece, broj objekata i mjeru dostupnosti. Ne uvoditi neobjašnjiv objedinjeni rezultat niti broj objekata predstavljati kao kapacitet.
- Prostorna preciznost prati izvor: podatak za četvrt ne prikazivati kao izmjeren broj djece u pojedinoj ulici ili zgradi. Ne raspoređivati djecu proizvoljno unutar četvrti.
- Za početnu usporedbu mogu se koristiti dokumentirane reprezentativne točke četvrti. Rezultate jasno označiti kao aproksimaciju; vrijeme ili udaljenost iz tih točaka ne predstavlja putovanje svake obitelji.
- Ako izračun prometnih ruta još nije dostupan, koristiti jasno označenu zračnu udaljenost. Ne pretvarati je u vrijeme hodanja ili vožnje.
- Dodavanje jedne hipotetske lokacije i usporedba dostupnosti prije i poslije, uz mogućnost uklanjanja scenarija. Scenarij ne mijenja izvorni imenik.
- Pripremiti reproducibilan demonstracijski primjer na stvarnoj snimci izvora; poboljšanje izračunati iz podataka, bez unaprijed izmišljenih rezultata.

### Proširenja nakon početne verzije

- Pješačka dostupnost preko mreže puteva, a zatim javni prijevoz prema GTFS voznom redu za odabrani dan i vrijeme. Dokumentirati izvor mreže puteva i uvjete korištenja.
- Finija prostorna analiza samo kada postoje odgovarajući demografski podaci.
- Usporedba više kandidatskih lokacija prema jasno navedenom cilju, primjerice smanjenju procijenjenog vremena pristupa.
- Analiza kapaciteta prema broju djece tek uz potvrđene, vremenski i dobno usporedive podatke. Ako kapacitet postoji samo za ustanovu, ne pripisivati ga svakom objektu.
- Simulacija dodatnog kapaciteta odvojeno od simulacije nove lokacije; korisnički uneseni kapacitet označiti kao pretpostavku scenarija.

### Tumačenje i ograničenja

- Popis 2021. opisuje stanje u svojoj referentnoj godini; ne dokazuje današnji broj djece ni broj djece koja čekaju upis. Dobne skupine ne sužavati bez podataka koji to podržavaju.
- Slabija prostorna dostupnost je pokazatelj za planiranje. Potvrđeni manjak mjesta zahtijeva podatke o kapacitetima, upisima i stvarnoj potražnji.
- Novi objekt može poboljšati prostornu dostupnost, ali sama lokacija ne jamči prikladan program, slobodno mjesto, izvedivost gradnje ili upis.
- Područje bez dostupnih podataka označiti kao nepoznato; nedostajući podatak nije nula. Usporedbu omogućiti i preko granica četvrti kako administrativna granica ne bi isključila blizak objekt.
- Uz svaku analizu navesti izvore, licence, pokrivenost, referentne datume, datum dohvata i metodu izračuna. Različite godine izvora prikazati izričito.

### Kriteriji prihvaćanja

- Svaki prikazani demografski pokazatelj vodi do izvora, prostorne jedinice, dobne skupine i referentne godine.
- Isti objekt u više izvora broji se jednom; sjedišta bez potvrđenog objekta i nesigurna povezivanja ne ulaze neprimjetno u izračun.
- Simulacija nove lokacije prikazuje početnu vrijednost, novu vrijednost i razliku pod istim parametrima. Dodavanje objekta ne može povećati minimalnu udaljenost do najbližeg objekta pod istom metrikom.
- Uklanjanje scenarija vraća početni rezultat. Polazišta koja već imaju bliži objekt zadržavaju svoju minimalnu udaljenost.
- Aproksimacije, nedostajući podaci i nepodržani načini putovanja jasno su označeni. Aplikacija ne prikazuje izmišljeni broj neupisane djece ili postotak poboljšanja.
- Demonstracija pokazuje povezivanje najmanje lokacija objekata, demografije i prostornih granica te omogućuje provjeru izvora i rezultata prije i poslije scenarija.

## Plan implementacije u manjim koracima

Obuhvat: prethodno opisana analiza dostupnosti vrtića u Zagrebu. Prvo gradimo upotrebljivu kartu objekata, potom analitičke slojeve i usporedbu jedne nove lokacije. Svaki korak može biti zasebna promjena koju provjeravamo prije nastavka. Sve stavke u nastavku su planirane.

### Polazište i Mapbox referenca

- Postoje React/TypeScript/Vite frontend, asyncpg pristup bazi, uvoz triju izvora i SQL pretraga. Frontend još prikazuje početnu stranicu; `src/KIDSic/api/` nema implementiran transport.
- Tablica `location` već ima koordinate, PostGIS `position` i prostorni indeks. Postojeći rezultat pretrage ne izlaže koordinate; potrebno je dodati ugovor za kartu. Nije potrebno ponovno uvoditi PostGIS.
- Referenca je lokalni [Mapbox integration skill](.agents/skills/mapbox-web-integration-patterns/SKILL.md), posebno React obrazac te prateće upute za tokene i uobičajene pogreške. Skill daje obrasce integracije, a nije postojeća KIDSic implementacija.
- Koristit ćemo izravno `mapbox-gl` u React komponenti: `useRef` za instancu i DOM element, `useEffect` za inicijalizaciju, uvoz Mapbox CSS-a i `map.remove()` pri uklanjanju. Promjene podataka ažuriraju izvor preko `setData()`, bez ponovnog stvaranja karte.
- Mapbox prikazuje podlogu i naše GeoJSON slojeve. Izračun dostupnosti i upravljanje izvornim podacima ostaju u Python/PostGIS dijelu aplikacije.

### Odabir pristupa i mjesta promjena

Razmotrena su dva pristupa integraciji:

1. **Izravni `mapbox-gl` u izdvojenoj React komponenti — odabrano.** Dodajemo jednu biblioteku, komponentu i povezivanje podataka. Slijedi instalirani skill i daje izravan pristup GeoJSON slojevima. Rizik su ručno upravljanje listenerima i usklađivanje React stanja s kartom; zato lifecycle i ažuriranje izvora ostaju na jednom mjestu.
2. **Dodatni React omotač za Mapbox.** Dodali bismo biblioteku s deklarativnim komponentama karte i slojeva. To može smanjiti ručno povezivanje, ali uvodi dodatnu ovisnost i provjeru kompatibilnosti s trenutačnim Reactom i Mapboxom. Za početni broj slojeva taj dodatak zasad nema jasnu korist; pristup možemo preispitati ako interakcije postanu znatno složenije.

Implementer kreće od ovih postojećih mjesta:

- `frontend/src/views/welcome/Welcome.tsx` — zamjena početnog prikaza; `frontend/src/shared/` — izdvojena karta i zajednički tipovi.
- `frontend/vite.config.ts` — trenutačni `root`, budući `envDir` i razvojni proxy; `frontend/package.json` — ovisnost i provjere frontenda.
- `src/KIDSic/dao/concrete/asyncpg_kindergarten.py`, metoda `find_options` — postojeća pretraga koju treba očuvati; za kartu dodati zaseban jasno imenovan upit i pripadajući DAO ugovor.
- `src/KIDSic/services/concrete/kindergarten_normalizer.py` — postojeća provjera koordinata i normalizacija uvoza; tu nadograditi podršku za potvrđeni Geoportal format.
- `src/KIDSic/db/alembic/versions/0001_simple_rag.sql` i `0002_settlement_seat.sql` — postojeći model; nove tablice i promjene dodavati novom migracijom.
- `src/KIDSic/api/`, `services/`, `dto/` i `factories/` — transport, poslovni ugovori i sastavljanje novih operacija prema postojećoj organizaciji; `tests/` — backend provjere.

### Pretpostavke i otvorena pitanja

- Prva analitička verzija obuhvaća Zagreb, jednu kandidatsku lokaciju i zračnu udaljenost. Pretraga drugih gradova ostaje dio postojećeg šireg proizvoda.
- Konkretni resursi Geoportala, granica i DZS tablice, njihove licence, dobne skupine i međusobna prostorna usklađenost još nisu potvrđeni za ovaj tijek. To su izlazni rezultati koraka g–i; bez njih ne tvrdimo da je analiza potpuna.
- Nisu provjereni stvarna popunjenost lokalne baze, pokrivenost koordinatama ni postojeći Mapbox račun/token. Provjeriti ih prije povezivanja stvarnog prikaza; ne popunjavati nedostatke izmišljenim podacima.
- HTTP framework još nije ovisnost projekta. U koraku d odabrati minimalan adapter uz postojeće asinkrone servise, a dogovoreni DTO zadržati neovisnim o njemu. MCP host i njegova pravila učitavanja potvrditi u koraku n.
- Prag dostupnosti i izbor reprezentativne točke moraju biti dokumentirane postavke, a ne predstavljeni kao službeni standard. Promjena metode znači ponovno računanje oba uspoređivana stanja.

### a) Pripremiti Mapbox konfiguraciju

- [ ] Dodati `mapbox-gl` v3 i konfiguraciju javnog `VITE_MAPBOX_ACCESS_TOKEN` tokena, uz predložak bez stvarne vrijednosti. Token za preglednik je javno vidljiv i kada dolazi iz `.env`; koristiti namjenski javni token s ograničenjima URL-ova za dopuštena okruženja.
- [ ] Uskladiti Vite `envDir` s lokacijom `frontend/.env.local` i `frontend/.env.example`, jer je trenutačni Vite `root` postavljen na `src/views`. Dodati TypeScript tip varijable i poruku kada token nedostaje.

**Gotovo kada:** aplikacija učitava konfiguraciju iz očekivane mape; nedostatak tokena daje razumljivu poruku.

### b) Prikazati osnovnu kartu Zagreba

- [ ] Dodati izdvojenu `KindergartenMap` komponentu u zajednički frontend kod i otvoriti je iz glavnog prikaza. Postaviti početni pogled na Zagreb, visinu spremnika, navigacijske kontrole i vidljivu atribuciju.
- [ ] Primijeniti lifecycle obrazac iz skilla, obraditi pogreške učitavanja i nepodržan WebGL te pozvati `resize()` kada se promijeni veličina panela. Kartu inicijalizirati jednom po montiranju; cleanup mora raditi i u React StrictModeu.

**Gotovo kada:** karta radi na desktopu i mobitelu, a ponovno otvaranje prikaza ne ostavlja dodatne instance ni listenere.

### c) Definirati ugovor podataka za kartu

- [ ] Dogovoriti DTO i GeoJSON `FeatureCollection`: stabilni `location_id`, `kindergarten_id`, naziv objekta, adresa, vrsta pružatelja, četvrt kada je poznata te podrijetlo i datumi. Koordinate su WGS84 u redoslijedu `[longitude, latitude]`.
- [ ] Razlikovati objekte i sjedišta. Zapise bez potvrđenih koordinata zadržati dostupnima u listi, uz oznaku da nemaju prikaz na karti. Odrediti kriterije filtara i ponašanje ograničenih/paginiranih odgovora.

**Gotovo kada:** postoji mali dokumentirani primjer odgovora i jasan odnos između broja rezultata u listi i broja točaka na karti.

### d) Izložiti stvarne objekte iz baze

- [ ] Dodati DAO upit i servis za aktivne objekte i njihove koordinate, uz provjeru grada, vrste pružatelja i opcionalnog prostornog obuhvata. Zadržati tok API → service → Unit of Work → DAO.
- [ ] Dodati tanki HTTP adapter za frontend, primjerice planiranu rutu `GET /api/locations`, te razvojni Vite proxy. Ne vezati kartu uz parser razgovornog upita niti RAG. Potpune rezultate za analizu dohvaćati neovisno o paginaciji liste i trenutačnom pogledu karte.

**Gotovo kada:** frontend može dohvatiti GeoJSON stvarnih objekata iz aktivnih snimki; testovi potvrđuju da nema duplikata ni sjedišta prikazanih kao objekti.

### e) Nacrtati objekte i njihove detalje

- [ ] Dodati GeoJSON izvor i slojeve točaka, s razlikovanjem vrsta pružatelja i grupiranjem točaka pri udaljenom pogledu. Slojeve dodavati nakon učitavanja stila; ako uvedemo promjenu stila, ponovno ih povezati na `style.load`.
- [ ] Klik na objekt otvara panel s nazivom, adresom i izvorima; klik na grupu približava kartu. Tekst podataka prikazivati kroz React ili sigurne DOM metode.

**Gotovo kada:** moguće je pronaći stvarni objekt, otvoriti njegove podatke i provjeriti izvor. Pogreška dohvata i prazan rezultat imaju zasebna stanja.

### f) Povezati kartu, listu i osnovne filtre

- [ ] Dodati zajedničko stanje odabranog `location_id` i filtara grada, naziva i vrste pružatelja. Odabir u listi ističe objekt na karti; odabir na karti otvara odgovarajući zapis u listi.
- [ ] Filtriranje ažurira podatke bez ponovne inicijalizacije karte. Zanemariti ili otkazati zastarjele zahtjeve; razlikovati učitavanje, prazne rezultate i pogreške. Omogućiti pristup detaljima tipkovnicom kroz listu.

**Gotovo kada:** lista i karta primjenjuju iste kriterije, uz objašnjen izostanak zapisa bez koordinata. Nepoznata dobna prikladnost ostaje označena kao nepoznata.

**Prva prekretnica — a–f:** upotrebljiva karta i pretraga stvarnih vrtićkih objekata.

### g) Dopuniti i provjeriti lokacije Geoportal izvorom

- [ ] Potvrditi shemu, koordinatni sustav i uvjete korištenja konkretnog Geoportal resursa; proširiti postojeći uvoz umjesto stvaranja paralelnog imenika.
- [ ] Povezati zapise sa stabilnim objektima, sačuvati podrijetlo dopunjenih atributa i izdvojiti nesigurna podudaranja. Evidentirati broj povezanih, nepovezanih i neupotrebljivih lokacija.

**Gotovo kada:** ponovljeni uvoz ne umnožava objekte i može se objasniti izvor svake prihvaćene koordinate. Neriješene zapise jasno prikazujemo u izvještaju pokrivenosti.

### h) Dodati granice gradskih četvrti

- [ ] Odabrati službeni izvor i licencu, uvesti granice sa stabilnim šiframa i pretvoriti geometrije u WGS84 za prikaz. Migracijom dodati potrebnu pohranu i provjeriti valjanost geometrija.
- [ ] Prostorno povezati objekte s četvrtima, uz određeno pravilo za rubne slučajeve. Prikazati poligone i omogućiti odabir četvrti; neslaganje s tekstualnom četvrti iz imenika označiti za pregled.

**Gotovo kada:** klik otvara pravu četvrt i popis pripadajućih objekata; objekti izvan granica i rubna neslaganja nisu tiho odbačeni.

### i) Povezati demografiju i prikazati pokazatelje

- [ ] Odabrati konkretnu DZS tablicu i dostupne dobne skupine; povezati je sa šiframa i granicama iste prostorne razine. Pohraniti godinu, jedinicu mjere, izvor i datum dohvata.
- [ ] Dodati obojene poligone prema broju djece, legendu i detalje četvrti. Broj objekata prikazati odvojeno; nedostajuća vrijednost ima posebnu oznaku. Dobni odabir nuditi samo za skupine koje izvor stvarno sadrži.

**Gotovo kada:** svaki broj vodi do odgovarajućeg izvora i godine, a nepoznati podaci razlikuju se od nule. Broj djece po četvrti nije prikazan kao izmjerena raspodjela po ulicama.

### j) Izračunati početnu prostornu dostupnost

- [ ] Za svaku četvrt odrediti i dokumentirati reprezentativnu točku. U backendu izračunati zračnu udaljenost do najbližeg potvrđenog objekta koristeći PostGIS `geography`; uključiti objekte preko granica četvrti.
- [ ] Vratiti korištenu točku, najbliži objekt, udaljenost u metrima, odabrani prag i oznaku metode. Sačuvati identitet snimki i kriterije analize. U prikazu odvojiti demografiju, broj objekata i dostupnost.

**Gotovo kada:** rezultat je ponovljiv za iste ulaze i označen kao aproksimacija iz reprezentativne točke. Bez objekata udaljenost je nedostupna; ne vraćamo nulu ili izmišljeno vrijeme putovanja.

### k) Omogućiti postavljanje nove lokacije

- [ ] Dodati način „Predloži lokaciju”: korisnik klikne kartu, pomakne jedan poseban marker i po potrebi ukloni prijedlog. Dodati tekstualni unos koordinata kao alternativu kliku.
- [ ] Provjeriti koordinate i dopušteni obuhvat Zagreba. Hipotetsku lokaciju držati u stanju scenarija, odvojeno od trajnih izvornih objekata.

**Gotovo kada:** lokaciju je moguće postaviti, pomaknuti i ukloniti bez promjene imenika. Odabir postojećeg objekta i postavljanje prijedloga ne aktiviraju se istim klikom.

### l) Usporediti postojeće stanje i scenarij

- [ ] Dodati servis i transportni ugovor za usporedbu, primjerice planirani `POST /api/accessibility/scenarios`. Koristiti iste reprezentativne točke, filtre, metodu i snimke podataka za oba stanja.
- [ ] Za svaku četvrt izračunati `nova_udaljenost = min(početna_udaljenost, udaljenost_do_kandidata)` kada početni rezultat postoji. Prikazati početnu udaljenost, novu udaljenost i smanjenje u metrima, uz zaseban prikaz prelaska odabranog praga. Kada početni rezultat nedostaje, razliku označiti kao neusporedivu.

**Gotovo kada:** dodavanje kandidata ne povećava minimalnu udaljenost; područja s bližim postojećim objektom ostaju nepromijenjena. Uklanjanje scenarija vraća početno stanje. Promjena ulaza ne dopušta prikaz zastarjelog rezultata kao aktualnog.

### m) Pripremiti provjerljivu demonstraciju prve verzije

- [ ] Odabrati reproducibilnu snimku stvarnih objekata, granica i demografije te demonstracijski kandidat. Upute moraju omogućiti ponavljanje uvoza i usporedbe; uz rezultat prikazati pokrivenost, reference izvora, datume i ograničenja.
- [ ] Pokrenuti backend testove i frontend `build`/`lint`, dodati ciljane provjere prostornih izračuna i scenarija te ručno provjeriti kartu u stvarnom pregledniku. Mock Mapboxa provjerava povezivanje i cleanup, ali ne dokazuje ispravan WebGL prikaz. Provjeriti i nevažeći token, nedostupnu podlogu/API, prazne podatke, mobitel i tipkovnicu.

**Gotovo kada:** demonstracija pokazuje cijeli tijek od objekata i četvrti do prije/poslije usporedbe, s rezultatima iz podataka. Rezultate možemo provjeriti i kroz tekstualni prikaz.

**Druga prekretnica — g–m:** prva analitička verzija opisana u ovom planu. Ako službeni demografski ili prostorni izvor nije dostupan pod prihvatljivim uvjetima, karta a–f ostaje samostalno upotrebljiva, a analitičku prekretnicu ne označavamo dovršenom.

### n) Povezati dovršeni tijek s MCP appom

- [ ] Kada postoje MCP transport i HTML pakiranje, izložiti dohvat objekata i usporedbu scenarija kroz iste servise. Prenositi strukturirane ulaze i rezultate umjesto dupliciranja izračuna u razgovornom sloju.
- [ ] Ugraditi postojeći React prikaz u MCP app i provjeriti pravila dopuštenih mrežnih odredišta/CSP-a, Mapbox worker, učitavanje stilova, fontova i podloge u stvarnom hostu.

**Gotovo kada:** isti upit daje iste rezultate u web prikazu i MCP appu, a karta je provjerena u oba okruženja. Ovaj korak slijedi nakon lokalne web demonstracije.

### o) Naknadno dodati prometne rute i naprednije analize

- [ ] Zasebno uvesti pješačku mrežu/routing, pa javni prijevoz uz ZET GTFS, datum i vrijeme polaska. Prije izbora pružatelja provjeriti pokrivenost, uvjete i trošak. Mapbox podloga sama ne izračunava dostupnost javnim prijevozom.
- [ ] Pretragu adresa, više kandidata i kapacitete dodavati kao zasebna proširenja. Za pretragu vlastitih objekata koristiti naš API; Mapbox Search uvoditi tek za potvrđenu potrebu pronalaska adrese i uz provjeru uvjeta korištenja rezultata.

**Gotovo kada:** svaki dodatni način ima vlastitu dokumentiranu metodu i ulaze; zračna udaljenost se ne predstavlja kao trajanje putovanja.

### Tehničke reference za provedbu

- [Lokalni Mapbox skill](.agents/skills/mapbox-web-integration-patterns/SKILL.md) i [konfiguracija tokena](.agents/skills/mapbox-web-integration-patterns/references/token-management.md).
- [Mapbox GL JS API](https://docs.mapbox.com/mapbox-gl-js/api/) — lifecycle, izvori, slojevi i ažuriranje karte.
- [Službeni primjer grupiranja GeoJSON točaka](https://docs.mapbox.com/mapbox-gl-js/example/cluster/) — podloga za prikaz objekata u koraku e.
- [Službeni primjer pomicanja točke](https://docs.mapbox.com/mapbox-gl-js/example/drag-a-point/) — referenca za interakciju kandidata u koraku k.
- [Upravljanje Mapbox tokenima](https://docs.mapbox.com/accounts/guides/tokens/) — javni tokeni i ograničenja URL-ova.
