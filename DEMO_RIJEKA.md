# KIDSic — mladi roditelji traže vrtić u Rijeci

Ciljana duljina videa: **4:40**. Najdulje dopušteno trajanje: **5:00**.
Format: snimka stvarne aplikacije uz naraciju i skraćivanje čekanja u montaži.

## Priča

Glumimo mlade roditelje koji su se upravo doselili u Rijeku. Tražimo vrtić
za dijete, ne poznajemo lokalne ustanove ni pravila sufinanciranja i koristimo
javni prijevoz. Krećemo od pitanja „Odakle uopće početi?” i dolazimo do
nekoliko opcija, razumijevanja troškova, plana puta i konkretnog kontakta.

Nazive vrtića uvodimo tek kad se pojave na karti. Ne počinjemo unaprijed
pripremljenim popisom ustanova koje novodoseljeni roditelji još ne poznaju.
Dob djeteta nije zadana; aplikaciji ne pripisujemo potvrdu dobne prikladnosti.

## Promptovi

Šalji ih pojedinačno, ovim redom, u istom razgovoru. Koristi jezik roditelja,
a nazive alata i tehničke parametre ostavi izvan promptova.

### 1. Novi smo u gradu — gdje početi?

```text
Nedavno smo se doselili u Rijeku i tražimo vrtić za dijete. Ne poznajemo vrtiće u gradu i koristimo javni prijevoz. Za početak nam pokaži vrtiće u Rijeci na karti da vidimo gdje se nalaze i koje opcije imamo.
```

Proširi kartu. Otvori nekoliko objekata, uključujući Malu vilu, tako da
sljedeće pitanje prirodno proizlazi iz onoga što smo upravo vidjeli.

### 2. Što sufinanciranje znači za nas?

```text
Na karti smo primijetili Malu Vilu u Rijeci. Ne znamo kako funkcionira gradsko sufinanciranje vrtića. Možeš li nam na tom primjeru jednostavno objasniti koja su pravila i iznosi navedeni u dostupnim izvorima te što trebamo provjeriti kao obitelj koja se tek doselila? Navedi izvore i datume podataka. Ako se na temelju njih ne može utvrditi naše pravo ili konačna cijena, jasno nam to reci.
```

Nakon odgovora vrati prethodnu kartu. Gumbima **Usporedi** dodaj:

- Malu vilu — Zametska 6.
- Gardelin — Zvonimirova 58.
- Potok — Josipa Završnika 3.

Otvori usporedbu. Ove nazive biramo iz prikazanih rezultata, nakon upoznavanja
s kartom. Usporedba se popunjava klikovima; ne treba dodatni prompt.

### 3. Kako ćemo s djetetom na posao?

```text
Za naš probni dan u Rijeci polazimo sa Zametske 6 prema poslu na Korzu 16, 6. studenoga 2026. u 07:00. Koristimo javni prijevoz i za predaju djeteta trebamo 10 minuta. Koja su nam tri vrtića najbolja opcija prema najranijem dolasku na posao? Usporedi sve dostupne objekte s potvrđenim lokacijama, a ne samo one koje smo dosad gledali. Pokaži rute i plan puta.
```

Proširi rezultat. Pokaži tab **Put**, vrijeme dolaska, predaju djeteta i
prelazak između alternativa. Zatim pokaži tab **Vrtić** za odabranu opciju.

### 4. Koga kontaktirati i što još pitati?

```text
Za Malu Vilu u Rijeci daj nam kontakt i sastavi kratak popis pitanja koja trebamo postaviti prije odluke: prima li dijete njegove dobi, ima li slobodnih mjesta, koje je radno vrijeme, kako se upisuje i kolika bi bila cijena za našu obitelj. Odvoji ono što već znamo iz izvora od onoga što tek trebamo potvrditi s vrtićem.
```

Ovaj prompt ne šalje poruku vrtiću; traži kontakt i pripremu pitanja.
Za završni kadar vrati prikaz karte s rutom, bez novog upita za opću kartu.

## Priprema prije snimanja

