-- Phase 5: SQL Analytics Views
-- Based on BPI Challenge 2017 loan application event log
-- Uses only verified Phase 4 tables (applications, events, etc.)
-- No synthetic extensions or fictional metrics

-- ============================================================================
-- ANALYTICAL VIEWS
-- ============================================================================

-- ============================================================================
-- view_application_metrics: Per-application processing metrics
-- Grain: One row per application
-- ============================================================================
CREATE OR REPLACE VIEW view_application_metrics AS
SELECT
    a.application_id,
    a.application_type,
    a.loan_goal,
    a.requested_amount,
    a.event_count,
    a.first_event_time,
    a.last_event_time,
    EXTRACT(EPOCH FROM (a.last_event_time - a.first_event_time)) / 3600.0 AS processing_hours,
    EXTRACT(EPOCH FROM (a.last_event_time - a.first_event_time)) / 86400.0 AS processing_days,
    -- Lifecycle analysis
    (SELECT COUNT(*) FROM events e
     WHERE e.application_id = a.application_id
     AND e.lifecycle_transition = 'complete') AS complete_count,
    (SELECT COUNT(*) FROM events e
     WHERE e.application_id = a.application_id
     AND e.lifecycle_transition = 'suspend') AS suspend_count,
    (SELECT COUNT(*) FROM events e
     WHERE e.application_id = a.application_id
     AND e.lifecycle_transition = 'withdraw') AS withdraw_count,
    -- Activity counts by prefix
    (SELECT COUNT(*) FROM events e
     WHERE e.application_id = a.application_id
     AND e.activity LIKE 'W_%') AS workflow_activity_count,
    (SELECT COUNT(*) FROM events e
     WHERE e.application_id = a.application_id
     AND e.activity LIKE 'O_%') AS offer_activity_count,
    (SELECT COUNT(*) FROM events e
     WHERE e.application_id = a.application_id
     AND e.activity LIKE 'A_%') AS application_activity_count,
    -- Date components for grouping
    DATE(a.first_event_time) AS first_date,
    EXTRACT(YEAR FROM a.first_event_time) AS first_year,
    EXTRACT(MONTH FROM a.first_event_time) AS first_month,
    EXTRACT(WEEK FROM a.first_event_time) AS first_week
FROM applications a;

-- ============================================================================
-- view_daily_throughput: Daily application volume (simplified)
-- Grain: One row per date where applications started
-- ============================================================================
CREATE OR REPLACE VIEW view_daily_throughput AS
SELECT
    DATE(a.first_event_time) AS date,
    COUNT(*) AS applications_started,
    SUM(a.event_count) AS total_events
FROM applications a
GROUP BY DATE(a.first_event_time)
ORDER BY DATE(a.first_event_time);

