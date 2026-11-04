# Provjera razgovorne pretrage: vrsta pružatelja

Nastavak [provjere grada i naziva](conversational_city_name.md). Automatizirani
testovi provjeravaju ugovor, filtriranje u bazi i UI; ne predstavljaju mjerenje
uspješnosti pojedinog LLM-a. Ove scenarije dodatno provjeriti u ciljnom AI
klijentu nakon osvježavanja MCP konektora, uz zabilježenu verziju klijenta/modela.

Prije ovog koraka MCP je odbijao `provider_kind`, iako ga je HTTP API podržavao.
Novi MCP ugovor prihvaća jednu vrstu ili `null` za sve vrste.

Očekivani ishodi zasebnih razgovora:

1. „Prikaži samo gradske vrtiće u Zagrebu.” → Zagreb, `municipal`.
2. „Javni vrtići u Rijeci.” → Rijeka, `municipal`; ne izmišljati vrijednost `public`.
3. „Privatni vrtić Bajka u Varaždinu.” → Varaždin, Bajka, `private`.
4. „Vjerski vrtići u Varaždinu.” → Varaždin, `religious`; ne uključivati sve privatne.
5. „Tražim dadilju u Zagrebu.” → Zagreb, `childminder`.
6. „Obrti za čuvanje djece u Rijeci.” → Rijeka, `childminder`; nula rezultata je
   valjan ishod ako takvih zapisa nema, bez zamjene privatnim vrtićima.
7. „Vrtići nepoznate vrste u Rijeci.” → Rijeka, `unknown`; ne uključivati gradske.
8. „Svi vrtići u Zagrebu.” → Zagreb, vrsta izostavljena ili `null`, bez zadanog tipa.
9. „Privatni i vjerski vrtići u Zagrebu.” → razjasniti jednu vrstu za ovaj poziv;
   ne izabrati samo privatne i tvrditi da su uključene obje vrste.
10. „Samo gradski vrtići.” → pitati za grad, bez pretpostavljenog Zagreba.

Pri provjeri odvojeno ocijeniti izbor vrste, očuvanje grada i naziva, usklađenost
karte/popisa s kriterijima te postupanje kod nula rezultata. Svaki rezultat mora
pripadati odabranoj vrsti, uključujući zapise bez koordinata. Nepoznata vrsta ne
smije se tretirati kao javna samo zato što su oznake iste boje.

U UI-ju provjeriti da „Pokušaj ponovno” šalje isti grad, naziv i vrstu. Novi upit
bez vrste mora pokazati „Sve vrste”. Kriteriji ostaju vidljivi i u fullscreen
prikazu. Za nevaljanu vrstu ili popis vrsta server mora dati uputu za ispravak
bez čitanja baze. Ne uklanjati filter automatski radi dobivanja više rezultata.