- Koristi novi razgovor u klijentu s MCP Apps podrškom i KIDSic konektorom.
  Endpoint: `https://defective-hydroxide-timothy.ngrok-free.dev/mcp`.
- Provjeri kartu, proširenje, usporedbu i glavni izračun puta prije snimanja.
  Uspješan backend test sam ne dokazuje rad kontrola u konkretnom MCP hostu.
- Snimaj u 1920 × 1080 ako je moguće. Ukloni nepotrebne bočne panele,
  povećaj tekst koliko treba za čitljivost i isključi obavijesti.
- Promptove kopiraj, nemoj ih sporo tipkati. U videu ih ostavi čitljivima
  nekoliko sekundi prije prijelaza na rezultat.
- Prvo snimi stvarni rad aplikacije, zatim naraciju. Rečenice o rezultatima
  uskladi s onime što je doista vraćeno.
- Izreži čekanje i traženje objekata skrolanjem. Pri prvom skraćenom
  izračunu prikaži natpis „Čekanje na izračun skraćeno”. Ne mijenjaj
  prikazane rezultate niti sugeriraj nepostojeću brzinu odgovora.

Učitani riječki vozni red pokriva **9. 10. – 8. 11. 2026.** Zato koristimo
izričiti probni datum **6. 11. 2026. u 07:00**, a ne „sutra”. Uz rutu
prikaži natpis „Ogledni scenarij · 6. 11. 2026. · spremljeni vozni red”.
Adrese služe glumi obiteljskog scenarija i nisu osobni podaci stvarne obitelji.
Zametska 6 ujedno je adresa Male vile; nemoj skrivati tu podudarnost ako
objašnjava najbolje rangiranu opciju. Ovim oglednim polazištem ne tvrdimo
stvarno prebivalište obitelji niti dokazujemo njezino pravo na sufinanciranje.

## 0:00–0:15 — Doselili smo se i ne znamo odakle početi

**Kadar:** razgovor i početak prvog prompta. Kratak naslov:
„Novi u Rijeci. Kako pronaći vrtić?”

**Naracija:**

> Tek smo se doselili u Rijeku i tražimo vrtić za dijete. Ne poznajemo
> ustanove, ne znamo kako funkcionira sufinanciranje i koristimo javni
> prijevoz. Krenimo od onoga što nam je prvo potrebno: pregleda opcija.

## 0:15–0:55 — Upoznajemo grad kroz kartu

**Pošalji prompt 1.**

**Na ekranu:**

1. Pokaži dobivenu kartu i kartice.
2. Proširi aplikaciju klikom na karticu ili kontrolu proširenja.
3. Otvori Malu vilu, zatim Gardelin. Pokaži njihove nazive i adrese.
4. Vrati odabir na Malu vilu prije pitanja o sufinanciranju.

**Naracija:**

> Sada imamo kartu i konkretne opcije. Odabirom objekta vidimo njegovu
> adresu, vrstu i dostupne kontakte. Ne moramo unaprijed znati nazive
> riječkih vrtića da bismo započeli potragu.

Na karti su samo objekti s potvrđenim koordinatama; ostali zapisi mogu
ostati na popisu. Broj rezultata nemoj nazivati brojem jedinstvenih ustanova.

## 0:55–1:40 — Razumijemo sufinanciranje

**Pošalji prompt 2.**

**Na ekranu:** pokaži sažetak odgovora, iznos ako ga izvor daje, uvjete i citat
s datumom. Zadrži se nekoliko sekundi na razlici između gradskog pravila i
prava konkretne obitelji. Ne otvaraj vanjske stranice u ovom kratkom videu.

**Naracija:**

> Kao novim stanovnicima, nije nam jasno što ćemo stvarno plaćati.
> Na primjeru jednog vrtića dobivamo objašnjenje dostupnih pravila i izvore.
> Jasno je odvojeno što je objavljeno od onoga što još moramo potvrditi
> za našu obitelj, uključujući uvjete nakon doseljenja.

Ako izvor ne potvrđuje uvjet vezan uz prebivalište ili trajanje boravka,
prikaži to kao pitanje za provjeru. Nemoj dodavati neprovjeren uvjet u naraciju.
Ne izgovaraj unaprijed pripremljenu konačnu cijenu.

