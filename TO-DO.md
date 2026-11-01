# TO-DO — KIDSic

## Uvoz i povezivanje otvorenih podataka

- [ ] Uvoziti nacionalni imenik dječjih vrtića MZOM-a s Portala otvorenih podataka RH.
- [ ] Uvoziti gradski skup lokacija i kontakata gradskih vrtića Zagreba.
- [ ] Uvoziti zaseban gradski skup privatnih i vjerskih vrtića te obrta za čuvanje djece.
- [ ] Obogatiti povezane objekte dostupnim atributima iz skupa Geoportal Dječji vrtići, uz potvrđene uvjete korištenja.
- [ ] Obrađivati JSON i CSV izvore s različitim zaglavljima, kodiranjima i zapisima adresa i koordinata.
- [ ] Povezivati nacionalne zapise ustanova s gradskim objektima prema normaliziranom nazivu, adresi i dostupnim identifikatorima.
- [ ] Razlikovati ustanovu, matični objekt i područne objekte te prikazivati sve lokacije iste ustanove.
- [ ] Uklanjati duplikate i prepoznavati preslike istog skupa na nacionalnom, gradskom i EU portalu.
- [ ] Zadržavati nepovezane zapise i označavati nesigurna podudaranja kako bi ih bilo moguće pregledati i ispraviti.
- [ ] Prikazivati objedinjeni profil vrtića s informacijama iz više skupova te navesti koji je izvor pridonio pojedinom podatku.

## Pretraga i odabir vrtića

- [ ] Pretraživati nacionalni imenik prema nazivu, mjestu, gradu, županiji i poštanskom broju.
- [ ] Pronalaziti objekte prema odabranoj lokaciji i radijusu udaljenosti kada su dostupne provjerene koordinate.
- [ ] Filtrirati zagrebačke objekte prema gradskoj četvrti.
- [ ] Filtrirati prema vrsti pružatelja: gradski, privatni, vjerski vrtić ili obrt dadilja.
- [ ] Filtrirati prema dobi djeteta i programu kada postoje potvrđeni podaci, uz zasebnu oznaku za rezultate s nepoznatim uvjetima.
- [ ] Prikazivati rezultate na listi i karti, s međusobno povezanim odabirom objekta.
- [ ] Omogućiti sortiranje prema udaljenosti i objasniti aktivne kriterije pretrage.

## Detalji i usporedba

- [ ] Prikazivati naziv ustanove, odabrani objekt, adresu, lokaciju, vrstu pružatelja, kontakte i službenu web-stranicu.
- [ ] Prikazivati potvrđene programe, jezike i atribute objekta kada postoje u povezanim izvorima.
- [ ] Omogućiti usporedbu do tri vrtića ili objekta prema udaljenosti, vrsti, dostupnim programima, objavljenim mjestima i postupku upisa.
- [ ] Omogućiti promjenu objekta unutar iste ustanove uz očuvanje povezanih podataka ustanove.
- [ ] Za podatke koji se razlikuju među izvorima prikazati neslaganje i podrijetlo vrijednosti.

## Objavljena slobodna mjesta

- [ ] Povezivati objavljene podatke o slobodnim mjestima s ustanovom, dobnom skupinom i programom, uz potvrđene uvjete korištenja izvora.
- [ ] Razlikovati mjesta objavljena za cijelu ustanovu od mjesta vezanih uz konkretan objekt.
- [ ] Prikazivati broj mjesta zajedno s datumom na koji se podatak odnosi i poveznicom na izvor.
- [ ] Razlikovati objavljenu nulu slobodnih mjesta, nepoznato stanje i zastarjelu snimku podataka.
- [ ] Omogućiti filtriranje prema objavljenim slobodnim mjestima uz vidljiv datum stanja.
- [ ] Za izvore bez potvrđenog uvoza omogućiti otvaranje službenog pregleda slobodnih mjesta.

## MCP app i razgovorna pretraga

- [ ] Povezati razgovorni upit o gradu i dobi djeteta sa strukturiranom pretragom te odvojiti potvrđenu dobnu prikladnost od nepoznatih uvjeta.
- [ ] Dohvaćati relevantne opise i upute kroz RAG samo za pronađene vrtiće i odgovarajuće programe, uz provjerljive poveznice na izvore.
- [ ] Omogućiti pretragu, dohvat detalja, usporedbu i vodič za upis kroz MCP alate.
- [ ] Pretvarati upit roditelja prirodnim jezikom u vidljive kriterije pretrage nad stvarnim podacima.
- [ ] Zatražiti pojašnjenje kada za pretragu nedostaje ključan podatak poput lokacije ili željene dobne skupine.
- [ ] Objasniti zašto rezultat odgovara upitu, uz poveznice na izvore korištenih informacija.
- [ ] Omogućiti otvaranje detalja, karte, usporedbe i službenog upisnog odredišta iz interaktivnog prikaza rezultata u MCP appu.
- [ ] Omogućiti korištenje osnovnih filtara i pregleda rezultata kada razgovorna AI funkcija nije dostupna.

## Priprema i nastavak upisa

- [ ] Povezivati svaku ustanovu s odgovarajućim službenim kanalom upisa: nacionalnim e-Upisima, gradskim sustavom ili uputama vrtića.
- [ ] Prikazivati službeni poziv, pedagošku godinu i objavljene rokove te razlikovati otvorene, buduće i završene rokove.
- [ ] Prikazivati korake i popis potrebnih dokumenata prema važećem službenom izvoru za odabranu ustanovu.
- [ ] Omogućiti nastavak na službeni sustav upisa uz jasno označen prijelaz na vanjsku uslugu.
- [ ] Razlikovati pripremu upisa i otvaranje službenog portala od stvarno predanog zahtjeva i potvrđenog upisa.

## Izvori, svježina i dostupnost

- [ ] Za svaki korišteni skup prikazivati izdavača, poveznicu, licencu, pokrivenost i datum dohvata.
- [ ] Razlikovati datum izmjene kataloga, datum izmjene resursa i datum stvarnog stanja podataka.
- [ ] Prikazivati nedostajuće podatke i ograničenu pokrivenost bez izmišljanja vrijednosti ili jamstva upisa.
- [ ] Omogućiti ponovno osvježavanje izvora uz očuvanje posljednje uspješno obrađene snimke.
- [ ] Omogućiti pretragu nad posljednjom uspješnom snimkom kada vanjski izvor nije dostupan, uz vidljivu oznaku svježine.
- [ ] Omogućiti demonstraciju cijelog korisničkog tijeka na reproducibilnoj snimci stvarnih povezanih podataka.
- [ ] Omogućiti korištenje pretrage, usporedbe i vodiča bez registracije roditelja i unosa OIB-a djeteta.
- [ ] Omogućiti korištenje ključnih funkcija na mobitelu i tipkovnicom, uz čitljive oznake i jasne poruke o praznim rezultatima i pogreškama.
