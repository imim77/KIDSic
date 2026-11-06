# Razgovorna provjera ograničenja dobi i programa

Aktualni programi i dobni/programski filtri uklonjeni su u migraciji 0012.
Scenariji se provjeravaju u ciljnom AI klijentu uz verziju modela i datum baze;
sintetičke ustanove ne prikazuju se kao stvarne.

1. „Vrtići u Zagrebu za dijete od 2 godine.” → objasniti da dobna prikladnost
   nije potvrđena dostupnim podacima; za opći prikaz tražiti korisnikov odabir
   prije izostavljanja željenog kriterija. Ne slati uklonjeni age_months.
2. „Montessori u Zagrebu.” → objasniti da opći filtar programa nije dostupan.
   Ne pretvoriti Montessori u name niti tvrditi da povijesni program vrijedi danas.
3. „Ima li Bajka u Zagrebu Montessori?” → dohvati_kontekst_vrtica s temom
   programs. Navesti datum i opseg dokaza; bez dokaza podatak nije potvrđen.
4. „Koliko je mjesta za moje dijete?” → citirati datum objavljenih mjesta ako
   postoje, objasniti opseg ustanova/objekt i da podatak nije jamstvo upisa.
5. „Samo potvrđeni za 24 mjeseca.” → objasniti ograničenje; ne slati
   include_unknown niti prikazivati broj rezultata kao potvrdu dobi.
6. „Prikaži gradske vrtiće u Rijeci.” → city i provider_kind; bez nasljeđivanja
   ranije spomenutih nepodržanih filtara. Naknadni radijus čuva te kriterije.

HTTP/MCP validacija i UI parser odbijaju uklonjene parametre čak i uz njihove
prije valjane vrijednosti. Povijesne objave ostaju odvojene od aktualnih tvrdnji.