## 1:40–2:20 — Uspoređujemo prve opcije

**Nema novog prompta.** Vrati gradsku kartu iz prvog rezultata.

**Na ekranu:**

1. Dodaj Malu vilu, Gardelin i Potok kroz gumbe „Usporedi”.
2. Skrati skrolanje rezovima, zadržavajući stvarne klikove dodavanja.
3. Klikni „Usporedi” na traci s odabranim opcijama.
4. Pokaži usporedne podatke, „Provjeriti” i „Sljedeći korak”.

**Naracija:**

> Nekoliko vrtića izdvojili smo iz pregleda grada. Sada ih gledamo jedan
> uz drugi: gdje su, kako ih kontaktirati i što još treba provjeriti.
> Tako nastaje prva kratka lista, bez pretpostavke da su nepoznati podaci
> već potvrđeni.

Ostavi usporedbu mirno na zaslonu barem desetak sekundi.

## 2:20–3:50 — Možemo li preko vrtića stići na posao?

**Pošalji prompt 3.**

**Na ekranu:**

1. Pokaži prompt i natpis s probnim datumom. Skrati čekanje.
2. Proširi rezultat s rutama. Nemoj ga zamijeniti općom gradskom kartom.
3. Otvori tab „Put” i pokaži „Na poslu”, „Ukupno” i „Presjedanja”.
4. Pokaži plan puta i deset minuta za predaju djeteta.
5. Klikni „Sljedeća opcija”, pričekaj promjenu rute, zatim pokaži treću.
6. Na odabranoj opciji pokaži i tab „Vrtić”.

**Naracija:**

> Budući da koristimo javni prijevoz, sama blizina nije dovoljna.
> Za probni dan zadajemo polazište, posao i vrijeme polaska. Aplikacija
> uspoređuje dostupne mapirane objekte i vraća tri opcije prema dolasku
> na posao. Plan uključuje hodanje, javni prijevoz i predaju djeteta.
> Klikom možemo pregledati alternativu i vidjeti kako bi nam izgledalo
> jutro s drugim vrtićem.

Pri prethodnoj provjeri uspoređeno je 27 objekata. Taj broj navedi samo ako
je isti u snimljenom rezultatu. „Najbolje” znači najraniji dolazak među
vraćenim planiranim rutama; ne potvrđuje mjesto, dobnu prikladnost ni radno vrijeme.

## 3:50–4:20 — Znamo što nam je sljedeće napraviti

**Pošalji prompt 4.**

**Na ekranu:** pokaži kontakt i kratak popis pitanja. Posebno istakni stavke
za koje nema potvrde, bez čitanja cijelog odgovora naglas.

**Naracija:**

> Sada znamo koje nas opcije zanimaju i kako bismo do njih putovali.
> Dobivamo i konkretan sljedeći korak: kontakt vrtića i pitanja o dobi,
> mjestima, radnom vremenu, upisu i cijeni za našu obitelj. Znamo što
> je potvrđeno, a što još trebamo pitati.

## 4:20–4:40 — Završetak

**Kadar:** vrati prethodnu kartu s rutom i otvorenim detaljima puta.
U montaži možeš upotrijebiti stvarno snimljen kadar, bez sugeriranja novog izračuna.

**Naracija:**

> Od pitanja „Odakle početi?” došli smo do pregleda vrtića, razumijevanja
> sufinanciranja i plana jutarnjeg puta. KIDSic nam pomaže suziti izbor
> i pripremiti se za odluku, uz izvore i jasno označene nepoznanice.

Ostavi tri sekunde mirnog završnog kadra s nazivom KIDSic.

## Trajanje i montaža

- Sedam scena ukupno traje **280 sekundi**, uz 20 sekundi rezerve do pet minuta.
- Izbačena je promjena na hodanje: obitelj u ovoj priči koristi javni prijevoz.
- Ako moraš dodatno skratiti, usporedi dva vrtića umjesto tri i skrati
  dodavanje u usporedbu. Sačuvaj glavni izračun puta i objašnjenje izvora.
