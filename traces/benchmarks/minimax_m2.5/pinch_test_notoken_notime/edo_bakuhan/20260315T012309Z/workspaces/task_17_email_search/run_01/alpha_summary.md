# Project Alpha Summary

## 1. Project Overview

Project Alpha is a new customer-facing analytics dashboard to replace the legacy reporting system.

- **Type**: Customer-facing analytics dashboard
- **Goal**: Replace legacy reporting system with modern real-time analytics
- **Target Users**: Enterprise clients (beta waitlist, prospective ARR deals)

## 2. Technology Stack

### Database & Storage
- **PostgreSQL + TimescaleDB**: Time-series data storage
- **Redis**: Caching for frequently accessed aggregations
- **S3**: Raw data lake storage

### Data Pipeline
- **Apache Kafka**: Real-time event streaming (~50K events/sec peak)
- **Apache Flink**: Stream processing and aggregation
- **Airflow**: Batch ingestion for historical data migration
- **dbt**: Batch transformations and data modeling
- **Great Expectations**: Data quality checks

### Application Layer
- **FastAPI (Python)**: REST API and WebSocket gateway
- **React + Recharts**: Frontend with charting library
- **OAuth2**: SSO integration for authentication

## 3. Budget Evolution

### Initial Budget
- **Total Approved**: $340K
  - Infrastructure: $85K
  - Engineering (6 FTEs, 4 months): $220K
  - QA and testing: $35K

### Budget Overrun Risk
- Data volume estimate increased to ~2TB/day
- Additional infrastructure costs: $15K/month (data) + $8K/month (Kafka 6 brokers)
- Projected total: ~$410K (21% overrun, +$70K over 4 months)
- CFO Linda Zhao requires cost-benefit analysis before approval

## 4. Timeline and Milestones

### Original Timeline
| Phase | Dates |
|-------|-------|
| Phase 1: Data Pipeline | Jan 20 - Feb 14 |
| Phase 2: API Layer | Feb 17 - Mar 14 |
| Phase 3: Frontend | Mar 17 - Apr 18 |
| Beta Launch | Apr 21 |
| GA Release | May 12 |

### Updated Timeline (Post-Security Review)
| Phase | Dates |
|-------|-------|
| Phase 2: API Layer | Feb 17 - Apr 1 (extended ~2.5 weeks) |
| Phase 3: Frontend | Apr 2 - May 3 |
| Beta Launch | May 6 (15-day slip) |
| GA Release | May 27 |

### Timeline Adjustment Reasons
- Security critical items: +1.5 weeks (cross-tenant isolation, WebSocket auth)
- WebSocket gateway service: +2 weeks
- Mitigation: Added 7th engineer (Alex Wong), parallel frontend development

## 5. Security Review Findings

### Critical Issues Identified (3 items)
1. **Cross-tenant data isolation**: Required fix before launch
2. **WebSocket authentication**: Needed for real-time streaming security
3. **Encryption at rest**: Compliance requirement

### Remediation Actions
- 1.5 weeks allocated for security fixes
- 2 weeks for WebSocket gateway implementation
- Security team approval required before Beta Launch

## 6. Client Feedback & Sales Pipeline

### Beta Waitlist Prospects (5 companies)
| Company | ARR Potential | Key Requirements |
|---------|---------------|-------------------|
| Summit Financial | $420K | Anomaly detection, SOC 2 Type II, white-labeling |
| DataFlow Inc | $300K | Snowflake integration, custom metrics |
| TechVentures | $680K | Real-time dashboards, API access |
| GlobalBank | $450K | GDPR compliance, multi-region |

### Feature Requests (Top 5)
1. Custom alerting / anomaly detection
2. Compliance-ready export (PDF/CSV)
3. API access for programmatic use
4. Multi-region / data residency support
5. White-labeling capabilities

### Revenue Projections
- **Original projection**: $2.1M ARR
- **Updated pipeline**: $1.85M - $2.8M ARR (ahead of target)
- Summit Financial's white-labeling request can be addressed with ~3 days of work
