-- Phase 9: Predictive SLA Risk Analytics Schema
-- Table: application_predictions
-- Views: view_predictive_sla_risk (historical), view_predictive_sla_risk_latest (latest per application)

-- ============================================================================
-- APPLICATION PREDICTIONS TABLE
-- Stores batch ML predictions for SLA risk classification and cycle-time regression
-- Grain: One record per application per model version
-- ============================================================================
CREATE TABLE IF NOT EXISTS application_predictions (
    application_id VARCHAR(255) NOT NULL REFERENCES applications(application_id) ON DELETE CASCADE,
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    risk_class SMALLINT NOT NULL CHECK (risk_class IN (0, 1)),
    risk_probability NUMERIC(6, 4) NOT NULL CHECK (risk_probability >= 0.0000 AND risk_probability <= 1.0000),
    predicted_processing_days NUMERIC(10, 2) NOT NULL CHECK (predicted_processing_days >= 0.00),
    scored_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (application_id, model_version)
);

-- Indexes for prediction query performance
CREATE INDEX IF NOT EXISTS idx_app_preds_model_version ON application_predictions(model_version);
CREATE INDEX IF NOT EXISTS idx_app_preds_risk_class ON application_predictions(risk_class);
CREATE INDEX IF NOT EXISTS idx_app_preds_scored_at ON application_predictions(scored_at);

-- ============================================================================
-- view_predictive_sla_risk: Historical View containing all model predictions
-- Grain: One row per application per model version
-- ============================================================================
CREATE OR REPLACE VIEW view_predictive_sla_risk AS
SELECT
    a.application_id,
    a.application_type,
    a.loan_goal,
    a.requested_amount,
    a.first_event_time,
    a.last_event_time,
    a.status AS application_status,
    m.processing_hours AS actual_processing_hours,
    m.processing_days AS actual_processing_days,
    a.event_count,
    p.model_version,
    p.model_type,
    p.risk_class AS predicted_risk_class,
    CASE
        WHEN p.risk_class = 1 THEN 'High Risk'
        ELSE 'Low Risk'
    END AS predicted_risk_label,
    p.risk_probability AS predicted_risk_probability,
    p.predicted_processing_days,
    CASE
        WHEN a.status IN ('complete', 'COMPLETED', 'COMPLETE') OR m.complete_count > 0 THEN
            ROUND((m.processing_days - p.predicted_processing_days)::NUMERIC, 2)
        ELSE NULL
    END AS processing_days_error,
    p.scored_at
FROM applications a
JOIN view_application_metrics m ON a.application_id = m.application_id
JOIN application_predictions p ON a.application_id = p.application_id;

-- ============================================================================
-- view_predictive_sla_risk_latest: Single-Row View returning latest ML prediction per case
-- Grain: One row per application (most recent scoring timestamp & version)
-- ============================================================================
CREATE OR REPLACE VIEW view_predictive_sla_risk_latest AS
WITH ranked_predictions AS (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            PARTITION BY p.application_id
            ORDER BY p.scored_at DESC, p.model_version DESC
        ) AS rank_idx
    FROM application_predictions p
)
SELECT
    a.application_id,
    a.application_type,
    a.loan_goal,
    a.requested_amount,
    a.first_event_time,
    a.last_event_time,
    a.status AS application_status,
    m.processing_hours AS actual_processing_hours,
    m.processing_days AS actual_processing_days,
    a.event_count,
    rp.model_version,
    rp.model_type,
    rp.risk_class AS predicted_risk_class,
    CASE
        WHEN rp.risk_class = 1 THEN 'High Risk'
        ELSE 'Low Risk'
    END AS predicted_risk_label,
    rp.risk_probability AS predicted_risk_probability,
    rp.predicted_processing_days,
    CASE
        WHEN a.status IN ('complete', 'COMPLETED', 'COMPLETE') OR m.complete_count > 0 THEN
            ROUND((m.processing_days - rp.predicted_processing_days)::NUMERIC, 2)
        ELSE NULL
    END AS processing_days_error,
    rp.scored_at
FROM applications a
JOIN view_application_metrics m ON a.application_id = m.application_id
JOIN ranked_predictions rp ON a.application_id = rp.application_id AND rp.rank_idx = 1;

-- ============================================================================
-- Record migration version
-- ============================================================================
INSERT INTO schema_versions (version, description)
VALUES ('003', 'Phase 9: Predictive SLA risk application_predictions table and analytics views')
ON CONFLICT (version) DO NOTHING;
