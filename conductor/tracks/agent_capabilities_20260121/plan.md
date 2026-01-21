# Plan: Specialized Agent Capabilities

## Goal
Replace mock tools with real, database-backed services (`app/services/`) to enable functional specialized agents.

## Phase 1: Financial Service (FinancialAnalysisAgent)
- [x] Scaffold `financial_service` feature (TDD) [f25ac35]
- [x] Implement `FinancialService` class (Supabase connection) [7459a57]
- [x] Implement `get_revenue_stats` and `get_expense_stats` real logic [e2cf14d]
- [x] Update `FinancialAnalysisAgent` to use `FinancialService` [0fa0863]

## Phase 2: Task & CRM Service (Sales/Operations Agents)
- [~] Scaffold `task_service` feature (TDD)
- [ ] Implement `TaskService` (CRUD for `ai_jobs` or new `tasks` table)
- [ ] Update `SalesAgent` and `OperationsAgent` to use `TaskService`

## Phase 3: Content Service (ContentCreationAgent)
- [ ] Scaffold `content_service` feature (TDD)
- [ ] Enhance `KnowledgeVault` for content generation/storage
- [ ] Update `ContentCreationAgent`
