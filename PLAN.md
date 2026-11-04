# PLAN — KIDSic

## Gdje gradu najviše nedostaje dostupnih vrtićkih usluga?

Status: implementirani koraci a–f (karta, lista i filtri); analitički slojevi i scenariji ostaju planirani. Početni obuhvat je Grad Zagreb. Funkcionalnost nadograđuje postojeći uvoz imenika ustanova i gradskih objekata.

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

Obuhvat: prethodno opisana analiza dostupnosti vrtića u Zagrebu. Prvo gradimo upotrebljivu kartu objekata, potom analitičke slojeve i usporedbu jedne nove lokacije. Svaki korak može biti zasebna promjena koju provjeravamo prije nastavka. Koraci a–f su implementirani i provjereni; koraci g–o ostaju planirani.

### Polazište i Mapbox referenca

Sljedeći nalazi opisuju stanje prije implementacije a–f; dovršene stavke i provjere zabilježene su ispod.

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
- Lokalna baza, pokrivenost koordinatama i javni Mapbox token provjereni su tijekom a–f. U drugim okruženjima provjeriti njihove aktivne snimke i konfiguraciju; ne popunjavati nedostatke izmišljenim podacima.
- U koraku d odabrani su Starlette i Uvicorn, uz DTO neovisan o transportu. MCP host i njegova pravila učitavanja potvrditi u koraku n.
- Prag dostupnosti i izbor reprezentativne točke moraju biti dokumentirane postavke, a ne predstavljeni kao službeni standard. Promjena metode znači ponovno računanje oba uspoređivana stanja.

### a) Pripremiti Mapbox konfiguraciju

- [x] Dodati `mapbox-gl` v3 i konfiguraciju javnog `VITE_MAPBOX_ACCESS_TOKEN` tokena, uz predložak bez stvarne vrijednosti. Token za preglednik je javno vidljiv i kada dolazi iz `.env`; koristiti namjenski javni token s ograničenjima URL-ova za dopuštena okruženja.
- [x] Uskladiti Vite `envDir` s lokacijom `frontend/.env.local` i `frontend/.env.example`, jer je trenutačni Vite `root` postavljen na `src/views`. Dodati TypeScript tip varijable i poruku kada token nedostaje.

**Gotovo kada:** aplikacija učitava konfiguraciju iz očekivane mape; nedostatak tokena daje razumljivu poruku.

### b) Prikazati osnovnu kartu Zagreba

- [x] Dodati izdvojenu `KindergartenMap` komponentu u zajednički frontend kod i otvoriti je iz glavnog prikaza. Postaviti početni pogled na Zagreb, visinu spremnika, navigacijske kontrole i vidljivu atribuciju.
- [x] Primijeniti lifecycle obrazac iz skilla, obraditi pogreške učitavanja i nepodržan WebGL te pozvati `resize()` kada se promijeni veličina panela. Kartu inicijalizirati jednom po montiranju; cleanup mora raditi i u React StrictModeu.

**Gotovo kada:** karta radi na desktopu i mobitelu, a ponovno otvaranje prikaza ne ostavlja dodatne instance ni listenere.

### c) Definirati ugovor podataka za kartu

- [x] Dogovoriti DTO i GeoJSON `FeatureCollection`: stabilni `location_id`, `kindergarten_id`, naziv objekta, adresa, vrsta pružatelja, četvrt kada je poznata te podrijetlo i datumi. Koordinate su WGS84 u redoslijedu `[longitude, latitude]`.
- [x] Razlikovati objekte i sjedišta. Zapise bez potvrđenih koordinata zadržati dostupnima u listi, uz oznaku da nemaju prikaz na karti. Odrediti kriterije filtara i ponašanje ograničenih/paginiranih odgovora.

**Gotovo kada:** postoji mali dokumentirani primjer odgovora i jasan odnos između broja rezultata u listi i broja točaka na karti.

### d) Izložiti stvarne objekte iz baze

- [x] Dodati DAO upit i servis za aktivne objekte i njihove koordinate, uz provjeru grada, vrste pružatelja i opcionalnog prostornog obuhvata. Zadržati tok API → service → Unit of Work → DAO.
- [x] Dodati tanki HTTP adapter za frontend, primjerice planiranu rutu `GET /api/locations`, te razvojni Vite proxy. Ne vezati kartu uz parser razgovornog upita niti RAG. Potpune rezultate za analizu dohvaćati neovisno o paginaciji liste i trenutačnom pogledu karte.

**Gotovo kada:** frontend može dohvatiti GeoJSON stvarnih objekata iz aktivnih snimki; testovi potvrđuju da nema duplikata ni sjedišta prikazanih kao objekti.

### e) Nacrtati objekte i njihove detalje

- [x] Dodati GeoJSON izvor i slojeve točaka, s razlikovanjem vrsta pružatelja i grupiranjem točaka pri udaljenom pogledu. Slojeve dodavati nakon učitavanja stila; ako uvedemo promjenu stila, ponovno ih povezati na `style.load`.
- [x] Klik na objekt otvara panel s nazivom, adresom i izvorima; klik na grupu približava kartu. Tekst podataka prikazivati kroz React ili sigurne DOM metode.

**Gotovo kada:** moguće je pronaći stvarni objekt, otvoriti njegove podatke i provjeriti izvor. Pogreška dohvata i prazan rezultat imaju zasebna stanja.

### f) Povezati kartu, listu i osnovne filtre

- [x] Dodati zajedničko stanje odabranog `location_id` i filtara grada, naziva i vrste pružatelja. Odabir u listi ističe objekt na karti; odabir na karti otvara odgovarajući zapis u listi.
- [x] Filtriranje ažurira podatke bez ponovne inicijalizacije karte. Zanemariti ili otkazati zastarjele zahtjeve; razlikovati učitavanje, prazne rezultate i pogreške. Omogućiti pristup detaljima tipkovnicom kroz listu.

