import { useEffect, useRef, useState } from "react";
import {
  ArrowDownUp,
  ArrowRight,
  Check,
  ChevronDown,
  Heart,
  Info,
  LayoutList,
  Leaf,
  Map,
  MapPin,
  Minus,
  PanelsTopLeft,
  Plus,
  Search,
  SlidersHorizontal,
  Sun,
  X,
} from "lucide-react";
import { Button } from "../../shared/ui/button";
import { Badge } from "../../shared/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "../../shared/ui/card";

type Kind = "Svi vrtići" | "Gradski" | "Privatni" | "Dadilje";
type School = {
  id: number;
  name: string;
  address: string;
  kind: Kind;
  area: string;
  color: string;
  x: number;
  y: number;
};
const schools: School[] = [
  {
    id: 1,
    name: "Vrtić Sunčani kutak",
    address: "Ulica lipa 12",
    kind: "Gradski",
    area: "Centar",
    color: "sunny",
    x: 46,
    y: 41,
  },
  {
    id: 2,
    name: "Vrtić Mala šuma",
    address: "Parkovna ulica 8",
    kind: "Privatni",
    area: "Banfica",
    color: "forest",
    x: 73,
    y: 28,
  },
  {
    id: 3,
    name: "Vrtić Plavi oblak",
    address: "Ulica braće Radić 24",
    kind: "Gradski",
    area: "Jalkovec",
    color: "blue",
    x: 69,
    y: 68,
  },
  {
    id: 4,
    name: "Dadilje Bubamara",
    address: "Cvjetna ulica 6",
    kind: "Dadilje",
    area: "Centar",
    color: "rose",
    x: 24,
    y: 63,
  },
];
const cities = ["Varaždin", "Zagreb", "Rijeka", "Split", "Osijek"];

