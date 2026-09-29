-- =============================================================================
-- NEIP Stage A — Phase 1: Supply Truth & Provenance
-- Target: Aurora PostgreSQL 16 + PostGIS
-- Run this once against a fresh database.
-- =============================================================================
--
-- 13 tables across 4 namespaces:
--   meta (3)  — provenance: where every number came from
--   stg  (1)  — staging: raw payloads before typing
--   ref  (6)  — reference: the entities (states, LGAs, plants)
--   obs  (3)  — observations: what was actually reported
--
-- Design rules (from scope_review.md):
--   1. Observed and derived data never mix (obs.* vs model.* in later stages)
--   2. Every figure traces to a source document and an ingestion run
--   3. The LGA is the spatial spine — everything resolves to 774 LGA codes
--   4. NULL means unreported; 0.00 means reported-as-zero
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS ref;
CREATE SCHEMA IF NOT EXISTS obs;


-- =============================================================================
-- meta — provenance
-- =============================================================================

-- One row per data source organisation/feed.
-- Licence here is a DEFAULT — the authoritative licence lives on source_document,
-- because a single source can publish datasets under different licences
-- (eval 01 F4: GRID3 uses CC-BY for boundaries and CC-BY-SA for roads).
CREATE TABLE meta.source (
    source_id       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    organisation    TEXT,
    url             TEXT,
    tier            SMALLINT,
    licence_default TEXT,
    access_method   TEXT,
    cadence         TEXT,
    notes           TEXT
);

-- One row per artefact: a PDF, a scraped page snapshot, a shapefile release.
-- This is the provenance anchor — every observation points here.
CREATE TABLE meta.source_document (
    source_document_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id           TEXT NOT NULL REFERENCES meta.source(source_id),
    title               TEXT,
    document_type       TEXT,
    -- nature: what kind of data is this at its origin?
    -- 'observed'     = direct measurement or official report (NERC, niggrid)
    -- 'modelled'     = output of a model (GRID3 population, HREA)
    -- 'crowdsourced' = community-contributed (OSM)
    -- 'compiled'     = assembled from multiple sources (Sahara report)
    nature              TEXT,
    licence             TEXT,
    published_at        DATE,
    retrieved_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    s3_uri              TEXT,
    checksum            TEXT,
    page_count          INTEGER,
    extraction_status   TEXT,
    extraction_notes    TEXT,

    CONSTRAINT chk_nature CHECK (
        nature IS NULL
        OR nature IN ('observed','modelled','crowdsourced','compiled')
    )
);

CREATE INDEX ix_source_document_source
    ON meta.source_document(source_id, published_at DESC);

-- Dedupe: don't re-extract an unchanged document.
CREATE UNIQUE INDEX ux_source_document_checksum
    ON meta.source_document(checksum)
    WHERE checksum IS NOT NULL;

-- One row per ingestion attempt. The audit trail.
CREATE TABLE meta.ingestion_run (
    ingestion_run_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id           TEXT NOT NULL REFERENCES meta.source(source_id),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ,
    status              TEXT NOT NULL DEFAULT 'running',
    rows_written        INTEGER,
    s3_raw_uri          TEXT,
    error_detail        TEXT,

    CONSTRAINT chk_run_status CHECK (
        status IN ('running','success','partial','failed')
    )
);


-- =============================================================================
-- stg — staging
-- =============================================================================

-- Raw payloads land here before typing/validation.
-- The parallel of the S3 raw bucket, inside the database.
-- Retained for audit; prunable after confirmed processing.
CREATE TABLE stg.raw_payload (
    raw_payload_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingestion_run_id    UUID NOT NULL REFERENCES meta.ingestion_run(ingestion_run_id),
    source_id           TEXT NOT NULL REFERENCES meta.source(source_id),
    payload             JSONB NOT NULL,
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at        TIMESTAMPTZ,
    processing_error    TEXT
);

-- Find unprocessed payloads quickly.
CREATE INDEX ix_stg_unprocessed
    ON stg.raw_payload(source_id, captured_at)
    WHERE processed_at IS NULL;


-- =============================================================================
-- ref — reference / dimension data
-- =============================================================================

