# Workflow za izradu dijagrama projekta

Ovaj workflow vodi agenta kroz izradu osam vrsta dijagrama pomoću PlantUML-a.
Radi ih redom i temelji sadržaj na stvarnoj implementaciji projekta. Nastavi
kroz sve korake dok korisnik ne prihvati završni dijagram ili izričito ne
zatraži prekid.

## Obavezna potvrda nakon svakog dijagrama

1. Izradi jedan dijagram, provjeri ga i prikaži korisniku njegovu sliku i izvor.
2. Pitaj korisnika prihvaća li taj dijagram i želi li da prijeđeš na sljedeći.
3. **Pričekaj izričitu potvrdu.** Nemoj započeti izradu ni generiranje sljedećeg
   dijagrama dok potvrda ne stigne. Protek vremena nije potvrda.
4. Ako korisnik traži izmjene, doradi trenutačni dijagram, ponovno ga provjeri
   i ponovno zatraži potvrdu. Ako korisnik odbije ili zatraži prekid, stani.
5. Nakon potvrde nastavi od sljedećeg koraka. Nakon osmog dijagrama zatraži
   završno prihvaćanje, a zatim predaj poveznice na sve prihvaćene rezultate.

Ne smatraj workflow dovršenim nakon samo jednog dijagrama. Pauza radi tražene
potvrde dio je workflowa: u sljedećem odgovoru nastavi od mjesta na kojem si
stao, bez ponavljanja prihvaćenih dijagrama osim ako korisnik zatraži izmjenu.

## Referentne datoteke i redoslijed

Prije svakog koraka **otvori i pročitaj navedenu referentnu datoteku**. Koristi
njezin PlantUML zapis kao uzor za vrstu dijagrama, oblikovanje i razinu
prikaza. Nazive, razrede, veze i ponašanje preuzmi iz projekta koji obrađuješ;
ne prenosi činjenice iz referentnog primjera kao činjenice o projektu.

Putanje referenci su relativne na ovaj `workflow.md`. Izlazne datoteke piši u
`docs/diagrams/` projekta koji analiziraš; naziv i ekstenziju `.plantuml`
zadrži točno kako je navedeno. Referentne datoteke nemoj prepisivati.

| Korak | Dijagram | Referentna datoteka | Izlazni PlantUML |
|---|---|---|---|
| 1 | Slučajevi uporabe | `diagram_examples/use_case.plantuml` | `docs/diagrams/use_case.plantuml` |
| 2 | Paketi | `diagram_examples/package.plantuml` | `docs/diagrams/package.plantuml` |
| 3 | MVVM arhitektura frontenda | `diagram_examples/frontend_mvvm.plantuml` | `docs/diagrams/frontend_mvvm.plantuml` |
| 4 | Arhitektura backenda | `diagram_examples/backend_architecture.plantuml` | `docs/diagrams/backend_architecture.plantuml` |
| 5 | UML komponente | `diagram_examples/components.plantuml` | `docs/diagrams/components.plantuml` |
| 6 | ER model podataka | `diagram_examples/er_diagram.plantuml` | `docs/diagrams/er_diagram.plantuml` |
| 7 | UML razredi i obrasci | `diagram_examples/class_diagram.plantuml` | `docs/diagrams/class_diagram.plantuml` |
| 8 | UML slijed | `diagram_examples/sequence_diagram.plantuml` | `docs/diagrams/sequence_diagram.plantuml` |

Datoteke `components.plantuml`, `er_diagram.plantuml`, `class_diagram.plantuml`
i `sequence_diagram.plantuml` čuvaju primjere CrisisMap koje je korisnik
poslao u razgovoru. Primjerima ER i slijeda dodan je `@enduml` jer u poslanom
tekstu završna oznaka nije bila navedena. Primjer paketa čuva korisnikov
početni isječak u komentarima, a kao izvršiv uzor koristi dovršeni dijagram
KIDSic. Za slučajeve uporabe, MVVM frontend i backend koriste se već izrađeni
KIDSic dijagrami jer zasebni izvorni primjeri nisu bili poslani.

## Prije izrade

1. Pročitaj primjenjive projektne upute, dokumentaciju, strukturu i trenutačno
   stanje repozitorija. Sačuvaj postojeće korisničke izmjene.
2. Utvrdi tehnologije i granice sustava. Prati javne ulaze prema servisima,
   integracijama i pohrani. Za frontend provjeri ekrane, hookove i adaptere.
3. Za ER model provjeri posljednje migracije i ograničenja, uključujući strane
   ključeve, obaveznost i jedinstvenost. Ako je dostupna pokrenuta baza, njezinu
   reviziju možeš provjeriti čitanjem; ne mijenjaj shemu ni podatke bez zasebne
   korisnikove upute.
