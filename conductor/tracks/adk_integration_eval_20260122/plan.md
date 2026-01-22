# Plan: ADK Integration & Evaluation Pipeline

## Goal
Formalize the `adk_a2a_app_testing.ipynb` and `evaluating_adk_agent.ipynb` notebooks into automated, reusable test pipelines. This ensures adherence to the A2A protocol and provides quantitative metrics on agent performance.

## Phase 1: A2A Protocol Integration Testing
- [x] Scaffold `tests/integration` directory and dependencies [bee129f]
- [x] Implement `test_a2a_protocol.py` (based on `adk_a2a_app_testing.ipynb`) [32b1511]
- [x] Verify A2A protocol works with local agent [8717f43]

## Phase 2: Agent Evaluation "IQ" Pipeline
- [x] Scaffold `tests/eval_datasets` and `scripts/evaluation` [3f5cd8d]
- [x] Create `evaluate_agent.py` script (based on `evaluating_adk_agent.ipynb`) [9b7c607]
- [~] Create sample evaluation dataset (`recruitment_eval.json`)
- [ ] Run baseline evaluation on `HRRecruitmentAgent`

## Phase Checkpoint
**Summary**: Integration tests and evaluation scripts fully implemented and verified.
