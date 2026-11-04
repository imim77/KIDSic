# Provjera razgovorne pretrage: područje i nastavci razgovora

Automatizirani testovi provjeravaju ugovor, SQL i prikaz; nisu mjerenje kvalitete
LLM-a. Ove scenarije dodatno provjeriti u ciljnom AI klijentu nakon osvježavanja
MCP konektora, uz zapis klijenta, modela i datuma snimke podataka.

1. „Vrtići na Banfici u Varaždinu.” → `city: Varaždin`, `area: Banfica`.
2. „Samo gradski na Trešnjevci-Jug u Zagrebu.” → Zagreb, municipal, Trešnjevka-Jug.
3. „Privatni vrtić Bajka u Centru, Varaždin.” → sva četiri kriterija; ne uklanjati
   naziv ili vrstu da bi se dobilo više rezultata.
4. „Vrtići na Zametu u Rijeci.” → Rijeka, Zamet; potvrđeni naziv u podacima može
   biti `Mjesni odbor Zamet`, ali Gornji Zamet nije isto područje.
5. „Vrtići u Črnomercu, Zagreb.” → Zagreb, Črnomerec; inačica `crnomerec` daje
   iste rezultate. Djelomični naziv `Črno` nije isti naziv područja.
6. „Tražim vrtiće na Banfici.” bez prethodnog grada → pitati grad; ne zaključivati
   grad iz imena područja.
7. „U nepostojećem području, Rijeka.” → nula uz iste kriterije; objasniti da
   nedostaje potvrđeno podudaranje, bez tvrdnje da ondje nema vrtića.
8. „Bajka na Banfici” → bez utvrđenog grada pitati grad; naziv objekta i područje
   ne zamjenjuju jedan drugoga.
9. „Prikaži Banfica” uz utvrđen grad, bez jasnog značenja → razjasniti misli li
   korisnik na područje ili naziv ustanove, umjesto proizvoljnog izbora.
10. „Banfica i Centar u Varaždinu.” → razjasniti jedno područje za poziv.

Višekoračni razgovori:

- „Privatni vrtić Bajka u Varaždinu.” → Varaždin, Bajka, private, bez područja.
  „Samo u Centru.” → isti grad/naziv/vrsta, `area: Centar`.
  „Makni naziv vrtića.” → Varaždin, private, Centar, bez name.
  „Bez ograničenja na područje.” → Varaždin, private, bez area.
- „Gradski vrtići na Zametu u Rijeci.” → Rijeka, municipal, Zamet.
  „A na Srdočima?” → Rijeka, municipal, Srdoči; bez oznaka stare pretrage.
  „Sve vrste tamo.” → Rijeka, Srdoči, provider_kind izostavljen ili null.
- Novi zaseban razgovor „Svi vrtići u Zagrebu.” → bez naslijeđenih filtara.

Odvojeno ocijeniti izdvajanje područja, očuvanje drugih kriterija, traženje
pojašnjenja, podudaranje rezultata i iskrenost objašnjenja praznog skupa.
Automatizirano se provjerava da adresa ili naziv koji spominju područje nisu
zamjena za potvrđeno polje, da stari/odbijeni/isključeni izvori ne filtriraju
te da sjedište s promijenjenom adresom ne zadržava staro područje.

U UI-ju provjeriti vidljivost područja i napomene o nepotpunoj pokrivenosti,
uključujući fullscreen. „Pokušaj ponovno” šalje sva četiri ista kriterija.
Novi poziv bez area prikazuje „Sva područja”; odsutnost filtra nije skriveno
nasljeđivanje. Nepoznate koordinate ne uklanjaju potvrđeno područje iz popisa.