-- 37 rows: 36 states + FCT.
CREATE TABLE ref.state (
    state_code      TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    zone            TEXT          -- geopolitical zone: 'South West', 'North Central', etc.
);

-- 774 rows from GRID3. The spine — everything else joins to this.
CREATE TABLE ref.lga (
    lga_code        TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    state_code      TEXT NOT NULL REFERENCES ref.state(state_code),
    area_km2        NUMERIC(12,3),
    source_document_id UUID REFERENCES meta.source_document(source_document_id)
);

CREATE INDEX ix_lga_state ON ref.lga(state_code);

-- ~8-10 rows: GenCo owner groups.
CREATE TABLE ref.genco (
    genco_id        TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    ownership       TEXT          -- 'private' | 'ndphc' | 'ipp' | 'state'
);

-- ~33-35 rows: individual power plants.
-- reporting_status handles the universe problem:
--   niggrid lists 33 (incl. non-operational AES, Gbarain)
--   NERC reports 28 (excludes them)
--   Sahara lists 35
--   Elec-T shows 30
-- These aren't errors — they're different definitions. This field records
-- the plant's actual operational state.
CREATE TABLE ref.plant (
    plant_id        TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    genco_id        TEXT REFERENCES ref.genco(genco_id),
    lga_code        TEXT REFERENCES ref.lga(lga_code),
    fuel_type       TEXT,          -- 'gas' | 'hydro' | 'steam' | 'gas_steam' | 'solar'
    plant_type      TEXT,          -- 'genco' | 'ipp' | 'nipp'
    reporting_status TEXT,         -- 'active' | 'non_operational' | 'decommissioned' | 'island_mode'
    commissioned_on DATE,
    is_grid_connected BOOLEAN NOT NULL DEFAULT TRUE,
    location        GEOGRAPHY(POINT, 4326),
    source_document_id UUID REFERENCES meta.source_document(source_document_id)
);

CREATE INDEX ix_plant_lga  ON ref.plant(lga_code);
CREATE INDEX ix_plant_fuel ON ref.plant(fuel_type);

-- Installed capacity PER SOURCE — because sources disagree.
-- The same plant can carry 1,320 MW per NERC and a different figure per Sahara.
-- The reconciliation report documents which numbers exist, not which is "right."
CREATE TABLE ref.plant_capacity (
    plant_id            TEXT NOT NULL REFERENCES ref.plant(plant_id),
    source_document_id  UUID NOT NULL REFERENCES meta.source_document(source_document_id),
    installed_mw        NUMERIC(10,2) NOT NULL,
    available_mw        NUMERIC(10,2),
    capacity_type       TEXT,      -- 'nameplate' | 'available' | 'dependable'
    as_of_date          DATE,
    PRIMARY KEY (plant_id, source_document_id)
);

-- Name variants across sources.
-- niggrid says "AFAM VI (GAS/STEAM)", NERC says "Afam VI",
-- OSM says "Afam VI Power Station", Sahara says "WAGL OML 11 - Afam VI".
-- Without this table, the same plant appears as four entities and every
-- per-plant aggregate is silently wrong.
CREATE TABLE ref.plant_alias (
    plant_id    TEXT NOT NULL REFERENCES ref.plant(plant_id),
    source_id   TEXT NOT NULL REFERENCES meta.source(source_id),
    alias       TEXT NOT NULL,
    PRIMARY KEY (source_id, alias)
);


-- =============================================================================
-- obs — observations (append-only, from sources)
-- =============================================================================