**Gotovo kada:** lista i karta primjenjuju iste kriterije, uz objašnjen izostanak zapisa bez koordinata. Nepoznata dobna prikladnost ostaje označena kao nepoznata.

**Prva prekretnica — a–f:** upotrebljiva karta i pretraga stvarnih vrtićkih objekata.

Potvrđeno 3. studenoga 2026.: 24 frontend testa, 52 backend testa nad zasebnom PostgreSQL bazom, frontend build i lint. Tri neobavezna testa postojećeg CKAN simulatora su preskočena. Preglednik s javnim Mapbox tokenom potvrđuje stvarnu podlogu, grupiranje, odabir i filtre, desktop prikaze 1366×768 i 1024×768 te mobilni prikaz 390×844. Lokalna aktivna snimka za Zagreb daje 371 točku i 90 zasebno označenih sjedišta bez točke. Dodane regresijske provjere pokrivaju zadržane starije koordinate, zastarjele odgovore i Mapbox događaje bez renderiranog UUID identifikatora.

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

## Prerada prikaza vrtića prema vizualnoj referenci

Status: UI-a–f dovršeni prema korigiranom zahtjevu za ugrađeni MCP prikaz. Ovo je zasebna dorada nakon osnovnih a–f; analitički koraci g–o ostaju zaseban plan.

### Zahtjev i nalazi

Korigirani zahtjev: prikaz za MCP app sadrži kartu, pomične kartice, detalje i fullscreen kontrolu. Uklonjeni su navigacija, branding, veliki naslov i podnožje zasebne stranice te legenda i filtri karte. Lokalni Vite ostaje razvojni pregled; MCP transport i HTML pakiranje pripadaju koraku n.

Referenca je korisnikova slika `Screenshot 2026-11-03 at 10.56.27.png`: zaobljeni okvir karte, naglašene točke, bijele kartice preko donjeg dijela karte, djelomično vidljiva sljedeća kartica i kružni gumb s ikonom proširenja u gornjem desnom kutu. Kartice trebaju biti vodoravno pomične, a klik na ikonu treba otvoriti prikaz preko cijelog ekrana.

Polazište prije dorade: `frontend/src/views/welcome/Welcome.tsx` držao je filtre i zajednički odabir te povezuje `useLocations`, `LocationResults` i `KindergartenMap`. `LocationResults.tsx` trenutačno prikazuje okomitu listu i otvorene detalje unutar retka. `KindergartenMap.tsx` upravlja jednom instancom karte i promjenama veličine preko `ResizeObserver`, a `LocationLayer.ts` rješava točke, grupe i odabir prema stabilnom `properties.location_id`. Te funkcije treba prilagoditi novom rasporedu, uz očuvanje postojeće logike dohvata i zaštite od zastarjelih odgovora.

Ugovor `frontend/src/shared/locations/types.ts` nema fotografije vrtića. Kartica zato u početnoj izvedbi koristi neutralnu sličicu/ikonu; stvarnu fotografiju može dobiti tek iz potvrđenog izvora s dopuštenim korištenjem. Glavni sadržaj kartice bit će naziv objekta, adresa, vrsta pružatelja i četvrt kada je poznata. Fotografije kuća, cijene i oznake iz primjera nisu podaci o vrtićima.

### Razmotreni pristupi i odabir

1. **Zajednički okvir karte i kartica, uz izvorno vodoravno pomicanje — odabrano.** CSS `overflow-x` i scroll snap daju pomicanje dodirom i trackpadom; gumbi omogućuju pomicanje mišem i tipkovnicom. Ne treba nova carousel biblioteka. Odvojena komponenta okvira upravlja proširenjem cijelog sadržaja. Glavni rizici su preklapanje kontrola i sukob gesti karte i kartica; rješavaju se jasnim zonama interakcije i provjerom u pregledniku.
2. **Carousel biblioteka i zasebna kopija karte u proširenom prikazu.** Biblioteka može olakšati složene animacije, ali dodaje ovisnost, dok druga karta traži usklađivanje kamere, odabira i lifecyclea. Za ovaj prikaz to donosi dodatne točke kvara bez potrebne korisničke koristi.

Za proširenje koristiti vlastiti gumb na zajedničkom okviru i Fullscreen API. Time kartice i detalji ostaju u istom fullscreen elementu. U pregledniku koji ga ne podržava ili odbije zahtjev koristiti prošireni prikaz preko cijelog prozora, uz jasan izlaz. Standardni Mapbox FullscreenControl razmotren je kao alternativa, ali vlastiti gumb jednostavnije pokriva traženi izgled i zamjensko ponašanje.

### UI-a) Postaviti kartu kao glavni prikaz

- [x] U `Welcome.tsx` zamijeniti raspored bočne liste i karte zajedničkom komponentom, primjerice `KindergartenExplorer`, koja sadrži kartu i sve njene preklopne elemente. Okvir prilagoditi dostupnoj veličini MCP prikaza, uz malu vanjsku marginu i bez navigacije, naslova, podnožja, legende ili filtara.
- [x] U `welcome.css` i `map.css` definirati zaobljen okvir, jasno određenu visinu i slojeve prikaza. Smjer preuzeti iz reference: bijele površine, tamni tekst, crveni markeri s bijelim rubom i naglašen odabrani objekt. Vrstu pružatelja zadržati kao tekst na kartici; broj na grupi označava broj objekata.

**Gotovo kada:** karta zauzima glavni prostor, a kontrole i budući red kartica imaju svoja mjesta na desktopu i mobitelu. Promjena rasporeda ne stvara novu Mapbox instancu.

