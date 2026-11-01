# Local CKAN simulation

This mock follows the CKAN Action API contract and the metadata fixtures in
`tests/fixtures/`. Its kindergarten rows are synthetic. The CLI is signed out,
so an owner's published mock was not searched. Orbit discovery only found
other countries' CKAN installations; Croatian behavior was checked against
the official CKAN documentation and the three live catalogues instead.

Run locally (Postman CLI 1.77.0 was used):

```sh
postman simulation run postman/simulations/ckan/ckan.sim.yaml --port 45471 --no-history --output ndjson
```

In another terminal:

```sh
export KIDSIC_CKAN_SIMULATION_URL=http://127.0.0.1:45471/ckan
uv run python -m unittest discover -s tests -p 'test_ckan_http.py' -v
CKAN_BASE_URL="$KIDSIC_CKAN_SIMULATION_URL" CKAN_ZAGREB_BASE_URL="$KIDSIC_CKAN_SIMULATION_URL" \
  uv run kidsic-sync-kindergartens --dry-run
```

The mock's resource URLs use this port by default. Export the same
`KIDSIC_CKAN_SIMULATION_URL` before starting the simulation if changing it.
The simulation runs only on the local machine and is never pushed or deployed.
Its log must show requests to both `package_show` and `/records/` to prove
that discovery and download were exercised. The context document distinguishes
live provider evidence from simulated caller behavior.