- Ne pokazuj instalaciju, postavljanje konektora, terminal, arhitekturu,
  sve filtre i rubne pogreške. Video prati jednu obitelj i njezinu potragu.
- Ne prikazuj slanje upita vrtiću ili prijavu djeteta kao izvršenu radnju:
  aplikacija u ovom toku daje informacije i pripremu za sljedeći korak.

## Provjera prije izvoza

- Trajanje uključujući uvod i završni kadar manje je od pet minuta.
- Svi promptovi i rezultati snimljeni su iz stvarnog rada aplikacije.
- Probni datum i skraćeno čekanje vidljivo su označeni.
- Naracija odgovara prikazanim iznosima, uvjetima i izračunima.
- Konačna cijena, pravo obitelji, mjesto, dobna prikladnost i radno vrijeme
  nisu proglašeni potvrđenima bez odgovarajućeg dokaza.
- U kadru nema vjerodajnica, obavijesti ili osobnih podataka stvarne obitelji.

## Dodatni promptovi za isprobavanje svih funkcionalnosti

Ovaj popis služi probi izvan vremenskog ograničenja videa.
Isprobaj ove promptove redom; nastavke šalji u istom razgovoru:

1. **Karta i kartice**  
   „Prikaži sve vrtiće u Rijeci na karti.”

2. **Gradski vrtići**  
   „Prikaži samo gradske vrtiće u Rijeci.”

3. **Druge vrste — pošalji zasebno**  
   „Prikaži privatne vrtiće u Rijeci.”  
   „Prikaži vjerske vrtiće u Rijeci.”  
   „Prikaži obrte za čuvanje djece u Rijeci.”

4. **Pretraga naziva**  
   „Prikaži vrtić Mala Vila u Rijeci.”

5. **Područje i nastavak pretrage**  
   „Prikaži vrtiće na Zametu u Rijeci.”  
   Zatim: „Zadrži Zamet, ali prikaži samo gradske.”  
   Zatim: „Ukloni područje, ali zadrži gradske vrtiće u Rijeci.”

6. **Radijus**  
   „Prikaži vrtiće u Rijeci unutar 1000 metara od točke longitude 14.4023729, latitude 45.3392354. Poredaj ih od najbližeg.”  
   To je zračna udaljenost, a ne vrijeme putovanja.

7. **Kontakti i izvori**  
   „Koji su telefon, e-mail i web vrtića Mala Vila u Rijeci? Navedi izvore i datume podataka.”

8. **Sufinanciranje**  
   „Koja spremljena pravila sufinanciranja vrijede kao kandidati za Malu Vilu u Rijeci? Navedi iznose, uvjete, izvore i datum provjere.”

9. **Granice dostupnih podataka**  
   „Prima li Mala Vila u Rijeci dvogodišnjake, ima li slobodnih mjesta i koji su rokovi upisa? Jasno odvoji potvrđene podatke od nepoznatih.”  
   Ovdje sustav treba priznati nedostatak dokaza.

10. **Put do posla javnim prijevozom**  
    „Za probni scenarij: živim na Zametskoj 6 u Rijeci, radim na Korzu 16. Polazim 6. studenoga 2026. u 07:00 javnim prijevozom. Usporedi sve dostupne objekte i prikaži tri najbolje opcije vrtića. Predaja djeteta traje 10 minuta.”

11. **Promjena prijevoza i predaje**  
    Nakon prethodnog: „Ponovi isti scenarij pješice, uz 5 minuta za predaju djeteta.”

12. **Vlastiti izbor vrtića**  
    „Za isti scenarij usporedi samo Malu Vilu, Gardelin i Potok, javnim prijevozom. Prikaži sve tri opcije.”

13. **Provjera pojašnjenja**  
    „Koji mi je vrtić u Rijeci najbolji na putu do posla?”  
    Treba pitati za dom, posao, datum, vrijeme i prijevoz.

Napomena za provjeru 13: za pouzdanu provjeru pitanja o nedostajućim podacima
pokreni novi razgovor ili izričito poništi prethodni scenarij. U istom
razgovoru ti podaci već mogu biti poznati iz koraka 10–12.