### UI-b) Izdvojiti karticu vrtića

- [x] Dodati `LocationCard.tsx` s malom sličicom lijevo i sažetkom desno: naziv, adresa, vrsta pružatelja i dostupna četvrt. Koristiti podatke iz postojećeg API-ja, uz oznake za sjedišta i objekte bez koordinata.
- [x] Kartici dati bijelu podlogu, veće zaobljenje i suptilnu sjenu prema referenci. Naziv omogućuje odabir, a zaseban jasno označen gumb otvara detalje; izbjegavati ugniježđene gumbe.

**Gotovo kada:** kartica radi s dugim nazivima i nedostajućim podacima, bez izmišljenih fotografija, kapaciteta ili slobodnih mjesta.

### UI-c) Omogućiti vodoravno pomicanje kartica

- [x] Dodati `LocationCarousel.tsx` kao red preko donjeg dijela karte: `overflow-x: auto`, kartice koje se ne skupljaju i scroll snap. Na manjim ekranima ostaviti vidljiv dio sljedeće kartice kao u referenci.
- [x] Omogućiti swipe na dodirnom zaslonu, pomicanje trackpadom te gumbe „Prethodni vrtić” i „Sljedeći vrtić”. Gumbi pomiču red do prethodne/sljedeće kartice i imaju ispravna stanja na početku i kraju; Tab i Enter omogućuju pristup svakoj kartici. Poštovati postavku smanjenog kretanja.

**Gotovo kada:** sve rezultate možemo pregledati pomicanjem udesno i vratiti se ulijevo; pomiče se samo red kartica, a stranica nema vodoravni overflow. Geste nad karticama ne pomiču kartu ispod njih.

### UI-d) Povezati kartice, markere i detalje

- [x] Zadržati zajednički `selectedId` u postojećem vlasniku stanja. Klik na karticu ističe objekt i približava kartu; klik na marker dovodi odgovarajuću karticu u vidljivi dio reda. Programsko pomicanje ograničiti na carousel, bez pomicanja cijele stranice.
- [x] Samo pregledavanje kartica pomicanjem ne mijenja odabir ni kameru. `LocationDetails.tsx` prikazivati u zasebnom panelu unutar zajedničkog okvira, kako dugi izvori ne bi povećavali visinu kartica. Sjedište otvara detalje bez stvaranja markera. Novi rezultati zamjenjuju sadržaj reda; nepoznate lokacije ostaju dostupne kao kartice.

**Gotovo kada:** odabir radi u oba smjera, zatvaranje detalja vraća fokus na pripadajuću kontrolu, a postojeća zaštita od zastarjelih zahtjeva i kasnih odgovora grupiranja ostaje ispravna.

### UI-e) Dodati prikaz preko cijelog ekrana

- [x] Dodati kružni gumb u gornjem desnom kutu sa smislenim nazivom „Prikaži preko cijelog ekrana” / „Vrati prikaz”. Fullscreen zahtjev pokrenuti izravno klikom nad cijelim zajedničkim okvirom, a stanje uskladiti s `fullscreenchange` i stvarnim `document.fullscreenElement`.
- [x] Podržati izlazak gumbom i tipkom Escape. Kada izvorni fullscreen nije dostupan, prikaz proširiti preko prozora pomoću `position: fixed`; tada privremeno onemogućiti pomicanje pozadine, ograničiti fokus na prošireni prikaz i pri izlasku vratiti prethodno stanje i fokus. Postojeći `ResizeObserver` mora prilagoditi kartu pri ulasku i izlasku.

**Gotovo kada:** karta, kartice i otvoreni detalji ostaju dostupni u proširenom prikazu. Odabir, položaj reda i kamera ostaju očuvani; nema druge karte ni ponovnog dohvata samo zbog proširenja. Nakon odbijenog zahtjeva gumb ne ostaje u lažnom fullscreen stanju.

### UI-f) Uskladiti kontrole i mobilni prikaz

- [x] Premjestiti postojeće zoom kontrole tako da se ne sudaraju s ikonom proširenja. Ukloniti legendu i filtre iz ugrađenog prikaza. Sačuvati vidljivu Mapbox/OSM atribuciju, uz prostor ispod kartica i sigurne rubove mobilnog uređaja.
- [x] Prilagoditi širinu kartica i visinu okvira manjim ekranima, landscape prikazu i promjeni veličine prozora. Interaktivni slojevi zauzimaju samo potrebnu površinu, tako da ostatak karte prima geste. Detalji imaju dostupan gumb za zatvaranje i pravilno upravljanje fokusom.

**Gotovo kada:** kartice ne prekrivaju ključne kontrole i atribuciju, fullscreen ikona je uvijek dostupna, a kartu i kartice možemo koristiti na uskom ekranu bez povećavanja stranice.

### UI-g) Prilagoditi prazna stanja i pogreške

- [ ] Premjestiti postojeće poruke za učitavanje, prazne rezultate, ponovni pokušaj i nepoznate koordinate u novi raspored. Ako podloga nije dostupna, kartice i detalji i dalje prikazuju stvarne rezultate API-ja.
- [ ] Broj rezultata ostaviti dostupan čitačima zaslona, bez dodatnog vizualnog alatnog reda. Kod nula rezultata ne ostaviti stare markere ili kartice; kod jednog rezultata onemogućiti nepotrebne gumbe pomicanja.

**Gotovo kada:** promjena izgleda čuva razliku između praznog rezultata, nedostupnog API-ja i nedostupne podloge, uz razumljiv sljedeći korak za korisnika.

### UI-h) Provjeriti i spremati u male commitove