-- Per-plant MW per hour from niggrid.
--
-- Scraped once at :55 each hour — the point of maximum reporting completeness.
-- We store exactly what the dashboard shows. A 0.00 means the dashboard showed
-- zero — either the plant hasn't reported yet or it genuinely generated nothing.
-- We don't distinguish the two in storage because the source doesn't.
--
-- reporting_gencos (from the header: "as reported by N Gencos") tells us how
-- complete the overall picture is at capture time — quality context for analysis,
-- not a storage interpretation rule.
CREATE TABLE obs.niggrid_plant_hourly (
    plant_id            TEXT NOT NULL REFERENCES ref.plant(plant_id),
    observed_hour       TIMESTAMPTZ NOT NULL,   -- the hour the dashboard displays ("as at HH:00")
    generation_mw       NUMERIC(10,2) NOT NULL, -- exactly what the dashboard showed
    reporting_gencos    SMALLINT,               -- how many GenCos had reported at capture time
    dashboard_total_mw  NUMERIC(10,2),          -- the stated system total from the header
    captured_at         TIMESTAMPTZ NOT NULL,    -- when WE scraped (vs when THEY say it's for)
    ingestion_run_id    UUID NOT NULL REFERENCES meta.ingestion_run(ingestion_run_id),
    PRIMARY KEY (plant_id, observed_hour)
) PARTITION BY RANGE (observed_hour);

-- Partitions created ahead by a maintenance job or manually per month.
-- Example for July 2026:
CREATE TABLE obs.niggrid_plant_hourly_2026_07
    PARTITION OF obs.niggrid_plant_hourly
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');

CREATE TABLE obs.niggrid_plant_hourly_2026_08
    PARTITION OF obs.niggrid_plant_hourly
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');

-- Per-plant quarterly performance from NERC (Tables 1 & 2 of the quarterly report).
-- Separate from niggrid because: different source, different cadence (quarterly vs hourly),
-- different columns (PAF, energy sent out — niggrid doesn't provide these).
--
-- PK includes source_document_id because NERC revises prior-quarter figures
-- inside the new report (eval 04 F3: the Ibadan correction). Two reports can
-- state different values for the same plant + quarter.
CREATE TABLE obs.nerc_plant_quarterly (
    plant_id            TEXT NOT NULL REFERENCES ref.plant(plant_id),
    period_start        DATE NOT NULL,         -- first day of quarter
    period_end          DATE NOT NULL,         -- last day of quarter
    installed_mw        NUMERIC(10,2),
    available_mw        NUMERIC(10,2),
    paf_pct             NUMERIC(6,2),          -- plant availability factor (%)
    avg_hourly_gen_mw   NUMERIC(10,2),         -- average hourly generation (from Table 2)
    energy_sent_out_mw  NUMERIC(10,2),         -- energy sent out (MW, from Table 2)
    grid_share_pct      NUMERIC(6,2),
    nerc_table_ref      TEXT,                  -- 'table_1' | 'table_2' — which NERC table this came from
    source_document_id  UUID NOT NULL REFERENCES meta.source_document(source_document_id),
    ingestion_run_id    UUID NOT NULL REFERENCES meta.ingestion_run(ingestion_run_id),
    PRIMARY KEY (plant_id, period_start, source_document_id)
);

-- Per-DisCo quarterly performance from NERC (Tables 4-9, 18).
-- Covers: energy offtake, billing, collection, ATC&C, metering.
--
-- This is deliberately wider than strictly normalised — NERC's table structure
-- changes across vintages (eval 04 F5: billing efficiency split in Q2 2025),
-- so modelling each NERC table as its own DB table would require schema changes
-- every time NERC reorganises. Instead: one row per DisCo per quarter per report,
-- with nullable columns for metrics that not all vintages provide.
-- nerc_tables_ref records which NERC tables contributed to this row.
CREATE TABLE obs.nerc_disco_quarterly (
    disco_id            TEXT NOT NULL,          -- FK added in Stage B when ref.disco is created
    period_start        DATE NOT NULL,
    period_end          DATE NOT NULL,
    -- Operational (Table 4)
    energy_offtake_mwh_per_h   NUMERIC(10,2),
    offtake_performance_pct    NUMERIC(6,2),
    -- Commercial (Tables 5-8)
    energy_received_gwh        NUMERIC(12,2),
    energy_billed_gwh          NUMERIC(12,2),
    billing_efficiency_pct     NUMERIC(6,2),
    energy_accounting_eff_pct  NUMERIC(6,2),   -- only from Q2 2025 onward (eval 04 F5)
    revenue_billed_ngn_bn      NUMERIC(14,2),
    revenue_collected_ngn_bn   NUMERIC(14,2),
    collection_efficiency_pct  NUMERIC(6,2),
    -- Loss (Table 9)
    myto_target_atcc_pct       NUMERIC(6,2),
    actual_atcc_pct            NUMERIC(6,2),
    -- Metering (Table 18)
    customers_active           INTEGER,
    customers_metered          INTEGER,
    metering_rate_pct          NUMERIC(6,2),
    -- Provenance
    nerc_tables_ref            TEXT,            -- e.g. 'tables_4,5,6,7,8,9,18'
    source_document_id  UUID NOT NULL REFERENCES meta.source_document(source_document_id),
    ingestion_run_id    UUID NOT NULL REFERENCES meta.ingestion_run(ingestion_run_id),
    PRIMARY KEY (disco_id, period_start, source_document_id)
);


-- =============================================================================
-- Serving views (Phase 1)
-- =============================================================================

-- Latest generation per plant (most recent hour captured).
-- reporting_gencos is exposed so consumers can judge completeness themselves.
CREATE VIEW obs.v_latest_plant_generation AS
SELECT DISTINCT ON (n.plant_id)
       n.plant_id,
       p.name,
       p.fuel_type,
       n.observed_hour,
       n.generation_mw,
       n.reporting_gencos,
       n.dashboard_total_mw,
       n.captured_at
FROM   obs.niggrid_plant_hourly n
JOIN   ref.plant p ON p.plant_id = n.plant_id
ORDER  BY n.plant_id, n.observed_hour DESC;

-- Latest NERC quarterly per plant (most recently published report's figures).
CREATE VIEW obs.v_latest_nerc_plant AS
SELECT DISTINCT ON (q.plant_id)
       q.plant_id,
       p.name,
       q.period_start,
       q.period_end,
       q.installed_mw,
       q.available_mw,
       q.paf_pct,
       q.avg_hourly_gen_mw,
       q.source_document_id
FROM   obs.nerc_plant_quarterly q
JOIN   ref.plant p ON p.plant_id = q.plant_id
ORDER  BY q.plant_id, q.period_start DESC, q.source_document_id DESC;

-- Latest NERC quarterly per DisCo.
CREATE VIEW obs.v_latest_nerc_disco AS
SELECT DISTINCT ON (d.disco_id)
       d.disco_id,
       d.period_start,
       d.period_end,
       d.energy_received_gwh,
       d.actual_atcc_pct,
       d.customers_active,
       d.metering_rate_pct,
       d.source_document_id
FROM   obs.nerc_disco_quarterly d
ORDER  BY d.disco_id, d.period_start DESC, d.source_document_id DESC;


-- =============================================================================
-- Seed data: sources
-- =============================================================================

INSERT INTO meta.source (source_id, name, organisation, url, tier, licence_default, access_method, cadence) VALUES
    ('niggrid',         'NISO Grid Dashboard',      'Nigerian Independent System Operator', 'https://niggrid.org', 1, 'public',   'scrape',   'hourly'),
    ('nerc_quarterly',  'NERC Quarterly Report',     'Nigerian Electricity Regulatory Commission', 'https://nerc.gov.ng', 2, 'public', 'pdf', 'quarterly'),
    ('nerc_factsheet',  'NERC Monthly Factsheet',    'Nigerian Electricity Regulatory Commission', 'https://nerc.gov.ng', 2, 'public', 'pdf', 'monthly'),
    ('grid3',           'GRID3 Nigeria',             'GRID3 / Columbia CIESIN',             'https://data.grid3.org', 1, 'CC-BY-4.0', 'download', 'static'),
    ('worldpop',        'WorldPop',                  'University of Southampton',            'https://worldpop.org', 1, 'CC-BY-4.0', 'download', 'static'),
    ('viirs',           'NOAA VIIRS DNB Monthly',    'NOAA / Colorado School of Mines',      'https://eogdata.mines.edu', 1, 'public domain', 'download', 'monthly'),
    ('hrea',            'HREA',                      'University of Michigan',               'https://planetarycomputer.microsoft.com', 1, 'open access', 'api', 'annual'),
    ('osm',             'OpenStreetMap (Geofabrik)',  'OpenStreetMap contributors',           'https://download.geofabrik.de', 3, 'ODbL', 'download', 'snapshot'),
    ('sahara_report',   'Sahara Annual Power Report', 'Sahara Power Group',                  'https://sahara-group.com', 5, 'proprietary', 'pdf', 'annual');
