# Rete — Nigeria Electricity Intelligence Platform

Rete measures Nigeria's electricity supply-demand gap spatially: what is
generated, what is delivered to each distribution company, and how far
that falls short of modelled demand, at the resolution the underlying
data actually supports.

**Live platform:** https://explorerete.com

This repository contains the full stack behind it: the data pipeline
(scrapers, loaders, schema), the API, and the frontend. It is the
supply-side and delivery infrastructure for the demand estimate produced
in a separate working paper (see below).

## What this is

Rete answers two questions existing sources leave separate: how much
power is Nigeria's grid delivering right now, and how much would it
deliver if the network's own rationing were removed. It does not
estimate total national demand, and it does not cover people with no
grid connection — see the platform's own Data page for the exact scope
of every figure shown.

The platform combines a live supply-side feed (hourly per-plant
generation and per-DISCO load allocation, scraped and loaded
automatically), a modelled demand ceiling (the fitted output of
[`disequilibrium_model_paper`](https://github.com/kunleowolabi/disequilibrium_model_paper),
154 DISCO-quarters, 2022Q4–2026Q1), and a spatial reference layer (GRID3
boundaries, OSM-derived transmission infrastructure, a DISCO franchise
crosswalk reconciling three independently-maintained plant naming
schemes).

## Stack

- **Infrastructure:** Terraform, Aurora Serverless v2 (PostGIS), Lambda,
  API Gateway, S3, CloudFront — all in `eu-west-1`, one region.
- **Ingestion:** two hourly scrapers write raw JSON to S3; an
  S3-triggered Lambda loads it into Aurora automatically. One-off
  reference data (GRID3, NERC, OSM, the demand panel) is loaded manually
  via scripts in `pipelines/loaders/`.
- **API:** one Lambda, one handler file per endpoint, dispatched by
  `pipelines/api/router.py`.
- **Frontend:** React + Vite, MapLibre for the map, deployed as a static
  site behind CloudFront.

Some infrastructure decisions aren't obvious from the code alone — see
`docs/architecture.md`.

## Running it locally

```bash
# Frontend
cd rete-frontend
npm install
npm run dev
```

Set `BASE_URL` in `rete-frontend/src/api/client.js` to a running API
instance first.

The loaders in `pipelines/loaders/` each connect to Aurora directly and
can be run individually against a tunnel to the database; see each
script's own docstring for what it expects.

## Data provenance

| Layer | Source | Cadence |
|---|---|---|
| Plant generation, DISCO load allocation | niggrid.org (Nigerian System Operator) | Hourly, automated |
| NERC commercial/operational data | NERC quarterly reports | Manual, per report |
| Suppressed demand estimate | `kunleowolabi/disequilibrium_model_paper` | Fixed panel, 2022Q4–2026Q1 |
| Administrative boundaries | GRID3 | Static |
| Transmission infrastructure | OpenStreetMap, via Geofabrik | Snapshot |
| Mini-grid site inventory | Nigeria SE4ALL | Static, last updated 2020 |

Every figure served by the API traces back to a row in `meta.source` and
`meta.ingestion_run`.

## Status

This is a first public version, not a complete national demand picture.
The demand estimate covers the connected network only. Eko, Ikeja, and
Ibadan's DISCO boundaries are approximated at full-state resolution
pending real franchise polygons. Medium- and low-voltage distribution
infrastructure is sparsely mapped in the available OpenStreetMap data.
These limitations are stated on the platform's own Data page as well as
here.

Open work is tracked in GitHub Issues. Contributions welcome.

## Related work

- [`disequilibrium_model_paper`](https://github.com/kunleowolabi/disequilibrium_model_paper) — the demand model this platform serves
- [`electricity-allocation`](https://github.com/kunleowolabi/electricity-allocation) — a related cross-country allocation method, not currently applied to Nigeria

## License

MIT License — see `LICENSE`. GRID3, NERC, OpenStreetMap, and SE4ALL data
retain whatever terms those providers apply to their own releases.

## Citation

Owolabi, A. (2026) *Rete: Nigeria Electricity Intelligence Platform*.
Available at: https://github.com/kunleowolabi/rete (Accessed: September 2026).

```
@misc{owolabi2026rete,
  title  = {Rete: Nigeria Electricity Intelligence Platform},
  author = {Owolabi, Ayokunle},
  year   = {2026},
  month  = {September},
  url    = {https://github.com/kunleowolabi/rete}
}
```