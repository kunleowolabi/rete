-- =============================================================================
-- Stage B — est.disco_demand_estimate
-- Landing table for Paper 2's disequilibrium model fitted output: per-DISCO-
-- quarter observed offtake, fitted demand ceiling, fitted supply, regime
-- classification, and the suppressed-demand gap. This is a MODEL OUTPUT,
-- versioned like any other derived artifact — not a raw observation.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS est;

CREATE TABLE est.disco_demand_estimate (
    disco_id             TEXT NOT NULL REFERENCES ref.disco(disco_id),
    period_start          DATE NOT NULL,
    period_end            DATE NOT NULL,

    -- Observed (what actually happened, MWh/h)
    observed_offtake_mwh_per_h   NUMERIC(10,2) NOT NULL,

    -- Model-fitted (disequilibrium model, Fair-Jaffee/Maddala-Nelson Model 1)
    fitted_demand_mwh_per_h      NUMERIC(10,2) NOT NULL,   -- D_hat: unconstrained draw
    fitted_supply_mwh_per_h      NUMERIC(10,2) NOT NULL,   -- S_hat: administratively allocated ceiling
    demand_regime_probability    DOUBLE PRECISION NOT NULL, -- pi_demand: P(demand-constrained)
    suppressed_gap_mwh_per_h     NUMERIC(10,2) NOT NULL,   -- D_hat - Q, the headline number

    -- Provenance / versioning
    model_version         TEXT NOT NULL DEFAULT 'v1_lagos_group_igr_2023_static',
    model_spec_note        TEXT,   -- e.g. 'Lagos-group IGR elasticity, static 2023 IGR (headline)'
    scope_note             TEXT DEFAULT 'Connected-network only. Excludes unconnected population. Demand-side identified by state IGR (formal economic activity), not population.',
    source_document_id     UUID REFERENCES meta.source_document(source_document_id),
    ingestion_run_id       UUID REFERENCES meta.ingestion_run(ingestion_run_id),

    PRIMARY KEY (disco_id, period_start, model_version)
);

-- Serving view: latest gap per DISCO (for the platform's headline display)
CREATE VIEW est.v_latest_disco_gap AS
SELECT DISTINCT ON (e.disco_id)
       e.disco_id, d.name, e.period_start, e.period_end,
       e.observed_offtake_mwh_per_h, e.fitted_demand_mwh_per_h,
       e.suppressed_gap_mwh_per_h, e.demand_regime_probability,
       e.model_version
FROM est.disco_demand_estimate e
JOIN ref.disco d ON d.disco_id = e.disco_id
ORDER BY e.disco_id, e.period_start DESC;