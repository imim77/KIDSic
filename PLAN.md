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
