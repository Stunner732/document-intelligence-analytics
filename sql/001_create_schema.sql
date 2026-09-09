-- Database Schema for Document Intelligence Analytics
-- Based on BPI Challenge 2017 event log structure
-- Phase 4: Initial schema migration

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- APPLICATION TABLE (trace-level)
-- Represents each loan application/case in the event log
-- ============================================================================
CREATE TABLE IF NOT EXISTS applications (
    application_id VARCHAR(255) PRIMARY KEY,
    application_type VARCHAR(100),
    loan_goal VARCHAR(255),
    requested_amount NUMERIC(15, 2),
    first_event_time TIMESTAMP WITH TIME ZONE,
    last_event_time TIMESTAMP WITH TIME ZONE,
    event_count INTEGER DEFAULT 0,
    status VARCHAR(50),
    event_origin VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_loan_goal ON applications(loan_goal);
CREATE INDEX IF NOT EXISTS idx_applications_first_event_time ON applications(first_event_time);
CREATE INDEX IF NOT EXISTS idx_applications_last_event_time ON applications(last_event_time);

-- ============================================================================
-- EVENTS TABLE (event-level)
-- Stores each event in the process execution
-- ============================================================================
CREATE TABLE IF NOT EXISTS events (
    event_id VARCHAR(255) PRIMARY KEY,
    application_id VARCHAR(255) NOT NULL REFERENCES applications(application_id) ON DELETE CASCADE,
    activity VARCHAR(255) NOT NULL,
    event_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    resource VARCHAR(255),
    lifecycle_transition VARCHAR(50),
    action VARCHAR(255),
    event_origin VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for event queries
CREATE INDEX IF NOT EXISTS idx_events_application_id ON events(application_id);
CREATE INDEX IF NOT EXISTS idx_events_activity ON events(activity);
CREATE INDEX IF NOT EXISTS idx_events_event_timestamp ON events(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_events_resource ON events(resource);
CREATE INDEX IF NOT EXISTS idx_events_lifecycle_transition ON events(lifecycle_transition);

-- Composite index for time-range queries per application
CREATE INDEX IF NOT EXISTS idx_events_app_time ON events(application_id, event_timestamp);

-- ============================================================================
-- OFFERS TABLE
-- BPI 2017 supports multiple offers per application
-- ============================================================================
CREATE TABLE IF NOT EXISTS offers (
    offer_id VARCHAR(255) PRIMARY KEY,
    application_id VARCHAR(255) NOT NULL REFERENCES applications(application_id) ON DELETE CASCADE,
    offered_amount NUMERIC(15, 2),
    offered_cost NUMERIC(15, 2),
    credit_score NUMERIC(10, 2),
    interest_rate NUMERIC(5, 2),
    term_months INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_offers_application_id ON offers(application_id);

-- ============================================================================
-- SYNTHETIC EXTENSIONS TABLE
-- Fictional operational fields for analytics demonstration
-- NEVER present as historical facts from the financial institution
-- ============================================================================
CREATE TABLE IF NOT EXISTS synthetic_extensions (
    application_id VARCHAR(255) PRIMARY KEY REFERENCES applications(application_id) ON DELETE CASCADE,
    document_type VARCHAR(100),
    page_count INTEGER,
    branch VARCHAR(100),
    operator_team VARCHAR(100),
    priority VARCHAR(20) CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    sla_target_hours INTEGER,
    region VARCHAR(50),
    channel VARCHAR(50),
    quality_score NUMERIC(5, 2),
    error_flag BOOLEAN DEFAULT FALSE,
    rejection_flag BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_synthetic_extensions_branch ON synthetic_extensions(branch);
CREATE INDEX IF NOT EXISTS idx_synthetic_extensions_priority ON synthetic_extensions(priority);
CREATE INDEX IF NOT EXISTS idx_synthetic_extensions_region ON synthetic_extensions(region);

-- ============================================================================
-- METADATA TABLE
-- Tracks data lineage and import history
-- ============================================================================
CREATE TABLE IF NOT EXISTS data_loads (
    load_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_file VARCHAR(500) NOT NULL,
    load_type VARCHAR(50) NOT NULL,
    records_loaded INTEGER,
    load_status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_data_loads_source_file ON data_loads(source_file);
CREATE INDEX IF NOT EXISTS idx_data_loads_load_status ON data_loads(load_status);

-- ============================================================================
-- VERSION TRACKING
-- Simple schema version tracking for migrations
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_versions (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT
);

-- Record initial schema version
INSERT INTO schema_versions (version, description)
VALUES ('001', 'Initial schema: applications, events, offers, synthetic_extensions, data_loads')
ON CONFLICT (version) DO NOTHING;