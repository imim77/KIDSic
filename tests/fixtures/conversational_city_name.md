# Provjera razgovorne pretrage: grad i naziv

Ovo su scenariji za provjeru AI klijenta povezanog s ažuriranim KIDSic MCP
serverom. Automatizirani testovi protokola, baze i UI-ja provjeravaju izvršavanje
strukturiranih poziva. Ne mjere pouzdanost izdvajanja argumenata proizvoljnog LLM-a.
Za procjenu modela zabilježiti naziv/verziju klijenta i modela te ponoviti ove
razgovore; mali početni skup nije statistička procjena kvalitete agenta.

Prije izmjene alat je prihvaćao samo `city`; poziv s `name` bio je odbijen.
Novi ugovor prihvaća `city` i opcionalni `name`, bez dodatnog čitanja izvora.

Svaki razgovor započeti zasebno:

1. „Prikaži vrtić Bajka u Zagrebu.” → grad Zagreb, naziv Bajka.
2. „Tražim Bajku u Varaždinu.” → grad Varaždin, naziv Bajka; ne Zagreb.
3. „Prikaži Zamet u Rijeci.” → grad Rijeka, naziv Zamet.
4. „Prikaži vrtiće u Varaždinu.” → grad Varaždin, bez naziva.
5. „Prikaži Čarobnu kućicu.” → pitanje za grad, bez poziva alata.
6. „Prikaži vrtiće.” → pitanje za grad, bez zadanog Zagreba.
7. „Tražim Bajku u Splitu.” → objašnjenje ograničenja na tri podržana grada.
8. „Prikaži NepostojeciTestNaziv u Rijeci.” → prazan rezultat uz iste kriterije;
   bez zamjene grada, uklanjanja naziva ili izmišljanja vrtića.
9. „Prikaži carobnu kucicu u Zagrebu.” → filtriranje bez potrebe za dijakriticima;
   naziv treba odgovarati nominativnom obliku ustanove, a ne cijeloj rečenici.
10. „Tražim Bajku, u Zagrebu ili Varaždinu.” → razjasniti jedan grad.

Odvojeno ocijeniti: ispravan alat i argumente, pitanje za nedostajući/višeznačan
grad, očuvanje gradskog opsega, podudaranje prikaza i upita te postupanje kad nema
rezultata. Za svaki scenarij očekuje se prolaz svih primjenjivih kriterija.
Nepostojeći naziv ne smije uzrokovati dodatnu širu pretragu bez korisnikova izbora.

Pri provjeri UI-ja izazvati privremenu pogrešku pretrage i odabrati „Pokušaj
ponovno”: alat mora primiti isti grad i naziv. Zatim poslati novi upit za drugi
naziv u istom gradu i potvrditi da stari rezultati i kriterij ne ostaju na karti.