4. Ako projekt nema frontend, MVVM, backend ili bazu, nemoj izmišljati sloj.
   Objasni ograničenje korisniku i zatraži njegovu odluku za taj korak prije
   nastavka. Ako nedostaje referentna datoteka, najprije je potraži; ako je ne
   možeš pronaći ili rekonstruirati iz dostupnog izvora, prijavi što nedostaje.

## Što prikazati

- **Slučajevi uporabe:** granicu sustava, stvarne aktere, njihove ciljeve i
  opravdane UML veze. Vanjski sustav prikaži kao aktera samo ako sudjeluje u
  prikazanom slučaju uporabe.
- **Paketi:** stvarnu strukturu, logično grupiranje i potvrđene ovisnosti.
  Raspored prilagodi čitljivosti; ne opisuj sadržaj svakog paketa u samom okviru.
- **Frontend MVVM:** View, ViewModel i Model/adapere, uz stvarne nazive
  komponenti, hookova, podatkovnih ugovora i smjer njihovih veza. Prikaži
  container kada postoji i označi ako projekt koristi drugačiji obrazac.
- **Backend:** slojeve i njihovu odgovornost, stvarna sučelja servisa,
  implementacije, sastavljanje ovisnosti, pristup podacima i integracije.
  Slojeve rasporedi pregledno, po mogućnosti jedan ispod drugoga.
- **Komponente:** logičke komponente i sučelja unutar granice sustava, bazu
  unutar granice te vanjske usluge izvan nje. Označi važne tokove podataka;
  logička komponenta ne znači zasebno fizičko postavljanje.
- **ER:** stvarne entitete, identifikatore, strane ključeve, reprezentativne
  atribute i provjerene kardinalnosti. Izdvoji shemu iz migracija, ne iz DTO-a.
  Nemoj izmišljati primarni ključ ondje gdje ga baza nema. Navedi reviziju i
  gdje je model definiran. Ako korisnik želi hrvatske oznake, razlikuj oznake
  na dijagramu od stvarnih naziva stupaca; ne preimenuj bazu bez posebne upute.
- **Razredi i obrasci:** odaberi reprezentativno područje koje se može povezati
  s kodom. Prikaži stvarne razrede, relevantne atribute, operacije, sučelja,
  nasljeđivanje i ovisnosti. Ne prikazuj kompoziciju ili poslovna pravila koja
  nisu potvrđena. Dodatne dijagrame radi samo kad ih korisnik zatraži.
- **Slijed:** odaberi stvarni slučaj uporabe, sudionike i redoslijed poziva.
  Prikaži relevantne alternativne ishode i pogreške; ne izmišljaj HTTP
  statuse, aktore ni ponašanje vanjskih sustava.

## Izrada i provjera svakog koraka

1. Pročitaj odgovarajući primjer iz tablice i relevantan kod projekta.
2. Napiši točno imenovani `.plantuml` izvor. Prati referentne boje, font i UML
   notaciju, uz eventualne korisnikove izričite izmjene. Sačuvaj postojeće
   korisničke datoteke: ako ciljni naziv već postoji, najprije provjeri njegov
   sadržaj i prilagodi ga umjesto da naslijepo prepišeš nepovezan rad.
3. Renderiraj SVG i PNG s istim osnovnim imenom. PNG mora biti prikladan za
   umetanje u Word, a SVG treba omogućiti povećavanje bez gubitka kvalitete.
   Ako za tekst čitljiv na stranici treba koristiti vodoravni raspored ili
   više prikaza, objasni to korisniku i predstavi konkretan rezultat.
4. Provjeri prolazi li PlantUML, vizualno pregledaj sliku i usporedi nazive,
   veze, smjer strelica, kardinalnosti i grane s kodom ili shemom. Ispravi
   pogreške prije prikazivanja. Funkcionalne testove pokreni samo kada su
   potrebni za provjeru tvrdnji dijagrama ili ih korisnik izričito zatraži.
5. Pokaži poveznice na `.plantuml`, SVG i PNG te kratak opis obuhvata. Pitaj
   za potvrdu prema pravilima iz prvog odjeljka i pričekaj odgovor.

Ako korisnik unaprijed odredi mapu za Word slike, spremi PNG i u tu mapu kada
su dostupna potrebna dopuštenja. Ako upis nije dopušten, zadrži rezultat u
projektu i jasno navedi ograničenje. Ne tvrdi da je slika spremljena na drugoj
lokaciji dok kopiranje nije uspjelo.
