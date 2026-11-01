// Contract: CKAN package_show envelope + the JSON array shapes captured in
// tests/fixtures. All kindergarten rows here are synthetic. No upstream calls.
const http = require('http');
const base = process.env.KIDSIC_CKAN_SIMULATION_URL || 'http://127.0.0.1:45471/ckan';
const municipalId = 'gradski_vrtici_grada_zagreba';
const otherId = 'privatni-vjerski-obrti-gz-kontakt-podaci';
const national = [{Naziv: 'Dječji vrtić "Primjer"', Adresa: 'Primjer 1', Mjesto: 'Zagreb',
  ePosta: '', Telefon: '', Zupanija: 'Grad Zagreb', PostanskiBroj: '10000'}];
const municipal = [{Id: 1, Naziv: 'DV Primjer-matični objekt', Adresa: 'Primjer 1',
  X: '15,9452', Y: '45.8017', Web: null, Email: 'test@example.invalid', Telefon: '',
  TipVrtica: 'Matični', VrstaVrtica: 'Gradski DV', GradskaCetvrt: 'Trešnjevka-Sjever'},
  {Id: 2, Naziv: 'DV Primjer-PO Druga', Adresa: 'Druga 2', X: '15.94', Y: '45.80',
  TipVrtica: 'Područni', VrstaVrtica: 'Gradski DV'}];
const other = [{...municipal[0], Id: 3, Naziv: 'DAD Sintetički', Adresa: 'Treća 3',
  VrstaVrtica: 'Obrt za čuvanje djece'}];

http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  const send = (status, value, type = 'application/json') => {
    res.writeHead(status, {'Content-Type': type});
    res.end(type === 'application/json' ? JSON.stringify(value) : value);
  };
  if (req.method !== 'GET') return send(501, {error: 'Endpoint not modeled'});
  if (url.pathname === '/api/3/action/package_show') {
    const id = url.searchParams.get('id');
    if (id === 'http-error') return send(503, '<html>upstream unavailable</html>', 'text/html');
    if (id === 'api-error') return send(200, {success: false, error: {__type: 'Not Found Error'}});
    if (id === 'html') return send(200, '<html>proxy error</html>', 'text/html');
    if (id === 'slow') return setTimeout(() => send(200, {success: false}), 250);
    const names = ['djecji-vrtici', municipalId, otherId, 'empty', 'broken-download'];
    if (!names.includes(id)) return send(404, {success: false, error: {message: 'Not found'}});
    return send(200, {success: true, result: {
      id: `package-${id}`, name: id, title: `Synthetic ${id}`, license_id: 'open-license',
      organization: {title: 'Synthetic publisher'}, resources: [
        {id: id === 'djecji-vrtici' ? 'djecji-vrtici' : `resource-${id}`,
         url: `${base}/records/${id}.json`, format: 'JSON', state: 'active'}
      ]
    }});
  }
  if (url.pathname === '/records/djecji-vrtici.json') return send(200, national);
  if (url.pathname === `/records/${municipalId}.json`) return send(200, municipal);
  if (url.pathname === `/records/${otherId}.json`) return send(200, other);
  if (url.pathname === '/records/empty.json') return send(200, []);
  if (url.pathname === '/records/broken-download.json') return send(500, {error: 'failed download'});
  return send(501, {error: 'Endpoint not modeled'});
}).listen(process.env.PORT || 45470);
