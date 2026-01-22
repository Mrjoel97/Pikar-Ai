# Plan: Agent Capabilities Enhancement (Phase 2)

## Goal
Implement real database-backed services for the remaining 6 specialized agents that currently use mock tools or only RAG search.

## Phase 1: Core Business Services
- [x] Scaffold `initiative_service` feature (TDD) [64745ee]
- [x] Implement `InitiativeService` class (Supabase CRUD for initiatives, OKRs) [0ad9761]
- [x] Update `StrategicPlanningAgent` to use `InitiativeService` [d2801e4]
- [ ] Scaffold `campaign_service` feature (TDD)
- [ ] Implement `CampaignService` class (Supabase CRUD for campaigns, metrics)
- [ ] Update `MarketingAutomationAgent` to use `CampaignService`

## Phase 2: HR & Compliance Services
- [ ] Scaffold `recruitment_service` feature (TDD)
- [ ] Implement `RecruitmentService` class (job postings, candidates)
- [ ] Update `HRRecruitmentAgent` to use `RecruitmentService`
- [ ] Scaffold `compliance_service` feature (TDD)
- [ ] Implement `ComplianceService` class (audits, risk assessments)
- [ ] Update `ComplianceRiskAgent` to use `ComplianceService`

## Phase 3: Customer & Analytics Services
- [ ] Scaffold `support_ticket_service` feature (TDD)
- [ ] Implement `SupportTicketService` class (ticket CRUD)
- [ ] Update `CustomerSupportAgent` to use `SupportTicketService`
- [ ] Scaffold `analytics_service` feature (TDD)
- [ ] Implement `AnalyticsService` class (events, reports)
- [ ] Update `DataAnalysisAgent` to use `AnalyticsService`