function Neighborhood({
  visible,
  selected,
  onSelect,
  city,
}: {
  visible: School[];
  selected: number | null;
  onSelect: (id: number) => void;
  city: string;
}) {
  const [zoom, setZoom] = useState(1);
  return (
    <section className="neighborhood" aria-label={`Shematska karta: ${city}`}>
      <div className="map-canvas" style={{ transform: `scale(${zoom})` }}>
        <svg
          className="street-map"
          viewBox="0 0 800 650"
          preserveAspectRatio="xMidYMid slice"
          aria-hidden="true"
        >
          <rect width="800" height="650" fill="#edf0e8" />
          <g fill="#e1e6db" stroke="#d8e0d5" strokeWidth="1.5">
            <path d="m45 30 151 0 15 100-158 28Z" />
            <path d="m244 22 142 0-12 127-137-12Z" />
            <path d="m435 22 112 0 6 134-130-15Z" />
            <path d="m605 10 170 0 13 146-161 17Z" />
            <path d="m28 213 158-35 23 124-153 38Z" />
            <path d="m249 193 121 2-15 132-104-5Z" />
            <path d="m423 199 141 12-7 133-139-12Z" />
            <path d="m620 216 159-20-7 156-151-7Z" />
            <path d="m45 394 154-40 18 114-141 42Z" />
            <path d="m263 382 92 0 8 145-87-2Z" />
            <path d="m420 387 138 9 4 127-141 1Z" />
            <path d="m616 394 158 0-3 134-151-1Z" />
          </g>
          <g fill="#d1e3c9">
            <path d="M453 24h93v121l-113-9Z" />
            <path d="m24 399 156-35 17 94-141 43Z" />
            <rect x="635" y="231" width="124" height="93" rx="24" />
          </g>
          <g fill="#e2dcd1">
            {[60, 109, 158].map((x) => (
              <rect key={x} x={x} y="54" width="29" height="47" rx="4" />
            ))}
            {[270, 315].map((x) => (
              <rect key={x} x={x} y="52" width="27" height="56" rx="4" />
            ))}
            {[72, 122, 161].map((x) => (
              <rect key={x} x={x} y="228" width="26" height="55" rx="4" />
            ))}
            {[445, 490, 530].map((x) => (
              <rect key={x} x={x} y="253" width="24" height="56" rx="4" />
            ))}
            {[453, 501, 540, 644, 686, 733].map((x) => (
              <rect key={x} x={x} y="424" width="26" height="62" rx="4" />
            ))}
            <rect x="272" y="238" width="64" height="47" rx="4" />
            <rect x="285" y="416" width="49" height="81" rx="4" />
          </g>
          <g
            fill="none"
            stroke="#fffefa"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path
              d="M-30 199Q220 137 387 172T837 167M-20 386Q213 315 392 358T839 368M224-20q-14 200 15 385t20 296M398-20q-34 194-10 365t7 340M579-20q25 215 8 383t18 304"
              strokeWidth="25"
            />
            <path d="M-20 550q240 28 430-1t430 9" strokeWidth="22" />
          </g>
          <path
            d="M-20 594Q164 533 336 596T826 575"
            fill="none"
            stroke="#b5dbe9"
            strokeWidth="62"
          />
          <path
            d="M-20 594Q164 533 336 596T826 575"
            fill="none"
            stroke="#c7e6ee"
            strokeWidth="40"
          />
          <path
            d="m233 563 12 63m342-68 12 66"
            stroke="#fffefa"
            strokeWidth="26"
          />

          <g
            fill="#8b9986"
            fontFamily="inherit"
            fontSize="12"
            textAnchor="middle"
          >
            <text x="487" y="173">
              Park mladih
            </text>
            <text x="116" y="531">
              Gradski park
            </text>
            <text x="693" y="342">
              Zeleni kutak
            </text>
          </g>
          <g
            fill="#9ca5a2"
            fontFamily="inherit"
            fontSize="11"
            letterSpacing="2"
            textAnchor="middle"
          >
            <text x="313" y="211">
              CENTAR
            </text>
            <text x="701" y="115">
              BANFICA
            </text>
            <text x="490" y="489">
              JALKOVEC
            </text>
          </g>
          <g fill="#a1aaa5" fontFamily="inherit" fontSize="10">
            <text x="65" y="173" transform="rotate(-12 65 173)">
              Ulica lipa
            </text>
            <text x="442" y="365" transform="rotate(7 442 365)">
              Ulica braće Radić
            </text>
            <text x="603" y="449" transform="rotate(-90 603 449)">
              Parkovna ulica
            </text>
          </g>
          <text
            x="448"
            y="606"
            fontSize="12"
            letterSpacing="4"
            fill="#6ea6bd"
            transform="rotate(-3 448 606)"
          >
            DRAVA
          </text>
        </svg>
        {visible.map((s) => (
          <button
            key={s.id}
            className="map-pin"
            data-active={selected === s.id}
            style={{ left: `${s.x}%`, top: `${s.y}%` }}
            aria-label={`Prikaži ${s.name}`}
            aria-pressed={selected === s.id}
            onClick={() => onSelect(s.id)}
          >
            <span>{s.id}</span>
          </button>
        ))}
      </div>
      <div className="map-city">
        <MapPin size={16} />
        <span>{city}</span>
        <span className="map-city-dot" />
        Hrvatska
      </div>
      <div className="zoom-controls">
        <Button
          variant="ghost"
          size="icon"
          aria-label="Povećaj kartu"
          disabled={zoom >= 1.5}
          onClick={() => setZoom((z) => Math.min(1.5, z + 0.1))}
        >
          <Plus />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Smanji kartu"
          disabled={zoom <= 1}
          onClick={() => setZoom((z) => Math.max(1, z - 0.1))}
        >
          <Minus />
        </Button>
      </div>
      {selected !== null && visible.some((s) => s.id === selected) && (
        <div className="map-selection">
          <span className="selection-number">{selected}</span>
          <div>
            <strong>{schools.find((s) => s.id === selected)?.name}</strong>
            <span>
              {schools.find((s) => s.id === selected)?.address}, {city}
            </span>
          </div>
          <Check size={18} />
        </div>
      )}
      <span className="map-caption">
        Ilustrativna karta · lokacije su primjeri
      </span>
    </section>
  );
}

