# Project Alpha Summary

## 1. Project Overview
new customer-facing analytics dashboard that will replace the legacy reporting system
- **Technology Stack:** PostgreSQL + TimescaleDB for the time-series data, FastAPI (Python), React with the new charting library (Recharts), Kafka for real-time data streaming
- **Budget:** Original: $340K, Revised: $432K

## 2. Timeline
- **Original Target Completion:** May 12, 2026
- **Changes:**
  - GA Release slipped from May 12, 2026 to May 27, 2026 due to security findings and the need to refactor the WebSocket gateway service.
- **Current Expected Completion:** May 27, 2026

## 3. Key Risks and Issues
- **Budget Concerns:**
  - This would push us from $340K to potentially $432K - a 27% overrun
- **Security Findings:**
  - initial security review identified several critical vulnerabilities related to cross-tenant data access if metric_id is guessable and per-message authentication tokens. Remediation efforts are underway.

## 4. Client/Business Impact
- **Sales Pipeline Identified:** $1.85M ARR-$2.8M ARR
- **Client Feedback:**
  - Initial client feedback has been very positive, particularly regarding the intuitive UI and real-time data updates. E.g., "The real-time dashboard is exactly what we've been looking for"
- **Revenue Projections:** $1.85M ARR-$2.8M ARR

## 5. Current Status
- [2026-01-15] Project Alpha officially greenlit.
- [2026-01-22] Phase 1 (Data Ingestion & Core API) is complete.
- [2026-02-25] Frontend team has made significant progress on the dashboard UI and core components.
