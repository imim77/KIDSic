# Provjera razgovorne pretrage: dob i program

Deterministički testovi provjeravaju validaciju, SQL, UI i MCP bridge. To nije
ocjena uspješnosti modela. Ove scenarije provjeriti u ciljnom AI klijentu uz
verziju klijenta/modela i datum snimke podataka; ne prikazivati sintetičke
ustanove kao stvarne. Lokalna snimka trenutačno nema zapisa programa.

1. „Vrtići u Zagrebu za dijete od 2 godine.” → age_months 24.
2. „Dijete ima 18 mjeseci, Rijeka.” → age_months 18.
3. „Dvije godine i šest mjeseci, Varaždin.” → age_months 30.
4. „Dijete ima dvije i pol godine, Zagreb.” → age_months 30, ne 2 ili 24.
5. „Tražim Montessori u Zagrebu za dvije godine.” → age 24, program Montessori;
   ne slati Montessori kao name bez zahtjeva za nazivom ustanove.
6. „Montessori u Zagrebu.” → samo program; ne izmišljati dob.
7. „Tražim jaslice u Rijeci.” ako se traži dobna prikladnost → pitati dob;
   ne pretvoriti riječ jaslice u pretpostavljen raspon ili točnu dob.
8. „Dijete je malo, Varaždin.” → pitati za dob ako je ona kriterij.
9. „Za dijete od 24 mjeseca.” bez utvrđenog grada → pitati grad.
10. „Za dvoje djece, 2 i 5 godina, Zagreb.” → razjasniti jednu dob po pozivu;
    ne izabrati proizvoljno jednu niti tvrditi da su obje zadovoljene.
11. „Vrtići za novorođenče u Zagrebu, 0 mjeseci.” → age 0; ne izgubiti nulu.
12. „Privatni vrtić Bajka u Centru Varaždina, Montessori, 24 mjeseca.” → svi
    kriteriji u jednom pozivu bez zamjene naziva programom.
13. „Samo potvrđeni za 24 mjeseca, Rijeka.” → include_unknown false; ako nema
    dokaza, objasniti nulu bez tvrdnje da ondje nema odgovarajućih vrtića.
14. „Uključi i one gdje treba provjeriti uvjete.” → include_unknown true;
    odvojeno navesti confirmed/unknown, bez tvrdnje da unknown odgovara dobi.
15. „Koliko je mjesta za moje dijete?” → ne tumačiti confirmed broj kao broj
    mjesta niti obećati upis; ta funkcionalnost nije dio ovog koraka.

Nastavci istog razgovora:

- „Gradski Montessori za 2 godine u Zagrebu na Črnomercu.” → grad/vrsta/područje/
  dob/program. „A za 3 godine?” mijenja age na 36 uz ostale iste kriterije.
- „Samo potvrđeni.” mijenja include_unknown na false. „Ipak pokaži i nepoznate.”
  vraća true bez uklanjanja dobi ili programa.
- „Makni dob.” → age_months null ili izostavljeno; program se čuva bez tvrdnje
  o prikladnosti za dob. „Svi programi.” zatim uklanja program i status postaje
  not_evaluated. Novi zaseban upit za grad ne nasljeđuje filtre.

Provjeriti zasebno: pretvaranje dobi u mjesece, izdvajanje programa nasuprot
nazivu ustanove, očuvanje kriterija, traženje pojašnjenja i iskrenost odgovora.
Stvarni podaci bez programskih dokaza moraju pokazivati nepoznato stanje.
Sintetički SQL testovi potvrđuju da se dob i program podudaraju u istom zapisu,
da je gornja granica isključiva i da zastarjeli ili pogrešno povezani dokazi ne
potvrđuju podudaranje. UI provjerava izvore i oznake potvrđenih podudaranja, bez gornjeg reda kriterija
i bez oznake nepoznatih uvjeta. Provjeriti retry sa svim kriterijima, fullscreen
i čišćenje starih kriterija; brojevi i nulta dob ostaju u odgovoru alata.