export default function KindergartenDesign() {
  const [city, setCity] = useState("Varaždin");
  const [cityDraft, setCityDraft] = useState("Varaždin");
  const [query, setQuery] = useState("");
  const [searchDraft, setSearchDraft] = useState("");
  const [kind, setKind] = useState<Kind>("Svi vrtići");
  const [selected, setSelected] = useState<number | null>(1);
  const [saved, setSaved] = useState<number[]>([]);
  const [savedOnly, setSavedOnly] = useState(false);
  const [view, setView] = useState<"split" | "list" | "map">("split");
  useEffect(() => {
    const narrow = window.matchMedia("(max-width: 759px)");
    const adapt = () => setView(narrow.matches ? "list" : "split");
    adapt();
    narrow.addEventListener("change", adapt);
    return () => narrow.removeEventListener("change", adapt);
  }, []);
  const [alphabetical, setAlphabetical] = useState(false);
  const guide = useRef<HTMLDialogElement>(null);
  const visible = schools
    .filter(
      (s) =>
        (kind === "Svi vrtići" || s.kind === kind) &&
        (!savedOnly || saved.includes(s.id)) &&
        `${s.name} ${s.address} ${s.area}`
          .toLocaleLowerCase("hr")
          .includes(query.toLocaleLowerCase("hr")),
    )
    .sort((a, b) =>
      alphabetical ? a.name.localeCompare(b.name, "hr") : a.id - b.id,
    );
  const toggleSave = (id: number) =>
    setSaved((items) =>
      items.includes(id) ? items.filter((x) => x !== id) : [...items, id],
    );
  return (
    <div className="kidsic-design">
      <div className="app-shell">
        <header className="app-header">
          <a
            href="/design.html"
            className="wordmark"
            aria-label="KIDSic početna"
          >
            <span>K</span>
            <span>I</span>
            <span>D</span>
            <span>S</span>
            <span>i</span>
            <span>c</span>
            <span className="wordmark-period">.</span>
          </a>
          <span className="header-caption">
            Mali svijet. Velike mogućnosti.
          </span>
          <Button
            variant="ghost"
            className="saved-button"
            aria-pressed={savedOnly}
            onClick={() => setSavedOnly((x) => !x)}
          >
            <Heart
              data-icon="inline-start"
              fill={savedOnly ? "currentColor" : "none"}
            />
            Moj izbor<Badge variant="secondary">{saved.length}</Badge>
          </Button>
        </header>
        <section className="intro">
          <div className="intro-copy">
            <div className="intro-kicker">
              <span />
              ZA VAŠ NAJLJEPŠI POČETAK
            </div>
            <h1>
              Mali koraci,
              <br />
              velike{" "}
              <span>
                avanture.
              </span>
            </h1>
            <p>
              Pronađite pravo mjesto za igru, prijateljstva
              i sve ono što vaše dijete tek
              postaje.
            </p>
          </div>

        </section>
        <main>
          <form
            className="search-bar"
            onSubmit={(e) => {
              e.preventDefault();
              setCity(cityDraft);
              setQuery(searchDraft.trim());
              setSelected(null);
            }}
          >
            <label className="city-field">
              <MapPin size={20} />
              <span>
                <span className="field-label">Gdje tražimo?</span>
                <select
                  aria-label="Grad"
                  value={cityDraft}
                  onChange={(e) => setCityDraft(e.target.value)}
                >
                  {cities.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </span>
              <ChevronDown size={16} />
            </label>
            <label className="name-field">
              <Search size={20} />
              <input
                aria-label="Naziv vrtića ili kvart"
                placeholder="Naziv vrtića ili kvart…"
                value={searchDraft}
                onChange={(e) => setSearchDraft(e.target.value)}
              />
            </label>
            <Button type="submit" className="search-submit">
              Pronađi vrtić
              <ArrowRight data-icon="inline-end" />
            </Button>
          </form>
          <div className="filter-row">
            <fieldset className="kind-filters">
              <legend className="sr-only">Vrsta vrtića</legend>
              {(["Svi vrtići", "Gradski", "Privatni", "Dadilje"] as Kind[]).map(
                (k) => (
                  <label
                    key={k}
                    className="filter-option"
                    data-checked={kind === k}
                  >
                    <input
                      type="radio"
                      name="kind"
                      checked={kind === k}
                      onChange={() => setKind(k)}
                    />
                    {k === "Svi vrtići" && <SlidersHorizontal size={14} />}
                    {k}
                  </label>
                ),
              )}
            </fieldset>
            <Button
              variant="link"
              className="guide-trigger"
              onClick={() => guide.current?.showModal()}
            >
              <Info data-icon="inline-start" />
              Kako odabrati vrtić?
            </Button>
          </div>
          <div className="results-header">
            <div>
              <h2>
                {savedOnly ? "Vaš mali izbor" : `Vrtići: ${city}`}
                <span className="result-count">{visible.length}</span>
              </h2>
              <p>
                {savedOnly
                  ? "Mjesta koja želite malo bolje upoznati."
                  : "Jedno od ovih mjesta moglo bi postati njihovo omiljeno."}
              </p>
            </div>
            <div className="view-buttons" aria-label="Način prikaza">
              <Button
                variant="ghost"
                className="split-view"
                size="icon"
                aria-label="Prikaži popis i kartu"
                aria-pressed={view === "split"}
                onClick={() => setView("split")}
              >
                <PanelsTopLeft />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Prikaži popis"
                aria-pressed={view === "list"}
                onClick={() => setView("list")}
              >
                <LayoutList />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Prikaži kartu"
                aria-pressed={view === "map"}
                onClick={() => setView("map")}
              >
                <Map />
              </Button>
            </div>
          </div>
          <div className="discovery" data-view={view}>
            <section
              className="result-list"
              aria-label="Vrtići"
              aria-live="polite"
            >
              <div className="list-toolbar">
                <span>
                  {visible.length}{" "}
                  {visible.length === 1 ? "rezultat" : "rezultata"} u vašem
                  gradu
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setAlphabetical((x) => !x)}
                >
                  <ArrowDownUp data-icon="inline-start" />
                  {alphabetical ? "Po nazivu" : "Zadani redoslijed"}
                </Button>
              </div>
              <div className="cards-scroll">
                {visible.map((s) => (
                  <Card
                    className="school-card"
                    key={s.id}
                    data-selected={selected === s.id}
                  >
                    <div className={`school-marker ${s.color}`} aria-hidden="true">{s.id}</div>
                    <div className="school-info">
                      <CardHeader>
                        <CardDescription>
                          {s.kind === "Gradski"
                            ? "Gradski vrtić"
                            : s.kind === "Privatni"
                              ? "Privatni vrtić"
                              : "Obrt za dadilje"}
                          <span>·</span>
                          {s.area}
                        </CardDescription>
                        <CardTitle>
                          <button onClick={() => setSelected(s.id)}>
                            {s.name}
                          </button>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <MapPin size={13} />
                        <span>
                          {s.address}, {city}
                        </span>
                      </CardContent>
                      <CardFooter>
                        <Button
                          variant="link"
                          size="sm"
                          onClick={() => {
                            setSelected(s.id);
                            if (window.innerWidth < 760) setView("map");
                          }}
                        >
                          Na karti
                          <ArrowRight data-icon="inline-end" />
                        </Button>
                      </CardFooter>
                    </div>
                    <Button
                      className="favorite"
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`${saved.includes(s.id) ? "Ukloni" : "Spremi"} ${s.name}`}
                      aria-pressed={saved.includes(s.id)}
                      onClick={() => toggleSave(s.id)}
                    >
                      <Heart
                        fill={saved.includes(s.id) ? "currentColor" : "none"}
                      />
                    </Button>
                  </Card>
                ))}
                {visible.length === 0 && (
                  <div className="no-results">
                    <Search size={27} />
                    <h3>
                      {savedOnly
                        ? "Vaš izbor čeka prvi vrtić."
                        : "Nismo pronašli taj mali kutak."}
                    </h3>
                    <p>
                      {savedOnly
                        ? "Dodirnite srce uz vrtić da ga spremite ovdje."
                        : "Pokušajte s drugim nazivom ili vrstom vrtića."}
                    </p>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setSavedOnly(false);
                        setKind("Svi vrtići");
                        setQuery("");
                        setSearchDraft("");
                      }}
                    >
                      Prikaži sve vrtiće
                    </Button>
                  </div>
                )}
              </div>
              <div className="parent-note">
                <Leaf size={19} />
                <p>
                  Svaki mališan raste svojim tempom.
                  <br />
                  <strong>Pronađite mjesto koje mu odgovara.</strong>
                </p>
              </div>
            </section>
            <Neighborhood
              visible={visible}
              selected={selected}
              onSelect={setSelected}
              city={city}
            />
          </div>
        </main>
        <footer className="app-footer">
          <span>
            <Sun size={15} />S ljubavlju za male početke.
          </span>
          <span>Dizajnerski prikaz · ogledni podaci</span>
        </footer>
      </div>
      <dialog
        ref={guide}
        className="parent-guide"
        aria-labelledby="guide-title"
      >
        <div className="guide-heading">
          <h2 id="guide-title">Velika odluka, korak po korak.</h2>
          <Button
            variant="ghost"
            size="icon"
            aria-label="Zatvori vodič"
            onClick={() => guide.current?.close()}
          >
            <X />
          </Button>
        </div>
        <p>Prije odluke, posjetite vrtić i razgovarajte s odgojiteljima.</p>
        <ul>
          <li>Kakav je dnevni ritam i kako izgleda prilagodba?</li>
          <li>Koliko djece i odgojitelja ima u skupini?</li>
          <li>Koliko vremena djeca provode vani?</li>
          <li>Kako vrtić podržava potrebe vašeg djeteta?</li>
        </ul>
        <div className="guide-note">
          <Info size={18} />
          <p>
            Dobne uvjete, cijene i slobodna mjesta provjerite izravno s vrtićem.
            Ovaj prikaz služi za pregled dizajna.
          </p>
        </div>
        <Button onClick={() => guide.current?.close()}>
          Razumijem
          <Check data-icon="inline-end" />
        </Button>
      </dialog>
    </div>
  );
}