- [ ] Prilagoditi postojeće `LocationApp.test.tsx` i `KindergartenMap.test.tsx`; dodati ciljane provjere carousela i fullscreen ponašanja: klikovi u oba smjera, marker–kartica odabir, izostanak navigacije, legende i filtara, odbijeni fullscreen zahtjev, Escape, vraćanje fokusa i uklanjanje listenera.
- [ ] Pokrenuti frontend testove, build i lint. U stvarnom pregledniku potvrditi pomicanje, fullscreen ulaz/izlaz, očuvanje kamere i ispravne dimenzije na desktopu, mobitelu i u landscapeu. Usporediti snimke s referencom, posebno položaj kartica, vidljivost sljedeće kartice i ikonu gore desno.

**Gotovo kada:** cijeli tijek radi na stvarnim podacima i nema regresija dohvata, izvora ili Mapbox lifecyclea. Svaki korak spremati kao zaseban pregledan Conventional Commit; usko povezane prilagodbe testova uključiti uz odgovarajuću promjenu.

### Pretpostavke i otvorena pitanja ove dorade

- „Preko cijelog ekrana” obuhvaća cijeli prikaz karte s karticama i kontrolama. Izvorni fullscreen koristiti gdje ga preglednik dopušta; prikaz preko prozora je zamjenska mogućnost.
- Pomicanje kartica znači pregledavanje rezultata u oba smjera; odabir se mijenja klikom ili aktivacijom kartice, a ne svakim pomakom reda.
- Fotografije trenutačno nisu raspoložive u API-ju. Njihovo pribavljanje ostaje zasebna nadogradnja; ovaj plan ne zahtijeva novu backend rutu ni promjenu baze.
- Ponašanje Fullscreen API-ja i gesta treba provjeriti u ciljnom pregledniku, osobito na mobitelu i kasnije u MCP hostu. Kontrole i detalji moraju biti potomci fullscreen okvira; panel izvan njega može nestati iz proširenog prikaza.

### Reference za ovu doradu