-- ============================================================================
-- view_activity_summary: Activity frequency and distribution
-- Grain: One row per activity
-- ============================================================================
CREATE OR REPLACE VIEW view_activity_summary AS
SELECT
    e.activity,
    COUNT(*) AS event_count,
    COUNT(DISTINCT e.application_id) AS unique_applications,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage_of_total,
    CASE
        WHEN e.activity LIKE 'W_%' THEN 'Workflow'
        WHEN e.activity LIKE 'O_%' THEN 'Offer'
        WHEN e.activity LIKE 'A_%' THEN 'Application'
        ELSE 'Other'
    END AS activity_type,
    ROUND(SUM(CASE WHEN e.lifecycle_transition = 'complete' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS complete_pct,
    ROUND(SUM(CASE WHEN e.lifecycle_transition = 'suspend' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS suspend_pct,
    ROUND(SUM(CASE WHEN e.lifecycle_transition = 'withdraw' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS withdraw_pct
FROM events e
GROUP BY e.activity
ORDER BY event_count DESC;

-- ============================================================================
-- view_resource_workload: Resource (user) utilization
-- Grain: One row per resource
-- ============================================================================
CREATE OR REPLACE VIEW view_resource_workload AS
SELECT
    e.resource,
    COUNT(*) AS event_count,
    COUNT(DISTINCT e.application_id) AS applications_handled,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM events WHERE resource IS NOT NULL), 2) AS workload_percentage,
    COUNT(DISTINCT e.activity) AS unique_activities,
    MIN(e.event_timestamp) AS first_event,
    MAX(e.event_timestamp) AS last_event
FROM events e
WHERE e.resource IS NOT NULL
GROUP BY e.resource
ORDER BY event_count DESC;

-- ============================================================================
-- view_application_type_metrics: Metrics by application type
-- Grain: One row per application type
-- ============================================================================
CREATE OR REPLACE VIEW view_application_type_metrics AS
SELECT
    a.application_type,
    COUNT(*) AS application_count,
    ROUND(AVG(a.event_count), 1) AS avg_events_per_application,
    ROUND(AVG(EXTRACT(EPOCH FROM (a.last_event_time - a.first_event_time)) / 3600.0), 2) AS avg_processing_hours,
    MIN(a.first_event_time) AS earliest_application,
    MAX(a.last_event_time) AS latest_application,
    COUNT(DISTINCT a.loan_goal) AS unique_loan_goals,
    ROUND(AVG(a.requested_amount), 2) AS avg_requested_amount
FROM applications a
WHERE a.application_type IS NOT NULL
GROUP BY a.application_type
ORDER BY application_count DESC;

-- ============================================================================
-- view_loan_goal_metrics: Metrics by loan goal
-- Grain: One row per loan goal
-- ============================================================================
CREATE OR REPLACE VIEW view_loan_goal_metrics AS
SELECT
    a.loan_goal,
    COUNT(*) AS application_count,
    ROUND(AVG(a.event_count), 1) AS avg_events,
    ROUND(AVG(EXTRACT(EPOCH FROM (a.last_event_time - a.first_event_time)) / 3600.0), 2) AS avg_processing_hours,
    ROUND(AVG(a.requested_amount), 2) AS avg_requested_amount,
    MIN(a.first_event_time) AS first_date,
    MAX(a.last_event_time) AS last_date
FROM applications a
WHERE a.loan_goal IS NOT NULL
GROUP BY a.loan_goal
ORDER BY application_count DESC;

-- ============================================================================
-- view_lifecycle_transition_metrics: Lifecycle transition analysis
-- Grain: One row per lifecycle transition
-- ============================================================================
CREATE OR REPLACE VIEW view_lifecycle_transition_metrics AS
SELECT
    e.lifecycle_transition,
    COUNT(*) AS event_count,
    COUNT(DISTINCT e.application_id) AS applications_affected,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM events), 2) AS percentage,
    ROUND(SUM(CASE WHEN e.activity LIKE 'W_%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS workflow_pct,
    ROUND(SUM(CASE WHEN e.activity LIKE 'O_%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS offer_pct,
    ROUND(SUM(CASE WHEN e.activity LIKE 'A_%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS application_pct
FROM events e
WHERE e.lifecycle_transition IS NOT NULL
GROUP BY e.lifecycle_transition
ORDER BY event_count DESC;

-- ============================================================================
-- view_event_origin_metrics: Metrics by event origin
-- Grain: One row per event origin
-- ============================================================================
CREATE OR REPLACE VIEW view_event_origin_metrics AS
SELECT
    e.event_origin,
    COUNT(*) AS event_count,
    COUNT(DISTINCT e.application_id) AS applications_affected,
    COUNT(DISTINCT e.activity) AS unique_activities,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM events), 2) AS percentage
FROM events e
WHERE e.event_origin IS NOT NULL
GROUP BY e.event_origin
ORDER BY event_count DESC;

-- ============================================================================
-- view_monthly_summary: Monthly aggregated metrics
-- Grain: One row per year-month
-- ============================================================================
CREATE OR REPLACE VIEW view_monthly_summary AS
SELECT
    EXTRACT(YEAR FROM a.first_event_time) AS year,
    EXTRACT(MONTH FROM a.first_event_time) AS month,
    TO_CHAR(DATE_TRUNC('month', a.first_event_time), 'YYYY-MM') AS year_month,
    COUNT(*) AS applications,
    SUM(a.event_count) AS total_events,
    ROUND(AVG(a.event_count), 1) AS avg_events_per_app,
    ROUND(AVG(EXTRACT(EPOCH FROM (a.last_event_time - a.first_event_time)) / 86400.0), 2) AS avg_processing_days,
    COUNT(DISTINCT a.application_type) AS application_types,
    COUNT(DISTINCT a.loan_goal) AS loan_goals
FROM applications a
GROUP BY EXTRACT(YEAR FROM a.first_event_time), EXTRACT(MONTH FROM a.first_event_time), DATE_TRUNC('month', a.first_event_time)
ORDER BY year, month;

-- ============================================================================
-- view_weekly_summary: Weekly aggregated metrics
-- Grain: One row per week (by application start date)
-- ============================================================================
CREATE OR REPLACE VIEW view_weekly_summary AS
SELECT
    EXTRACT(YEAR FROM a.first_event_time) AS year,
    EXTRACT(WEEK FROM a.first_event_time) AS week,
    DATE_TRUNC('week', a.first_event_time) AS week_start,
    COUNT(DISTINCT a.application_id) AS applications,
    SUM(a.event_count) AS events
FROM applications a
GROUP BY EXTRACT(YEAR FROM a.first_event_time), EXTRACT(WEEK FROM a.first_event_time), DATE_TRUNC('week', a.first_event_time)
ORDER BY week_start;

-- ============================================================================
-- view_event_sequence: Event sequence per application (for process mining)
-- Grain: One row per event
-- ============================================================================
CREATE OR REPLACE VIEW view_event_sequence AS
SELECT
    e.event_id,
    e.application_id,
    e.activity,
    e.event_timestamp,
    e.resource,
    e.lifecycle_transition,
    e.event_origin,
    ROW_NUMBER() OVER (PARTITION BY e.application_id ORDER BY e.event_timestamp, e.event_id) AS event_sequence,
    LEAD(e.activity) OVER (PARTITION BY e.application_id ORDER BY e.event_timestamp, e.event_id) AS next_activity,
    LAG(e.activity) OVER (PARTITION BY e.application_id ORDER BY e.event_timestamp, e.event_id) AS prev_activity,
    LEAD(e.event_timestamp) OVER (PARTITION BY e.application_id ORDER BY e.event_timestamp, e.event_id) - e.event_timestamp AS time_to_next
FROM events e;

-- ============================================================================
-- view_processing_time_buckets: Applications by processing time bucket
-- Grain: One row per time bucket
-- ============================================================================
CREATE OR REPLACE VIEW view_processing_time_buckets AS
SELECT
    bucket,
    COUNT(*) AS application_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage,
    ROUND(AVG(event_count), 1) AS avg_events
FROM (
    SELECT
        a.application_id,
        a.event_count,
        CASE
            WHEN EXTRACT(EPOCH FROM (a.last_event_time - a.first_event_time)) / 3600.0 < 1 THEN '< 1 hour'
            WHEN EXTRACT(EPOCH FROM (a.last_event_time - a.first_event_time)) / 3600.0 < 24 THEN '1-24 hours'
            WHEN EXTRACT(EPOCH FROM (a.last_event_time - a.first_event_time)) / 86400.0 < 7 THEN '1-7 days'
            WHEN EXTRACT(EPOCH FROM (a.last_event_time - a.first_event_time)) / 86400.0 < 30 THEN '1-4 weeks'
            ELSE '> 4 weeks'
        END AS bucket
    FROM applications a
) sub
GROUP BY bucket
ORDER BY
    CASE bucket
        WHEN '< 1 hour' THEN 1
        WHEN '1-24 hours' THEN 2
        WHEN '1-7 days' THEN 3
        WHEN '1-4 weeks' THEN 4
        ELSE 5
    END;

-- ============================================================================
-- view_offer_analysis: Offer-related metrics (uses events table only)
-- Grain: One row per offer status
-- ============================================================================
CREATE OR REPLACE VIEW view_offer_analysis AS
SELECT
    offer_status,
    COUNT(*) AS event_count,
    COUNT(DISTINCT application_id) AS applications
FROM (
    SELECT
        application_id,
        CASE
            WHEN activity = 'O_Created' THEN 'Created'
            WHEN activity = 'O_Create Offer' THEN 'Created'
            WHEN activity IN ('O_Sent (mail and online)', 'O_Sent (online only)') THEN 'Sent'
            WHEN activity = 'O_Accepted' THEN 'Accepted'
            WHEN activity = 'O_Returned' THEN 'Returned'
            WHEN activity = 'O_Refused' THEN 'Refused'
            WHEN activity = 'O_Cancelled' THEN 'Cancelled'
            ELSE 'Other'
        END AS offer_status
    FROM events
    WHERE activity LIKE 'O_%'
) sub
GROUP BY offer_status
ORDER BY event_count DESC;

-- ============================================================================
-- MATERIALIZED VIEWS (for heavy aggregations - simplified without generate_series)
-- ============================================================================

-- ============================================================================
-- mv_activity_summary: Pre-computed activity counts
-- Refresh: Weekly or on demand
-- ============================================================================
CREATE MATERIALIZED VIEW mv_activity_summary AS
SELECT
    e.activity,
    COUNT(*) AS event_count,
    COUNT(DISTINCT e.application_id) AS unique_applications,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage_of_total,
    CASE
        WHEN e.activity LIKE 'W_%' THEN 'Workflow'
        WHEN e.activity LIKE 'O_%' THEN 'Offer'
        WHEN e.activity LIKE 'A_%' THEN 'Application'
        ELSE 'Other'
    END AS activity_type
FROM events e
GROUP BY e.activity
ORDER BY event_count DESC;

CREATE UNIQUE INDEX idx_mv_activity ON mv_activity_summary(activity);

-- ============================================================================
-- mv_resource_workload: Pre-computed resource metrics
-- Refresh: Weekly or on demand
-- ============================================================================
CREATE MATERIALIZED VIEW mv_resource_workload AS
SELECT
    e.resource,
    COUNT(*) AS event_count,
    COUNT(DISTINCT e.application_id) AS applications_handled,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM events WHERE resource IS NOT NULL), 2) AS workload_percentage,
    COUNT(DISTINCT e.activity) AS unique_activities
FROM events e
WHERE e.resource IS NOT NULL
GROUP BY e.resource
ORDER BY event_count DESC;

CREATE UNIQUE INDEX idx_mv_resource ON mv_resource_workload(resource);

-- ============================================================================
-- mv_monthly_summary: Pre-computed monthly metrics
-- Refresh: Monthly or on demand
-- ============================================================================
CREATE MATERIALIZED VIEW mv_monthly_summary AS
SELECT
    EXTRACT(YEAR FROM a.first_event_time) AS year,
    EXTRACT(MONTH FROM a.first_event_time) AS month,
    TO_CHAR(DATE_TRUNC('month', a.first_event_time), 'YYYY-MM') AS year_month,
    COUNT(*) AS applications,
    SUM(a.event_count) AS total_events,
    ROUND(AVG(a.event_count), 1) AS avg_events_per_app,
    ROUND(AVG(EXTRACT(EPOCH FROM (a.last_event_time - a.first_event_time)) / 86400.0), 2) AS avg_processing_days
FROM applications a
GROUP BY EXTRACT(YEAR FROM a.first_event_time), EXTRACT(MONTH FROM a.first_event_time), DATE_TRUNC('month', a.first_event_time)
ORDER BY year, month;

CREATE UNIQUE INDEX idx_mv_monthly ON mv_monthly_summary(year, month);

-- ============================================================================
-- mv_application_type_summary: Pre-computed application type metrics
-- Refresh: Weekly or on demand
-- ============================================================================
CREATE MATERIALIZED VIEW mv_application_type_summary AS
SELECT
    a.application_type,
    COUNT(*) AS application_count,
    ROUND(AVG(a.event_count), 1) AS avg_events_per_application,
    ROUND(AVG(EXTRACT(EPOCH FROM (a.last_event_time - a.first_event_time)) / 3600.0), 2) AS avg_processing_hours,
    ROUND(AVG(a.requested_amount), 2) AS avg_requested_amount
FROM applications a
WHERE a.application_type IS NOT NULL
GROUP BY a.application_type;

CREATE UNIQUE INDEX idx_mv_app_type ON mv_application_type_summary(application_type);

-- ============================================================================
-- Record migration
-- ============================================================================
INSERT INTO schema_versions (version, description)
VALUES ('002', 'Analytics views: application_metrics, daily_throughput, activity_summary, resource_workload, materialized views')
ON CONFLICT (version) DO NOTHING;