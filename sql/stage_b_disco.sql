-- =============================================================================
-- Stage B — ref.disco
-- Adds the DISCO reference table and wires the FK that obs.nerc_disco_quarterly
-- was built to accept (see comment on that table in stage_a.sql).
-- =============================================================================

CREATE TABLE ref.disco (
    disco_id            TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    states_served       TEXT[] NOT NULL,
    ring_fenced_note     TEXT,              -- for partial-state franchises like Aba
    source_document_id  UUID REFERENCES meta.source_document(source_document_id)
);

ALTER TABLE obs.nerc_disco_quarterly
    ADD CONSTRAINT fk_nerc_disco_quarterly_disco
    FOREIGN KEY (disco_id) REFERENCES ref.disco(disco_id);