- Korisnikova priložena snimka zaslona — raspored karte, kartica i gumba proširenja.
- [Lokalni Mapbox skill](.agents/skills/mapbox-web-integration-patterns/SKILL.md) — očuvanje jedne instance, lifecycle i promjena veličine.
- [MDN: requestFullscreen](https://developer.mozilla.org/en-US/docs/Web/API/Element/requestFullscreen) i [fullscreenchange](https://developer.mozilla.org/en-US/docs/Web/API/Document/fullscreenchange_event) — zahtjev, pogreške i usklađivanje stanja.
- [MDN: scroll-snap-type](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/scroll-snap-type) — vodoravno zaustavljanje na karticama.
- [Mapbox: FullscreenControl](https://docs.mapbox.com/mapbox-gl-js/api/markers/#fullscreencontrol) — uspoređeni ugrađeni pristup.

### Zabilježene provjere UI dorade

Dana 3. studenoga 2026. prolazi 36 frontend testova, build i lint. Stvarni preglednik potvrđuje pomicanje kartica, odabir i detalje, native fullscreen s gumbom i Escapeom te očuvanje pomaka reda i odabranog objekta. Provjereni su uski prikaz 390×844 i rotacija u 568×320 bez ponovnog učitavanja; kamera pri promjeni veličine osvježava samo padding i zadržava središte i zoom. Korigirani UI nema navigaciju, legendu ni filtre.

## MCP prikaz vrtića po obaveznom gradu (3. studenoga 2026.)

### Istraživanje i odluka

Postojeći HTTP API (`api/locations.py`) koristi `LocationService` i potpuni GeoJSON,
a `Welcome.tsx` dohvaća početni Zagreb. MCP transport i povezani HTML resurs još
ne postoje. `LocationQuery` smije zadržati HTTP default, ali MCP alat ne smije
naslijediti Zagreb kada korisnik nije naveo grad.

Uspoređene su dvije mogućnosti: povezati alat s vanjskim Vite URL-om ili poslužiti
samostalni HTML resurs kroz MCP. Vanjski URL zahtijeva dodatni hosting, CORS i
pristup API-ju iz sandboxa; odabran je samostalni HTML s rezultatima preko host
bridgea. Prikaz koristi postojeći explorer, bez zasebnog dohvata ili novih filtara.

Službeni MCP Apps obrazac povezuje alat preko `_meta.ui.resourceUri` s HTML-om
`text/html;profile=mcp-app`. Rezultati ulaze kroz `ui/notifications/tool-result`,
a fullscreen se traži od hosta kada je podržan. Reference:
https://developers.openai.com/plugins/build/chatgpt-ui i
https://modelcontextprotocol.io/extensions/apps/overview.

### Mali koraci

- [x] MCP-a: Dodati službeni Python MCP SDK i Streamable HTTP `/mcp` tvornicu s
  postojećim servisom i upravljanim životnim vijekom baze.
- [x] MCP-b: Registrirati read-only alat `prikazi_vrtice(city)` s obaveznim,
  nepraznim gradom, bez defaulta. Upute servera/alata nalažu pitanje za grad;
  nevaljan poziv ne smije čitati bazu. Rezultat je sažetak `{city, metadata}`, a potpuni GeoJSON u `_meta.locations`.
- [x] MCP-c: Povezati svaki poziv s istim UI resursom, uključujući prazan skup;
  poslužiti samostalni build i CSP za Mapbox. Pogreške servisa sanitizirati.
- [x] MCP-d: Dodati zaseban embedded ulaz i standardni MCP Apps bridge. Ne čitati
  `/api` ni pretpostaviti Zagreb. Očistiti zastarjele rezultate/odabir pri novom
  gradu; ponovni pokušaj koristi host alat. Sačuvati samostalni razvojni preview.
- [x] MCP-e: Dodati host fullscreen uz postojeći samostalni fullscreen te
  dokumentirati build, pokretanje i spajanje klijenta.
- [x] MCP-f: Provjeriti stvarni MCP initialize/tools/list/tools/call/resources/read,
  obavezan grad, prazne rezultate i kvar baze; frontend testove, lint, build te
  host bridge s ugrađenim HTML-om. Spremiti male Conventional Commitove.

### Granice i provjera

Server može jamčiti UI metapodatke za svaki poziv alata i odbiti izostavljen grad.
Generički AI klijent odlučuje hoće li pozvati alat i podržava li MCP Apps; njegove
odluke ne možemo nametnuti serverom. Upute eksplicitno nalažu ovaj alat za zahtjev
za prikaz vrtića te pitanje kada grad nedostaje. Stvarni ChatGPT prikaz traži
povezan dostupan server; lokalna provjera ne znači objavu ili povezivanje računa.
Bez potvrđenih koordinata kartice ostaju dostupne; podaci se ne izmišljaju.


### Završne provjere MCP integracije

Prolazi 41 frontend test (uključujući stvarni SDK postMessage handshake), lint,
samostalni build i MCP single-file build. Backend suite: 62 testa, 32 prolaze,
30 se preskače bez zasebne testne baze/CKAN simulatora; svih 7 novih MCP testova
prolazi preko službenog ClientSession i ASGI transporta.

Stvarni lokalni MCP endpoint na portu 8001 provjeren je nad razvojnom bazom:
Zagreb 461 rezultat (371 koordinata), Split 22 i Varaždin 14 (bez koordinata),
izmišljeni naziv grada 0 rezultata. Izostavljen grad vraća pojašnjenje. UI resurs
nema vanjske skripte ni stylesheet zahtjeve. Puni zagrebački odgovor je oko 1,12 MB,
pa su GeoJSON i izvori u `_meta.locations`, a sažetak za model oko 112 bajtova.

Vizualna provjera novog host prikaza nije dovršena: upravljanje preglednikom
onemogućeno je postavkom aplikacije. Postojeći standalone UI je ranije vizualno
provjeren; handshake i host fullscreen sada su provjereni testnim hostom. Stvarni
ChatGPT prikaz i njegove odluke o pozivu alata ostaju provjera nakon povezivanja
servera prema `MCP.md`; server nije automatski objavljen ni dodan u korisnikov račun.

## Tailwind CSS u oba frontend prikaza (3. studenoga 2026.)

Postoje dva Vite builda s različitim rootovima: razvojni/standalone
`vite.config.ts` i samostalni MCP HTML `vite.mcp.config.ts`. Oba ulaza uvoze
`src/shared/theme.css`; layout i kartice trenutačno koriste custom CSS.

Uspoređeni su službeni `@tailwindcss/vite` i PostCSS integracija. Odabran je Vite
plugin za oba builda jer ne zahtijeva dodatnu PostCSS konfiguraciju. Tailwind v4
ima CSS konfiguraciju teme. Koristit će se službeni odvojeni importi teme i
utility klasa bez Preflight reseta kako se ne bi promijenile postojeće Mapbox
kontrole, tipografija i stilovi. Eksplicitni `source('../')` u shared CSS-u
obuhvaća cijeli `src`, neovisno o dubini pojedinog Vite roota.

- [x] TW-a: Instalirati `tailwindcss` i `@tailwindcss/vite` te uključiti plugin u
  oba Vite builda.
- [x] TW-b: Izložiti postojeće boje kao Tailwind tokene i primijeniti utility
  klase na oba glavna prikaza i kartice. Ukloniti zamijenjene CSS deklaracije;
  specifični Mapbox i fullscreen stilovi ostaju postojeći.
- [x] TW-c: Pokrenuti postojeće testove, lint i oba builda. Provjeriti generirane
  utility klase u standalone CSS-u i MCP HTML-u bez vanjskih CSS zahtjeva.
- [x] TW-d: Dokumentirati način korištenja i spremiti male commitove.

Izgled ostaje isti; nisu zatraženi novi UI elementi ni shadcn/ui komponente.
Referenca: https://tailwindcss.com/docs/installation/using-vite i
https://tailwindcss.com/docs/preflight#disabling-preflight.


Tailwind 4.3.4: prolazi 41 frontend test, lint, standalone build i MCP single-file
build. Iz generiranih artefakata potvrđene su korištene layout/card/sr-only klase
te MCP HTML bez vanjskih skripti ili stylesheet zahtjeva. Lokalni MCP server na
8001 ponovno je pokrenut i kroz `resources/read` potvrđeno je da služi Tailwind
build. Nova vizualna provjera nije odrađena jer je upravljanje preglednikom
onemogućeno postavkom aplikacije; promijenjena pravila imaju iste vrijednosti
kao prethodni CSS.

## Kompaktne shadcn/ui kartice na karti

Referentna snimka prikazuje niži vodoravni red s više vidljivih kartica i kružnim
strelicama na rubovima. Sadašnja kartica ima širinu do 510 px i minimalnu visinu
188 px, uz dodatni red kontrola iznad. Nema stvarnih fotografija vrtića u izvorima,
pa ostaje neutralna sličica bez izmišljanja fotografija, ocjena i cijena.

Uspoređeni su zamjena cijelog carousela shadcn Carousel/Embla komponentom i
primjena shadcn Card/Button/Badge uz postojeći native scroll-snap. Odabrano je
zadržati provjereno pomicanje i odabir te zamijeniti kartice i gumbe službenim
shadcn komponentama: manje ovisnosti, očuvani fokus, touch i map-marker reveal.

- [x] SC-a: Dodati lokalni shadcn/ui config i službene Card/Button/Badge komponente
  iz @shadcn registra preko CLI-ja. Podesiti alias u TypeScriptu, oba Vite builda i
  testovima; spojiti semantičke tokene s postojećom temom bez reseta Mapbox stilova.
- [x] SC-b: Prekomponirati kartice s CardHeader/Title/Description/Content/Footer,
  manjom sličicom i kratkim retcima. Cilj širina oko 320 px, visina oko 132 px
  (ista visina u landscapeu radi poruke o koordinatama), uz više vidljivih kartica na desktopu.
- [x] SC-c: Premjestiti shadcn icon gumbe na lijevi/desni rub reda. Zadržati
  pristupačna imena, disabled rubove, reduced motion, keyboard i scroll-snap.
- [x] SC-d: Provjeriti postojeće interakcijske testove i oba builda/lint; provjeriti
  dimenzije u pregledniku ako je upravljanje dostupno. Osvježiti MCP build/server
  i spremiti manje commitove.

Reference: korisnikova snimka 2026-11-03 13.00.47 i službene stranice
https://ui.shadcn.com/docs/components/base/card,
https://ui.shadcn.com/docs/components/base/button,
https://ui.shadcn.com/docs/components/base/badge.


Shadcn CLI dodao je Card/Button/Badge u `src/shared/ui`; korištena je službena
Radix Slot primitiva umjesto cijelog Radix paketa. Kompaktne kartice su 132 px
visoke; širina je 320 px na desktopu i do 280 px na mobitelu. Zadržana je ista visina
u landscapeu da napomena o nepoznatim koordinatama i gumb za detalje ne budu
odrezani. Na vrlo uskom ekranu širina računa viewport, a ne sadržaj tracka nakon
paddinga, čime se izbjegava dvostruko sužavanje.

Neovisni pregled i završne provjere potvrđuju 41 frontend test, lint i oba builda;
7 MCP protokolnih testova prolazi nakon verzioniranja UI resursa na map-v2 zbog
host cachea. Ispravljeni su nedostajući --primary/--radius i odvojene boje muted
pozadine/teksta. Vizualna usporedba sa snimkom nije odrađena: Work postavke i dalje
onemogućuju upravljanje preglednikom. Lokalni MCP server osvježen je za pregled
u Inspectoru; korisnik treba ponovno otvoriti app nakon reconnecta.

## Uklanjanje dodatnog sadržaja kartica i pogleda detalja

Korisnik traži uklanjanje oznake pružatelja, napomene o sjedištu/koordinatama i
akcije „Detalji i izvori”, zajedno s cijelim panelom detalja. Izabrano je ukloniti
komponente, stanje i callbackove umjesto samo skrivanja elemenata CSS-om, tako da
odabir sjedišta više ne otvara zaseban pogled. Kartica zadržava naziv, adresu,
neutralnu sličicu i postojeći odabir; backend podaci i pravila crtanja oznaka se
ne mijenjaju.

- [x] Ukloniti polja i akciju iz Card kompozicije te details props/state/panel i
  pripadajući neupotrijebljeni CSS.
- [x] Prilagoditi interakcijske provjere: bez detalja i automatskog otvaranja za
  sjedište, uz očuvani odabir, pomicanje i fullscreen. Ukloniti testove izbrisanog
  UI panela; izvori ostaju u backend ugovoru.
- [x] Provjeriti testove/lint/build, verzionirati UI resurs radi cachea i osvježiti
  lokalni MCP server. Spremiti manji commit.

Provjereno: 39 frontend testova, lint, standalone i MCP build te 7 MCP testova
prolaze. Testovi potvrđuju da ni odabir sjedišta ne otvara detalje i da nema
uklonjenih oznaka/akcija, uz očuvani fullscreen i pomicanje. Dva testa uklonjenog
UI panela izbrisana su zajedno s komponentom. UI resurs je map-v3 radi cachea.

## Klik na cijelu karticu

Jedan nativni shadcn Button pokriva cijelu relativno pozicioniranu karticu, a
sličica i tekst ne presreću pokazivač. Time se zadržavaju jedan fokusni korak,
aria-pressed i izvorno Enter/Space ponašanje, bez dodatnih click callbackova ili
ugniježđenih gumba. Hover podloga je iza teksta; puni naziv/adresa dostupni su i
na title atributu gumba. Dimenzije i pomicanje kartica ostaju isti.

Prolazi 39 frontend testova (dopunjena provjera Space aktivacije), lint, oba
builda i 7 MCP testova. UI resurs map-v4 osvježava host cache.

## Reorganizacija Python arhitekture — 2026-11-03

### Istraživanje i cilj

Referenca je GitHub HEAD FOIHirelooma `8ba897db799e993aa43c7d488879efb3870218f2`
(provjeren preko `git ls-remote`). Lokalni checkout `438886f` razlikuje se;
referentne datoteke pregledane su i kroz `git show` na GitHub reviziji.
Primjenjivi obrasci vidljivi su u kodu, a nisu zaseban pronađeni pravilnik:

- `api/tool_provider.py`, `api/mcp_server.py`: klase grupa alata i vlasnik transporta.
- `services/concrete/source_feed_registration.py`: odvojeni planner i servis.
- `services/concrete/hzz_feed_parser.py`: parser s malim javnim sučeljem.
- `factories/source_feed_registration.py`, `services/dependency.py`: sastavljanje
  implementacija odvojeno od poslovnih odluka, uz caller-owned resurse.
- `dao/interfaces`, `dao/concrete`, `db/uow/base.py`: ugovori repozitorija,
  implementacije i transakcijski opseg.

KIDSic već ima iste osnovne pakete. Promjena naziva svih paketa ne bi riješila
spojene odgovornosti: normalizator bira shemu i parsira sve izvore, MCP factory
registrira alate, čita HTML i upravlja resursima kroz zatvaranja, parser upita
učitava kataloge iz baze, a HTTP sloj poznaje asyncpg iznimke. Ugovor i konkretna
implementacija pisaćeg UoW-a nalaze se u istom modulu. Početno stanje: 71 Python
test, 68 prošlo i tri opcionalna testa preskočena.

### Razmotreni pristupi

1. Potpuna zamjena paketa s `presentation/application/domain/infrastructure`:
   jasna nova taksonomija, ali velika migracija importova i slabija sličnost
   FOIHireloomu bez dodatne koristi za postojeće jednostavne tokove.
2. Zadržati FOIHireloom raspored i razdvojiti stvarne odgovornosti klasama:
   manji rizik, postojeći ulazi ostaju dostupni, a ovisnosti i zamjenjive
   strategije postaju izričite. Odabran je ovaj pristup.

### Odabrana implementacija

- Prezentacija: `api` (HTTP/MCP) i `commands`; bez SQL-a ili upravljanja driverom.
  MCP razdvojiti na klasu transporta, grupu lokacijskih alata i UI resurs.
  Postojeći `KIDSic.mcp.server:create_app` zadržati kao kompatibilni ulaz.
- Poslovni sloj: `services/interfaces` i `services/concrete`; izdvojiti planner,
  normalizator s ubrizganim parserima za nacionalni imenik, Zagreb i dadilje,
  te parser upita koji prima podatke kataloga umjesto repozitorija.
- Podaci: `dao/interfaces`, `dao/concrete`, `integrations` i `db/uow`;
  ugovor pisaćeg UoW-a odvojiti od asyncpg implementacije, a driver pogreške
  pretvoriti u `PersistenceError` prije povratka prema servisu/API-ju.
- `factories` sastavlja konkretne parser strategije i servise; `DependencyService`
  upravlja životnim vijekom HTTP klijenta i poola. DTO-i ostaju podaci.
- Sačuvati postojeće SQL upite, tablice, mapiranja, transakcijsku atomarnost,
  filtriranje RAG-a, city-required MCP ugovor, kompresiju i UI metapodatke.
  Nisu potrebne migracije baze ni ponovni uvoz podataka.

### Otvorena pitanja i provjera

Nema blokirajućih pitanja. Refaktor je ograničen na postojeće funkcionalnosti;
referenca nije razlog za uvođenje SQLAlchemy ORM-a, FastMCP-a ili eksplicitnog
commita koji bi mijenjao postojeće ponašanje. Čisti pomoćni izračuni mogu ostati
funkcije; nove klase moraju imati stvarnu ulogu i mogućnost zasebne provjere.
Provjeriti postojeće i nove testove parser zamjenjivosti, slojnih ovisnosti,
životnog vijeka i protokola. Zatim pokrenuti puni Python skup na odvojenoj
migriranoj testnoj bazi te stvarni read-only MCP poziv za Varaždin (33 lokacije).

### Rezultat i završna provjera

Implementirani su `api/mcp_server.py`, `api/location_tools.py`,
`api/apps/map_resource.py`, `services/concrete/parsers`,
`source_normalizer.py`, `source_planner.py` i `db/uow/asyncpg_source.py`.
`RequestParser` prima kataloške vrijednosti; servisi/factories imaju tipizirane
UoW ovisnosti. Stari MCP i normalizacijski ulazi ostaju kompatibilni adapteri.
PostgreSQL iznimke pri otvaranju, radu i zatvaranju transakcije pretvaraju se
u `PersistenceError`, uz rollback/release i očuvan uzrok.

Završni skup: 79 testova, 76 prošlo, tri postojeća opcionalna HTTP simulation
testa preskočena. Provjereno je dodavanje novog parsera bez izmjene servisa,
smjer importova po slojevima i oslobađanje konekcije nakon driver grešaka.
Stvarni `prikazi_vrtice` odgovor na privremenom refaktoriranom MCP serveru bio
je identičan cijelom odgovoru postojećeg servera za Varaždin: 33/33 mapirane
lokacije, uključujući GeoJSON i izvore. Stvarni CSV dry-run vratio je 14 obrta,
a pretraga Brezja iste četiri lokacije. Privremeni server je ugašen; postojeći
server nije prekidan. `compileall` i `git diff --check` su uredni. Nema promjene
SQL upita, migracija niti ponovnog upisa u radnu bazu.

## Razlikovanje pružatelja u Varaždinu i Zagrebu — 2026-11-04

Istraživanje: `kindergarten.provider_kind` već je NOT NULL i ograničen na
`municipal`, `private`, `religious`, `childminder`, `other`, `unknown`.
`api/locations.py` → `services/concrete/location.py` →
`dao/concrete/asyncpg_location.py` već vraća i filtrira to polje. Zagrebački
parser i varaždinski CSV dadilja daju potvrđen tip; nacionalni parser ga
izostavlja. U radnoj bazi 11 varaždinskih i 91 zagrebačka ustanova zato ima
`unknown`; 79 zagrebačkih zapisa opisuje druge programe/udruge, a ne vrtiće.
Brojanje po općini obuhvaća i sjedišta čije mjesto nije doslovno Zagreb.
Razgovorna pretraga u `asyncpg_kindergarten.py` uopće ne vraća tip.

Razmotreno: novo polje s tri hrvatske vrijednosti dupliciralo bi već postojeći
ugovor i izgubilo razliku vjerskih vrtića. Odabrano: dopuniti postojeći tip,
sačuvati provjereni izvor razvrstavanja i dodati ga razgovornoj pretrazi.
Kurirana podudaranja nacionalnog parsera ograničiti na potvrđeni grad i točan
normalizirani naziv; ne zaključivati vlasništvo iz proizvoljnog naziva.
Ostale izričito imenovane programe/udruge u tim gradovima označiti `other`.
Nove nepoznate vrtiće zadržati kao `unknown` do provjere.

Izvori provjereni prije implementacije:
- https://varazdin.hr/djecji-vrtici/ — osnivači varaždinskih vrtića.
- https://varazdin.hr/upload/2024/11/obrazlozenje_nacrta_proracuna_2025-2027_-_672b9864ddddb.pdf
  — deset privatnih/vjerskih ustanova, uključujući Malo drvo, Sreću i Pandu.
- https://www.zagreb.hr/UserDocsImages/arhiva/odgoj_obrazovanje_spot/POPIS%20VJERSKIH%20I%20PRIVATNIH%20DV_ZA%20WEB_kris.pdf
  — osnivači zagrebačkih privatnih/vjerskih vrtića.
- https://tltkindergarten.com/hr/ — Drvo znanja.
- https://rino-institut.hr/ — Ružičnjak / Klinci Rinci.

Implementacija: dopuniti nacionalni parser pregledanim mapiranjem i URL-om
izvora; postojeći DAO zadržava taj izvor u provenijenciji. Nova Alembic
migracija dopunjava samo prethodno nepoznate tipove postojećih zapisa, bez
promjene identiteta ili geografske snimke. Provjeriti ponovljeni uvoz, opseg
grada, zaštitu poznatih tipova, API filtre i integracijske testove u odvojenoj
bazi. Nepoznato: budući izvori mogu sadržavati nove ustanove; ne dodjeljivati
im privatno vlasništvo bez dokaza.


Završna provjera: 84 Python testa, 81 prošao i tri opcionalna HTTP simulation
testa preskočena. Provjereni su ponovni uvoz, zaštita poznatih tipova i drugih
gradova, odbijanje NULL/nevažećeg tipa te vraćanje prethodne provenijencije pri
downgradeu. Migracija je primijenjena na lokalnu radnu bazu. Stvarni servis
lokacija vraća 33 lokacije Varaždina (9 municipal, 9 private, 1 religious,
14 childminder) i 461 Zagreba (241 municipal, 69 private, 18 religious,
54 childminder, 79 other). Nema `unknown` tipova u oba grada; pojedinačni
filtri vraćaju točno odgovarajuće skupove. `git diff --check` prolazi.

## Obuhvat Zagreba, Varaždina i Rijeke — 2026-11-04

Istraživanje: javni HTTP/MCP ulazi koriste `LocationQuery`, razgovorna pretraga
`RequestParser`, a svi redoviti izvori prolaze kroz `SourceRecordNormalizer`
prije `AsyncpgSourceRepository`. `dto/municipality.py` već potvrđuje općinu
prema mjestu i županiji, uz zagrebačka naselja. Radna baza ima 963 ustanove;
304 imaju sjedište ili objekt u tražena tri grada. Ostale treba ukloniti,
zajedno s pripadnim izvornim zapisima i ovisnim podacima. Postoje i pružatelji
s objektom u Zagrebu bez poznatog sjedišta; oni moraju ostati.

Pristupi: filtriranje samo prikaza ostavilo bi nepotrebne podatke i ponovni
uvoz ostalih gradova. Odabrano je zajedničko pravilo triju podržanih općina,
filtriranje prije upisa i provjera snapshotova u DAO-u, javno odbijanje
nepodržanog grada te transakcijska migracija čišćenja.

`MUNICIPALITIES` ostaje katalog samo triju gradova; nazivi, dijakritika i
postojeći padežni aliasi ostaju podržani. Naselja poput Sesveta ostaju dio
Zagreba; samostalni javni upit treba navesti podržani grad. Povijesne podatke
obrisati od ovisnih prema roditeljskim tablicama, bez CASCADE, uz očuvanje
ustanova s barem jednim podržanim objektom i njihovih dokaza. Izvorne zapise
bez povezane ustanove iz nacionalnog skupa također filtrirati po potvrđenoj
geografiji. Prije primjene na radnu bazu napraviti lokalni pg_dump; downgrade
ne izmišlja izbrisane podatke i zahtijeva obnovu sigurnosne kopije.

Provjera: miješani uvoz i ponovljeni uvoz, odbijanje nepodržanih gradova u
HTTP/MCP/razgovornoj pretrazi, očuvanje Rijeke i zagrebačkih naselja, migracija
s ovisnostima programa/kapaciteta/upisa/RAG-a i ustanovom vanjskog sjedišta.
Puni Python testovi koriste odvojenu testnu bazu. Nema otvorenih pitanja;
ne provoditi nova geokodiranja niti zaključivati nedostajuće tipove u Rijeci.

Završeno: migracija `0005_supported_cities` primijenjena je na lokalnu bazu
nakon sigurnosne kopije `database/backups/kidsic-before-supported-cities-20261104.dump`
(čitljivost arhiva potvrđena alatom pg_restore). Uklonjeno je 659 ustanova i
659 pripadnih izvornih zapisa; ostale su 304 ustanove i 694 izvorna zapisa.
Probna migracija s rollbackom usporedila je cijele odgovore lokacijskog DAO-a:
Zagreb 461, Varaždin 33 i Rijeka 13 rezultata ostali su identični. Završno
čitanje nakon primjene potvrdilo je iste brojeve i nula ustanova bez sjedišta
ili objekta u podržanim gradovima. Puni Python skup: 89 testova, 86 prošlo,
tri postojeća opcionalna HTTP simulation testa preskočena. Migracija je
provjerena i kroz Alembic nad odvojenom bazom; git diff --check prolazi.
