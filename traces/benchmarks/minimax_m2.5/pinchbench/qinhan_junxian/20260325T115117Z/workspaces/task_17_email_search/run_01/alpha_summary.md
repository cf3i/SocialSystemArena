# Project Alpha Summary

## 1. Project Overview

**What is Project Alpha?**  
Project Alpha is a new customer-facing analytics dashboard that will replace the company's legacy reporting system. It is designed to provide real-time insights and interactive data visualization for clients.

**Technology Stack:**
- **Database:** PostgreSQL + TimescaleDB for time-series data storage
- **API Layer:** FastAPI (Python)
- **Frontend:** React with Recharts charting library
- **Data Pipeline:** Apache Kafka for real-time event streaming, Apache Flink for stream processing, Airflow for batch processing
- **Authentication:** OAuth2 integration with existing SSO
- **Additional:** Redis for caching, S3 for data lake storage

**Budget:**
- **Original Budget:** $340K (approved)
- **Revised Budget:** $410K (due to infrastructure cost increases)
  - Initial breakdown: Infrastructure $85K, Engineering (6 FTEs, 4 months) $220K, QA/Testing $35K
  - Additional costs: $15K/month for higher-than-projected data volume (~2TB/day), $8K/month for Kafka cluster scaling (6 brokers instead of 3)

---

## 2. Timeline

**Original Timeline (as of Jan 15, 2026):**
- Phase 1 (Data Pipeline): Jan 20 - Feb 14
- Phase 2 (API Layer): Feb 17 - Mar 14
- Phase 3 (Frontend): Mar 17 - Apr 18
- Beta Launch: Apr 21
- GA Release: May 12

**Updated Timeline (as of Feb 18, 2026 - after security review):**
- Phase 1 (Data Pipeline): Jan 20 - Feb 12 ✓ COMPLETED
- Phase 2 (API Layer): Feb 17 - Apr 1 (extended from Mar 14)
- Phase 3 (Frontend): Apr 2 - May 3 (extended from Apr 18)
- Beta Launch: May 6 (delayed from Apr 21)
- GA Release: May 27 (delayed from May 12)

**Total Delay:** 15 days (due to security review findings)

---

## 3. Key Risks and Issues

### Budget Concerns
- **Original vs. Revised:** Budget increased from $340K to $410K (27% overrun)
- **Root Cause:** Higher-than-expected data volume (2TB/day) and Kafka cluster sizing requirements
- **Mitigation:** CFO Linda Zhao requested cost-benefit analysis, confirmation of $2.1M ARR projections, and exploration of cost optimization options (spot instances, tiered data retention)

### Security Findings (Feb 10 Security Review)
- **Critical Issues Found:**
  1. Authentication/authorization vulnerabilities in API gateway
  2. Missing WebSocket security implementation
- **Impact:** Added ~1.5 weeks for auth fixes, ~2 weeks for WebSocket gateway
- **Decision:** Security fixes are non-negotiable; timeline adjusted accordingly

### Technical Challenges
- Kafka cluster required 6 brokers instead of 3 for peak load handling
- Data volume projection increased from initial estimates
- Real-time metric widgets blocked until WebSocket API endpoint is ready

---

## 4. Client/Business Impact

### Sales Pipeline & Revenue Projections
- **Projected ARR:** $1.85M - $2.8M from the analytics product
- **Confirmed by Sales:** Jessica confirmed the $2.1M ARR projection still holds

### Client Feedback
- **Summit Financial (key beta client):**
  - Requested white-labeling capability
  - White-label support can be added with ~3 days of work during Phase 3
  - No hard deadlines before May 6 Beta Launch
- **Client Sentiment:** Generally positive, excited about dashboard capabilities
- **Beta Waitlist:** Confirmed no hard client deadlines before May 6

### Business Decisions Made
- Added Alex Wong as 7th engineer to help with security fixes
- Moved compliance export feature to Phase 3 to keep Phase 2 focused
- Started frontend component development in parallel during late Phase 2
- White-label support worth prioritizing based on client feedback

---

## 5. Current Status (as of Feb 25, 2026)

### Completed
- **Phase 1 (Data Pipeline):** Completed on Feb 12 (ahead of original Feb 14 schedule)
- **Frontend Foundation:**
  - Design system and component library (Storybook)
  - Dashboard layout engine with drag-and-drop
  - Chart components (line, bar, area, pie)
  - Authentication flow with SSO
  - Responsive layouts for tablet/desktop

### In Progress
- **Phase 2 (API Layer):** In progress (security fixes being implemented)
- **Frontend Development:**
  - Real-time data streaming UI (waiting on WebSocket gateway)
  - Report export interface (PDF preview + CSV download)
  - Alert configuration wizard

### Blocked Items
- Live metric widgets awaiting WebSocket API endpoint (Marcus ETA: Mar 10)
- Custom metric builder awaiting metric definition API

### Next Milestones
- Phase 2 completion target: Apr 1
- Phase 3 completion target: May 3
- Beta Launch: May 6
- GA Release: May 27

---