# Data dictionary: planned canonical document-operations dataset

**Planned grain:** one record per loan-application case represented as a fictional document-processing packet. The raw source stays at event grain; conversion is deferred to the data-quality phase.

| Column | Type | Definition | Lineage |
| --- | --- | --- | --- |
| `document_id` | string | Unique application/case identifier | Source-derived |
| `document_type` | string | Fictional packet type | Synthetic |
| `page_count` | integer | Fictional page count | Synthetic |
| `received_timestamp` | timestamp | Earliest relevant application event | Derived |
| `processing_start_timestamp` | timestamp | Start of operational handling | Derived |
| `processing_end_timestamp` | timestamp | Last relevant event | Derived |
| `branch`, `operator_team` | string | Fictional operating assignment | Synthetic |
| `status` | string | Canonical case outcome/status | Derived |
| `error_flag` | boolean | Fictional rework/error proxy | Synthetic proxy |
| `rejection_flag` | boolean | Denied/refused outcome mapping | Derived |
| `sla_target_hours` | integer | Fictional SLA threshold | Synthetic |
| `channel` | string | Submission-channel proxy | Derived proxy |
| `priority`, `region` | string | Fictional operational labels | Synthetic |
| `document_category` | string | Loan-purpose category | Source-derived (`LoanGoal`) |
| `processing_stage` | string | Process activity/stage | Derived |
| `quality_score` | decimal | Fictional quality score | Synthetic |
| `application_type` | string | Loan application type | Source-derived |
| `requested_amount` | decimal | Requested loan amount | Source-derived |
| `source_event_count` | integer | Number of source events in the case | Derived |
| `source_file` | string | Raw-file identifier | Metadata |

The event-level staging table will preserve `event_id`, `event_timestamp`, `activity`, `event_origin`, `lifecycle_transition`, `action`, `resource`, and offer attributes where present. Its final dictionary is deferred until Phase 3 validates full extraction.
